import api from '../services/api.js';
import Store from '../context/State.js';

export function useCart() {
    async function refreshCart() {
        try {
            console.log('[useCart] Fetching cart data...');
            const data = await api.getCart();
            console.log('[useCart] Cart data received:', data);
            Store.setState({ cart: data });

            // Force render if on cart page
            const currentPage = document.querySelector('.page.active')?.id;
            if (currentPage === 'page-cart') {
                console.log('[useCart] Force rendering page-cart');
                CartPage.render(data);
            }
        } catch (err) {
            console.error('[useCart] refresh cart failed', err);
        }
    }

    async function addToCart(medicine_id, medicine_name, price) {
        try {
            const res = await api.addToCart({
                medicine_id: String(medicine_id),
                medicine_name,
                price_inr: Number(price)
            });

            if (res.status === 'warning') {
                alert(res.message);
                return;
            }

            await refreshCart();
        } catch (err) {
            alert('Unable to add item to cart.');
        }
    }

    async function removeFromCart(id, removeAll = false) {
        try {
            await api.removeFromCart(id, 1, removeAll);
            await refreshCart();
        } catch (err) {
            alert('Removal failed.');
        }
    }

    async function clearCart() {
        try {
            await api.clearCart();
            await refreshCart();
        } catch (err) {
            alert('Clear failed.');
        }
    }

    return { refreshCart, addToCart, removeFromCart, clearCart };
}
