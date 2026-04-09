import api from '../services/api.js';
import Store from '../context/State.js';

export function useMedicines() {
    async function refreshMedicines(filters = {}) {
        Store.setState({ loading: true, error: null });
        try {
            const data = await api.fetchMedicines(filters);
            Store.setState({ medicines: data, loading: false });
        } catch (err) {
            Store.setState({ error: err.message, loading: false });
            console.error('[useMedicines]', err);
        }
    }

    async function refreshCategories() {
        try {
            const data = await api.fetchCategories();
            Store.setState({ categories: data.categories || [] });
        } catch (err) {
            console.error('[useMedicines] categories failed', err);
        }
    }

    async function loadMedicineDetail(id) {
        Store.setState({ loading: true });
        try {
            const data = await api.fetchMedicineById(id);
            Store.setState({ selectedMedicine: data, loading: false });
        } catch (err) {
            Store.setState({ error: 'Medicine not found', loading: false });
        }
    }

    return { refreshMedicines, refreshCategories, loadMedicineDetail };
}
