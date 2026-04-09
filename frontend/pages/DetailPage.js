export const DetailPage = {
    render(medicine) {
        const container = document.getElementById('medicineDetailContent');
        if (!medicine) {
            container.innerHTML = '<div style="padding:40px;text-align:center;">Medicine not found.</div>';
            return;
        }

        container.innerHTML = `
            <div style="display:grid;grid-template-columns:300px 1fr;gap:40px;padding:32px;">
                <div style="background:var(--card-2);border-radius:var(--radius);height:300px;display:flex;align-items:center;justify-content:center;font-size:80px;">
                    💊
                </div>
                <div>
                    <h2 style="font-size:28px;font-weight:800;color:var(--text);margin-bottom:8px;">${medicine.name}</h2>
                    <div style="font-size:16px;color:var(--primary);font-weight:600;margin-bottom:20px;">${medicine.package_size || 'Standard Pack'}</div>
                    
                    <div class="mb-24" style="font-size:15px;color:var(--muted);line-height:1.6;">
                        ${medicine.description || medicine.descriptions || 'No description available for this medicine.'}
                    </div>

                    <div style="display:flex;align-items:center;gap:32px;margin-bottom:32px;padding:20px;background:rgba(255,255,255,0.03);border-radius:var(--radius-sm);">
                        <div>
                            <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Price</div>
                            <div style="font-size:24px;font-weight:800;color:var(--text);">₹${Number(medicine.price).toFixed(2)}</div>
                        </div>
                        <div>
                            <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Type</div>
                            <div style="font-size:14px;font-weight:700;">${medicine.prescription_required ? '<span style="color:var(--danger)">Rx Required</span>' : '<span style="color:var(--success)">OTC</span>'}</div>
                        </div>
                        <div>
                            <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Category</div>
                            <div style="font-size:14px;font-weight:700;color:var(--text);">${medicine.category || 'General'}</div>
                        </div>
                    </div>

                    <button class="btn btn-primary" style="padding:14px 40px;font-size:16px;" 
                        onclick="window.addToCart('${medicine.id}', '${medicine.name.replace(/'/g, "\\'")}', ${medicine.price})">
                        Add to Cart
                    </button>
                </div>
            </div>
        `;
    }
};
