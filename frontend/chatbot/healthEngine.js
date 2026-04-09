import api from '../services/api.js';
import Store from '../context/State.js';

export const HealthEngine = {
    /**
     * Tracks dosage per day for a specific medicine
     */
    async setDosage(medicineId, dosagePerDay) {
        try {
            const res = await fetch(`http://127.0.0.1:8000/cart/set-dosage?medicine_id=${medicineId}&dosage_per_day=${dosagePerDay}`, {
                method: 'POST'
            });
            const data = await res.json();
            return data;
        } catch (err) {
            console.error('[HealthEngine] Dosage set failed', err);
            return null;
        }
    },

    /**
     * Checks for interactions between items in the current cart
     */
    async checkInteractions() {
        try {
            const data = await api.getCart();
            const items = data.items || [];
            if (items.length < 2) return null;

            const res = await api.fetchHealthRisk(); // Re-use backend risk logic
            return res;
        } catch (err) {
            return null;
        }
    },

    /**
     * Calculates a summary level risk (Low/Medium/High)
     */
    getRiskCategory(score) {
        if (score >= 26) return 'High Attention Needed';
        if (score >= 11) return 'Monitor Closely';
        return 'Safe';
    }
};
