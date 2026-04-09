/**
 * Intent Engine
 * Maps user queries to system intents
 */

const INTENT_PATTERNS = {
    SEARCH: [
        /show me (.+)/i, /search (.+)/i, /find (.+)/i, /i need (.+)/i,
        /(.+) दाखवा/i, /(.+) पाहिजे/i, /(.+) दाखव/i,
        /(.+) दिखाओ/i, /(.+) चाहिए/i
    ],
    ADD_TO_CART: [
        /add (.+) to cart/i, /put (.+) in cart/i, /buy (.+)/i,
        /(.+) कार्टमध्ये टाका/i, /(.+) ॲड करा/i,
        /(.+) कार्ट में जोड़ें/i, /(.+) ऐड करें/i
    ],
    REMOVE_FROM_CART: [
        /remove (.+) from cart/i, /i don't want (.+)/i, /cancel (.+)/i, /remove (.+)/i, /delete (.+)/i,
        /don't need (.+)/i, /take off (.+)/i, /forget (.+)/i,
        /(.+) काढा/i, /(.+) काढून टाका/i, /(.+) नको आहे/i,
        /(.+) निकालें/i, /(.+) हटाओ/i, /(.+) नहीं चाहिए/i
    ],
    SHOW_CART: [
        /show cart/i, /check cart/i, /what is in my cart/i, /view cart/i,
        /कार्ट दाखवा/i, /माझे कार्ट/i,
        /कार्ट दिखाओ/i, /मेरा कार्ट/i
    ],
    CLEAR_CART: [
        /clear cart/i, /empty cart/i, /removeすべて/i,
        /कार्ट रिकामे करा/i, /कार्ट साफ करा/i,
        /कार्ट खाली करो/i, /कार्ट साफ करो/i
    ],
    RISK_ANALYSIS: [
        /analyze risk/i, /check health/i, /how am i/i, /risk analysis/i,
        /आरोग्य तपासा/i, /रिस्क तपासा/i,
        /चेक हेल्थ/i, /रिस्क चेक करें/i
    ],
    REFILL_CHECK: [
        /refill/i, /when to order/i, /stock/i,
        /रिफिल केव्हा करायचे/i, /औषध संपले/i,
        /रिफिल कब करना है/i, /दवा खत्म हो गई/i
    ],
    TRUST_QUERY: [
        /why trust/i, /is it safe/i, /how it works/i, /system trust/i,
        /विश्वास का ठेवावा/i, /हे सुरक्षित आहे का/i,
        /भरोसा क्यों करें/i, /क्या यह सुरक्षित है/i
    ],
    GREETING: [
        /hi/i, /hello/i, /hey/i, /good morning/i, /good evening/i, /how are you/i,
        /नमस्कार/i, /नमस्ते/i, /शुभ सकाळ/i, /शुभ संध्याकाळ/i
    ]
};

export const IntentEngine = {
    classify(text) {
        for (const [intent, patterns] of Object.entries(INTENT_PATTERNS)) {
            for (const pattern of patterns) {
                const match = text.match(pattern);
                if (match) {
                    return {
                        intent,
                        entities: match.slice(1).filter(e => e)
                    };
                }
            }
        }

        // Simple keyword fallback
        const lower = text.toLowerCase();
        if (lower.includes('order') || lower.includes('orde') || lower.includes('medicine')) return { intent: 'SEARCH', entities: [] };
        if (lower.includes('cart')) return { intent: 'SHOW_CART', entities: [] };

        return { intent: 'UNKNOWN', entities: [] };
    }
};
