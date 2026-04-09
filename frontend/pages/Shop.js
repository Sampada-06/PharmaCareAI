import Store from '../context/State.js';

// Professional medical images by category
function getProductImage(category) {
    const cat = (category || '').toLowerCase();
    
    // MEDICINE (Tablets/Capsules) - Generic capsule
    if (cat.includes('medicine') || cat.includes('tablet') || cat.includes('capsule')) {
        return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="32" cy="32" rx="24" ry="12" fill="#14B8A6" opacity="0.2"/>
            <path d="M32 12C20 12 10 20 10 32C10 44 20 52 32 52C44 52 54 44 54 32C54 20 44 12 32 12Z" fill="#14B8A6"/>
            <path d="M32 12C20 12 10 20 10 32H32V12Z" fill="#0D9488"/>
            <circle cx="32" cy="32" r="3" fill="white" opacity="0.3"/>
        </svg>`;
    }
    
    // SUPPLEMENT - Different color capsule
    if (cat.includes('supplement') || cat.includes('vitamin') || cat.includes('calcium') || cat.includes('omega') || cat.includes('iron') || cat.includes('multivitamin')) {
        return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="32" cy="32" rx="24" ry="12" fill="#F59E0B" opacity="0.2"/>
            <path d="M32 12C20 12 10 20 10 32C10 44 20 52 32 52C44 52 54 44 54 32C54 20 44 12 32 12Z" fill="#F59E0B"/>
            <path d="M32 12C20 12 10 20 10 32H32V12Z" fill="#D97706"/>
            <circle cx="32" cy="32" r="3" fill="white" opacity="0.3"/>
        </svg>`;
    }
    
    // SKINCARE - Cream tube
    if (cat.includes('skincare') || cat.includes('cream') || cat.includes('gel') || cat.includes('lotion') || cat.includes('moisturiz') || cat.includes('sunscreen') || cat.includes('acne') || cat.includes('aloe') || cat.includes('cetaphil')) {
        return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="20" y="12" width="24" height="8" rx="2" fill="#8B5CF6"/>
            <path d="M22 20H42V48C42 50.2 40.2 52 38 52H26C23.8 52 22 50.2 22 48V20Z" fill="#A78BFA"/>
            <rect x="24" y="24" width="16" height="3" rx="1.5" fill="white" opacity="0.3"/>
            <rect x="24" y="30" width="12" height="2" rx="1" fill="white" opacity="0.2"/>
        </svg>`;
    }
    
    // SANITARY - Baby/hygiene products
    if (cat.includes('sanitary') || cat.includes('baby') || cat.includes('diaper') || cat.includes('wipes') || cat.includes('pads') || cat.includes('tampon') || cat.includes('mask')) {
        return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="16" y="20" width="32" height="28" rx="4" fill="#EC4899"/>
            <rect x="20" y="24" width="24" height="20" rx="2" fill="#F9A8D4"/>
            <path d="M28 32L32 36L40 28" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
    }
    
    // BODY CARE - Bottle
    if (cat.includes('body') || cat.includes('soap') || cat.includes('antiseptic') || cat.includes('foot') || cat.includes('medicated')) {
        return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="24" y="12" width="16" height="6" rx="2" fill="#06B6D4"/>
            <path d="M22 18H42V50C42 51.1 41.1 52 40 52H24C22.9 52 22 51.1 22 50V18Z" fill="#22D3EE"/>
            <ellipse cx="32" cy="35" rx="8" ry="12" fill="white" opacity="0.2"/>
            <rect x="26" y="22" width="12" height="2" rx="1" fill="white" opacity="0.3"/>
        </svg>`;
    }
    
    // DEFAULT - Generic capsule for medicines
    return `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="32" cy="32" rx="24" ry="12" fill="#14B8A6" opacity="0.2"/>
        <path d="M32 12C20 12 10 20 10 32C10 44 20 52 32 52C44 52 54 44 54 32C54 20 44 12 32 12Z" fill="#14B8A6"/>
        <path d="M32 12C20 12 10 20 10 32H32V12Z" fill="#0D9488"/>
        <circle cx="32" cy="32" r="3" fill="white" opacity="0.3"/>
    </svg>`;
}

export const ShopPage = {
    render(medicines) {
        const grid = document.getElementById('productGrid');
        if (!medicines || medicines.length === 0) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;">No medicines found.</div>';
            return;
        }

        grid.innerHTML = medicines.map(m => `
            <div class="product-card" onclick="window.viewMedicine('${m.id}')">
                <div class="product-img" style="position:relative; display:flex; align-items:center; justify-content:center; padding:16px; background:rgba(20,184,166,0.03); border-radius:12px; margin-bottom:12px;">
                    ${m.prescription_required ? '<div class="rx-badge">Rx Required</div>' : '<div class="otc-badge">OTC</div>'}
                    <div style="position:absolute; top:8px; right:8px; background:rgba(20, 184, 166, 0.1); color:var(--primary); font-size:9.5px; padding:3px 8px; border-radius:12px; font-weight:700; border:1px solid rgba(20, 184, 166, 0.4); text-transform:uppercase; backdrop-filter:blur(4px);">${m.category || 'Medicine'}</div>
                    ${getProductImage(m.category)}
                </div>
                <div class="product-body">
                    <div class="product-name">${m.name || '—'}</div>
                    <div class="product-brand" style="color:var(--primary); font-weight:600; font-size:11px; margin-bottom:4px;">${m.package_size || 'Standard Pack'}</div>
                    <div class="product-footer">
                        <div class="product-price">₹${Number(m.price).toFixed(2)}</div>
                        <button class="btn btn-primary btn-sm" 
                            onclick="event.stopPropagation(); window.addToCart('${m.id}', '${m.name.replace(/'/g, "\\'")}', ${m.price})">
                            Add
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    },

    // Initial Load
    init() {
        console.log('[ShopPage] Initializing...');
        window.refreshCart();
        window.refreshMedicines();
        window.refreshCategories();
    },

    populateCategories(categories) {
        console.log('[ShopPage] Populating categories:', categories);
        const select = document.getElementById('categorySelect');
        if (!select) return;

        // Keep "All Categories"
        select.innerHTML = '<option value="">All Categories</option>';
        if (categories && Array.isArray(categories)) {
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                opt.style.background = 'var(--card)';
                opt.style.color = 'var(--text)';
                select.appendChild(opt);
            });
        }
    }
};
