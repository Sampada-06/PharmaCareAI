const API_BASE = 'http://127.0.0.1:8001';

/**
 * Check if backend is running and show helpful error
 */
async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE}/docs`, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        return false;
    }
}

/**
 * Show user-friendly error when backend is down
 */
function showBackendDownError() {
    const errorHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                    background: rgba(239, 68, 68, 0.95); color: white; padding: 30px; 
                    border-radius: 15px; max-width: 500px; z-index: 10000; text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <h2 style="margin: 0 0 15px 0; font-size: 24px;">⚠️ Backend Server Not Running</h2>
            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6;">
                The PharmaCare backend server is not running. Please start it to use the application.
            </p>
            <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0 0 10px 0; font-weight: bold;">Quick Fix:</p>
                <code style="background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 5px; 
                            display: block; font-size: 14px; color: #fff;">
                    Double-click: START_BACKEND.bat
                </code>
                <p style="margin: 10px 0 0 0; font-size: 13px; opacity: 0.9;">
                    Or run: <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">
                    uvicorn app.main:app --reload --port 8000</code>
                </p>
            </div>
            <button onclick="location.reload()" 
                    style="background: white; color: #dc2626; border: none; padding: 12px 30px; 
                           border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer;">
                Retry Connection
            </button>
        </div>
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                    background: rgba(0,0,0,0.7); z-index: 9999;"></div>
    `;

    // Remove existing error if present
    const existing = document.getElementById('backend-error-overlay');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.id = 'backend-error-overlay';
    div.innerHTML = errorHTML;
    document.body.appendChild(div);
}

/**
 * Wrapper for fetch with better error handling
 */
async function safeFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);

        // Handle 401 Unauthorized - token expired
        if (response.status === 401) {
            console.warn('[API] 401 Unauthorized - Token expired');
            handleTokenExpired();
            throw new Error('Session expired. Please login again.');
        }

        return response;
    } catch (error) {
        // Network error - backend is down
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            showBackendDownError();
            throw new Error('Backend server is not running. Please start the backend server and try again.');
        }
        throw error;
    }
}

/**
 * Handle expired token - show message and redirect to login
 */
