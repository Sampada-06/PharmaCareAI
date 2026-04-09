/**
 * Global State Management (Observer Pattern)
 */
class GlobalState {
    constructor() {
        this.state = {
            medicines: [],
            categories: [],
            cart: { items: [], item_count: 0, total: 0 },
            loading: false,
            error: null,
            currentPage: 'home',
            selectedMedicine: null // For details page
        };
        this.listeners = [];
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
}

const Store = new GlobalState();
export default Store;
