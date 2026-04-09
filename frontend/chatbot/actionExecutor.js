import api from '../services/api.js';
import Store from '../context/State.js';
import { useMedicines } from '../hooks/useMedicines.js';
import { useCart } from '../hooks/useCart.js';

const { refreshMedicines } = useMedicines();
const { addToCart, refreshCart, clearCart } = useCart();

export const ActionExecutor = {
    async execute(intentObj, context) {
        const { intent, entities } = intentObj;

        switch (intent) {
            case 'SEARCH':
                const query = entities[0] || '';
                await refreshMedicines({ search: query });
                return {
                    status: 'success',
                    data: Store.state.medicines,
                    message: `Found ${Store.state.medicines.length} results for "${query}".`
                };

            case 'ADD_TO_CART':
                const term = entities[0];
                const bypass = intentObj.entities?.force_bypass_rx || false;

                // Identification logic
                const target = Store.state.medicines.find(m =>
                    m.name.toLowerCase().includes(term.toLowerCase())
                ) || Store.state.medicines[0];

                if (target) {
                    const res = await api.addToCart({
                        medicine_id: String(target.id),
                        medicine_name: target.name,
                        price_inr: Number(target.price),
                        qty: intentObj.qty || 1,
                        force_bypass_rx: bypass
                    });

                    if (res.status === 'refused') {
                        return { status: 'refused', type: res.type, message: res.message };
                    }

                    if (res.status === 'warning') {
                        return { status: 'warning', type: 'prescription', message: res.message, medicine_id: target.id };
                    }

                    await refreshCart();
                    return {
                        status: 'success',
                        data: target,
                        message: `Added ${intentObj.qty || 1} units of ${target.name} to your cart.`
                    };
                }
                return { status: 'error', message: "I couldn't identify the medicine to add." };

            case 'REMOVE_FROM_CART':
                const removeTerm = entities[0];
                await refreshCart();
                const toRemove = Store.state.cart.items.find(item =>
                    item.name.toLowerCase().includes(removeTerm.toLowerCase())
                );

                if (toRemove) {
                    const qtyToRemove = intentObj.qty || 1;
                    await api.removeFromCart(toRemove.id, qtyToRemove);
                    await refreshCart();
                    return {
                        status: 'success',
                        message: `Removed ${qtyToRemove} units of ${toRemove.name} from your cart.`
                    };
                }
                return { status: 'error', message: `I couldn't find ${removeTerm} in your cart.` };

            case 'SHOW_CART':
                await refreshCart();
                return {
                    status: 'success',
                    data: Store.state.cart,
                    message: "Here is your current cart summary."
                };

            case 'CLEAR_CART':
                await clearCart();
                return {
                    status: 'success',
                    message: "Your cart has been cleared."
                };

            case 'RISK_ANALYSIS':
                // Bridge to the global checkHealthRisk function
                if (window.checkHealthRisk) await window.checkHealthRisk();
                return {
                    status: 'success',
                    message: "Health risk analysis completed. Please check your dashboard."
                };

            case 'TRUST_QUERY':
                return { status: 'info', type: 'trust' };

            case 'REFILL_CHECK':
                await refreshCart();
                const summary = Store.state.cart.prediction_summary;
                return {
                    status: 'success',
                    data: summary,
                    message: summary.upcoming_refills > 0
                        ? `You have ${summary.upcoming_refills} medicines due for refill soon.`
                        : "All your medicines are currently well-stocked."
                };

            case 'GREETING':
                return {
                    status: 'success',
                    message: "Hello! How can I help you with your healthcare needs today?"
                };

            case 'GENERATE_QR':
                const qrRes = await api.generateQr(intentObj.order_id, intentObj.amount);
                return {
                    status: 'success',
                    type: 'qr_code',
                    data: qrRes.qr_string,
                    message: intentObj.message || "Please scan this QR code to complete your payment."
                };

            case 'PLACE_ORDER':
                let userInfo = { name: 'Guest', phone: '000-000-0000', email: 'guest@example.com' };
                let userId = 'anonymous';
                
                try {
                    const localUser = localStorage.getItem('user');
                    if (localUser) {
                        const userParsed = JSON.parse(localUser);
                        userInfo = {
                            name: userParsed.name || 'User',
                            phone: userParsed.phone || 'N/A',
                            email: userParsed.email || 'N/A'
                        };
                        userId = userParsed.id || 'anonymous';
                    }
                } catch (e) {
                    console.error("Error getting user info for order:", e);
                }

                const orderData = {
                    items: Store.state.cart.items,
                    total_amount: Store.state.cart.total,
                    payment_method: intentObj.payment_method || 'COD',
                    customer_info: userInfo,
                    user_id: userId
                };
                const orderRes = await api.createOrder(orderData);
                if (orderRes.status === 'success') {
                    await refreshCart();
                    return {
                        status: 'success',
                        type: 'order_confirmed',
                        order_id: orderRes.order_id,
                        message: `Order placed successfully! Your Order ID is ${orderRes.order_id}. You can track it by saying "Track my order".`
                    };
                }
                return { status: 'error', message: "Failed to place order." };

            case 'TRACK_ORDER':
                const trackId = intentObj.order_id || entities[0];
                if (!trackId) return { status: 'error', message: "Please specify an Order ID to track." };
                const trackRes = await api.trackOrder(trackId);
                return {
                    status: 'success',
                    data: trackRes,
                    message: `Order ${trackId} Status: ${trackRes.shipping_status}. Payment: ${trackRes.payment_status}.`
                };

            default:
                return { status: 'unknown', message: "I'm not sure how to handle that request yet." };
        }
    }
};