function handleTokenExpired() {
    // Only show once per session
    if (sessionStorage.getItem('token_expired_shown')) return;
    sessionStorage.setItem('token_expired_shown', 'true');

    const errorHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                    background: rgba(251, 146, 60, 0.95); color: white; padding: 30px; 
                    border-radius: 15px; max-width: 500px; z-index: 10000; text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <h2 style="margin: 0 0 15px 0; font-size: 24px;">🔒 Session Expired</h2>
            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6;">
                Your login session has expired. Please login again to continue.
            </p>
            <button onclick="location.href='auth.html'" 
                    style="background: white; color: #ea580c; border: none; padding: 12px 30px; 
                           border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer;">
                Go to Login
            </button>
        </div>
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                    background: rgba(0,0,0,0.7); z-index: 9999;"></div>
    `;

    const div = document.createElement('div');
    div.id = 'token-expired-overlay';
    div.innerHTML = errorHTML;
    document.body.appendChild(div);

    // Clear expired token
    localStorage.removeItem('auth_token');

    // Auto-redirect after 3 seconds
    setTimeout(() => {
        window.location.href = 'auth.html';
    }, 3000);
}

/**
 * Standardized API Wrapper for PharmaCare AI
 */
const api = {
    // ── Auth Endpoints ──────────────────────────────────────────────
    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email); // OAuth2PasswordRequestForm uses 'username'
        formData.append('password', password);

        const response = await safeFetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        if (data.access_token) {
            localStorage.setItem('auth_token', data.access_token);
        }
        return data;
    },

    async register(userData) {
        const response = await safeFetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }
        return await response.json();
    },

    async getCurrentUser() {
        const token = localStorage.getItem('auth_token');
        if (!token) return null;

        const response = await safeFetch(`${API_BASE}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        }).catch(() => null);

        if (!response || !response.ok) {
            localStorage.removeItem('auth_token');
            return null;
        }
        const userData = await response.json();
        // Store user data in localStorage for quick access
        localStorage.setItem('user', JSON.stringify(userData));
        return userData;
    },

    async updateProfile(profileData) {
        const token = localStorage.getItem('auth_token');
        if (!token) throw new Error('Not authenticated');

        const response = await safeFetch(`${API_BASE}/me`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Profile update failed');
        }

        const updatedUser = await response.json();
        // Update localStorage with new data
        localStorage.setItem('user', JSON.stringify(updatedUser));
        return updatedUser;
    },

    logout() {
        localStorage.removeItem('auth_token');
        window.location.href = 'index.html';
    },

    _getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('auth_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    },

    async get(endpoint) {
        const response = await safeFetch(`${API_BASE}${endpoint}`, {
            headers: this._getHeaders()
        });
        const data = await response.json();
        return { ok: response.ok, status: response.status, json: data };
    },

    async post(endpoint, body) {
        const response = await safeFetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify(body)
        });
        const data = await response.json();
        return { ok: response.ok, status: response.status, json: data };
    },

    // ── Medicine Endpoints ──────────────────────────────────────────
    async fetchMedicines(params = {}) {
        // Sanitize parameters to remove undefined/null values
        const cleanParams = Object.fromEntries(
            Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== '')
        );
        const query = new URLSearchParams(cleanParams).toString();
        const response = await safeFetch(`${API_BASE}/medicines${query ? '?' + query : ''}`);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async fetchMedicineById(id) {
        const response = await safeFetch(`${API_BASE}/medicines/${id}`);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async fetchCategories() {
        const response = await safeFetch(`${API_BASE}/categories`);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    // ── Cart Endpoints ──────────────────────────────────────────────
    async getCart() {
        const response = await safeFetch(`${API_BASE}/cart`, {
            headers: this._getHeaders()
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async addToCart(data) {
        const response = await safeFetch(`${API_BASE}/cart/add`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async removeFromCart(id, qty = 1, removeAll = false) {
        const response = await safeFetch(`${API_BASE}/cart/remove/${id}?qty=${qty}&remove_all=${removeAll}`, {
            method: 'DELETE',
            headers: this._getHeaders()
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async clearCart() {
        const response = await safeFetch(`${API_BASE}/cart/clear`, {
            method: 'DELETE',
            headers: this._getHeaders()
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    // ── Health Risk Index ───────────────────────────────────────────
    async fetchHealthRisk() {
        const response = await safeFetch(`${API_BASE}/health/risk-index`, {
            headers: this._getHeaders()
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    // ── Chat & AI Endpoints ─────────────────────────────────────────
    async chat(message, context = {}) {
        // Clean context to avoid circular references or undefined values
        const cleanContext = context && typeof context === 'object'
            ? JSON.parse(JSON.stringify(context))
            : {};

        const response = await safeFetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify({
                message: String(message),
                context: cleanContext,
                history: context.history || []
            })
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(`API Error: ${response.status} - ${JSON.stringify(errorData)}`);
        }
        return await response.json();
    },

    async uploadPrescription(file, medicineName = '') {
        const formData = new FormData();
        formData.append('file', file);
        const query = medicineName ? `?medicine_name=${encodeURIComponent(medicineName)}` : '';
        const response = await safeFetch(`${API_BASE}/upload_prescription${query}`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    // ── Order & Payment Endpoints ───────────────────────────────────
    async createOrder(data) {
        const response = await safeFetch(`${API_BASE}/orders/create`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },


    async generateQr(orderId, amount) {
        const response = await safeFetch(`${API_BASE}/payments/generate-qr?order_id=${orderId}&amount=${amount}`, {
            method: 'POST',
            headers: this._getHeaders()
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    },

    async checkout(data) {
        const response = await safeFetch(`${API_BASE}/checkout`, {
            method: 'POST',
            headers: this._getHeaders(),
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Checkout failed');
        }
        return response.json();
    },

    // ── Orders ──

    async trackOrder(orderId) {
        const response = await safeFetch(`${API_BASE}/orders/track/${orderId}`, {
            method: 'GET',
            headers: this._getHeaders()
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Track order failed');
        }
        return response.json();
    },

    async fetchMyOrders() {
        const response = await safeFetch(`${API_BASE}/orders/my`, {
            method: 'GET',
            headers: this._getHeaders()
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to fetch orders');
        }
        return response.json();
    },

    async fetchRefillAlerts() {
        const userStr = localStorage.getItem('user');
        if (!userStr) return { predictions: [] };
        const user = JSON.parse(userStr);
        if (!user.id) return { predictions: [] };

        const response = await safeFetch(`${API_BASE}/refill-predictions/${user.id}`, {
            method: 'GET',
            headers: this._getHeaders()
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to fetch refill alerts');
        }
        return response.json();
    }
};

export default api;
