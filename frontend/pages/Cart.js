export const CartPage = {
    render(cartData) {
        console.log('[CartPage] Rendering with data:', cartData);

        // Handle both formats: direct items array or wrapped in object
        const items = Array.isArray(cartData) ? cartData : (cartData.items || []);
        const itemCount = cartData.item_count || items.length;
        const total = cartData.total || items.reduce((sum, item) => sum + (item.subtotal || 0), 0);

        const tableWrap = document.getElementById('cartTableWrap');
        const emptyEl = document.getElementById('cartEmpty');
        const totalEl = document.getElementById('cartTotal');
        const totalVal = document.getElementById('cartTotalValue');
        const tbody = document.getElementById('cartTableBody');
        const countEls = ['cartTopBadge', 'cartNavBadge'];

        // Update badges
        countEls.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = itemCount;
                el.style.display = itemCount > 0 ? 'inline-block' : 'none';
            }
        });

        if (items.length === 0) {
            console.log('[CartPage] No items, showing empty state');
            tableWrap.style.display = 'none';
            emptyEl.style.display = 'block';
            totalEl.style.display = 'none';
            const actionEl = document.getElementById('cartActions');
            if (actionEl) actionEl.style.display = 'none';
            return;
        }

        console.log('[CartPage] Rendering', items.length, 'items');
        tableWrap.style.display = 'block';
        emptyEl.style.display = 'none';
        totalEl.style.display = 'flex';
        const actionEl = document.getElementById('cartActions');
        if (actionEl) actionEl.style.display = 'block';

        tbody.innerHTML = items.map(item => {
            const rxRequired = item.requires_prescription;
            // A prescription is considered "valid" if it's in DB or if it's verified in localStorage
            const isVerified = (item.prescription_url) || (localStorage.getItem(`prescription_${item.id}_verified`) === 'true');
            const hasUpload = isVerified || localStorage.getItem(`prescription_${item.id}`);

            return `
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:12px;font-size:13px;color:var(--text);">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <strong>${item.name}</strong>
                        <span style="font-size:9px; background:rgba(20,184,166,0.1); color:var(--primary); padding:2px 6px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px;">${item.category || 'Medicine'}</span>
                        ${rxRequired ? '<span style="font-size:9px; background:rgba(239,68,68,0.1); color:var(--danger); padding:2px 6px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;">Rx Required</span>' : ''}
                    </div>
                    <div style="font-size:10px; color:var(--muted); margin-top:4px;">ID: ${item.id}</div>
                    ${rxRequired ? `
                        <div style="margin-top:8px;">
                            ${isVerified ? `
                                <div style="display:flex; align-items:center; gap:8px; padding:6px 10px; background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3); border-radius:6px; font-size:11px; color:var(--success);">
                                    <span style="font-weight:700;">✓</span>
                                    <span style="font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Prescription Verified</span>
                                    <button onclick="window.viewPrescriptionInCart('${item.id}')" style="margin-left:auto; background:none; border:none; color:var(--success); text-decoration:underline; cursor:pointer; font-size:11px;">View</button>
                                    <button onclick="window.removePrescriptionFromCart('${item.id}')" style="background:none; border:none; color:var(--danger); cursor:pointer; font-size:11px;">✗</button>
                                </div>
                            ` : hasUpload ? `
                                <div style="display:flex; align-items:center; gap:8px; padding:6px 10px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:6px; font-size:11px; color:var(--warning);">
                                    <span>⚠️</span>
                                    <span>Uploaded (Verification Pending)</span>
                                    <button onclick="window.removePrescriptionFromCart('${item.id}')" style="margin-left:auto; background:none; border:none; color:var(--danger); cursor:pointer; font-size:11px;">Remove</button>
                                </div>
                            ` : `
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <input type="file" id="prescription_${item.id}" accept="image/*,.pdf" style="display:none;" onchange="window.handlePrescriptionUpload('${item.id}', this, '${item.name}')" />
                                    <button onclick="document.getElementById('prescription_${item.id}').click()" class="btn btn-sm" style="font-size:11px; padding:6px 12px; background:rgba(56,189,248,0.1); color:var(--accent); border:1px solid rgba(56,189,248,0.3);">
                                        📎 Upload Prescription
                                    </button>
                                    <span style="font-size:10px; color:var(--warning);">⚠️ Required before checkout</span>
                                </div>
                            `}
                        </div>
                    ` : ''}
                </td>
                <td style="padding:12px;text-align:center;">
                    <div class="cart-prediction-box">
                        Qty: ${item.qty}
                    </div>
                </td>
                <td style="padding:12px;text-align:right;">₹${Number(item.price).toFixed(2)}</td>
                <td style="padding:12px;text-align:right;font-weight:600;color:var(--primary);">₹${Number(item.subtotal).toFixed(2)}</td>
                <td style="padding:12px;text-align:center;">
                    <button class="btn btn-ghost btn-sm" style="color:var(--danger);" onclick="window.removeFromCart('${item.id}', true)">&times;</button>
                </td>
            </tr>
        `}).join('');

        if (totalVal) {
            totalVal.textContent = '₹' + Number(total).toFixed(2);
        }

        console.log('[CartPage] Rendered successfully, total:', total);

        // Update checkout button state
        CartPage.updateCheckoutButton(items);
    },

    updateCheckoutButton(items) {
        const checkoutBtn = document.querySelector('#cartActions button');
        if (!checkoutBtn) return;

        // Check if all prescription-required items have VERIFIED prescriptions
        const missingPrescriptions = items.filter(item => {
            if (!item.requires_prescription) return false;
            const isVerified = (item.prescription_url) || (localStorage.getItem(`prescription_${item.id}_verified`) === 'true');
            return !isVerified;
        });

        if (missingPrescriptions.length > 0) {
            checkoutBtn.disabled = true;
            checkoutBtn.style.opacity = '0.5';
            checkoutBtn.style.cursor = 'not-allowed';
            checkoutBtn.title = 'Please upload a valid prescription for all required items';
        } else {
            checkoutBtn.disabled = false;
            checkoutBtn.style.opacity = '1';
            checkoutBtn.style.cursor = 'pointer';
            checkoutBtn.title = '';
        }
    }
};
