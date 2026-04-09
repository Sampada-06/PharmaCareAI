/**
 * Language Detector & Response Mapper
 * Supports: English (en), Hindi (hi), Marathi (mr)
 */

const LANG_PATTERNS = {
    mr: /[\u0900-\u097F]/, // General Devanagari (Marathi/Hindi) - will refine with specific keywords
    hi: /[\u0900-\u097F]/,
};

// Common keywords for refinement
const KEYWORDS = {
    mr: ['पाहिजे', 'दाखवा', 'औषध', 'तापासाठी', 'मला', 'pahije', 'dakhav', 'dakhaoa', 'dakhaun', 'mala', 'mazya', 'tapasathi', 'taapasathi', 'tappasathi'],
    hi: ['चाहिए', 'दिखाओ', 'दवा', 'बुखार', 'मुझे', 'chahiye', 'dikhao', 'mujhe', 'mere', 'bukhar', 'bukhaar', 'chahie']
};

export const LanguageDetector = {
    detect(text) {
        const lowerText = text.toLowerCase();

        // Check for Marathi specifics
        if (KEYWORDS.mr.some(k => lowerText.includes(k))) return 'mr';

        // Check for Hindi specifics
        if (KEYWORDS.hi.some(k => lowerText.includes(k))) return 'hi';

        // Fallback to Devanagari detection for broad HI/MR vs EN
        if (LANG_PATTERNS.mr.test(text)) return 'hi'; // Default Devanagari to Hindi if unknown

        return 'en';
    },

    getResponses(lang) {
        const responses = {
            en: {
                welcome: "How can I help you with your healthcare needs today?",
                searching: "Searching for medicines...",
                not_found: "I couldn't find any medicines matching that.",
                added: "Added to your cart successfully.",
                prescription_needed: "This medicine requires a prescription. Please upload it using the panel on the right.",
                removed: "I've removed that from your cart for you.",
                refill_needed: "Based on your dosage, you might need a refill soon.",
                interaction_warning: "Warning: Potential interaction detected between these medicines.",
                risk_high: "Caution: Your health risk index is high. Please consult a professional.",
                ask_dosage: "How many times per day do you take this medicine?",
                trust: "PharmaCare uses real-time predictive refills, AI risk scoring, and interaction detection to ensure your safety.",
                out_of_stock: "This medicine is currently out of stock.",
                expired: "This medicine has expired and cannot be sold.",
                prescription_success: "Prescription verified successfully! I've added the medicine to your cart. How many units do you need?",
                prescription_failed: "I couldn't verify the prescription details. Please ensure the doctor's name, medicine name, and date are clearly visible."
            },
            hi: {
                welcome: "आज मैं आपकी स्वास्थ्य संबंधी जरूरतों में क्या सहायता कर सकता हूँ?",
                searching: "दवाइयां खोजी जा रही हैं...",
                not_found: "मुझे इससे मिलती-जुलती कोई दवाई नहीं मिली।",
                added: "आपकी टोकरी में सफलतापूर्वक जोड़ दिया गया है।",
                prescription_needed: "इस दवा के लिए नुस्खे (Prescription) की आवश्यकता है। कृपया दाईं ओर दिए गए पैनल का उपयोग करके इसे अपलोड करें।",
                removed: "मैंने इसे आपके कार्ट से निकाल दिया है।",
                refill_needed: "आपकी खुराक के आधार पर, आपको जल्द ही रिफिल की आवश्यकता हो सकती है।",
                interaction_warning: "चेतावनी: इन दवाइयों के बीच संभावित प्रतिक्रिया पाई गई है।",
                risk_high: "सावधान: आपका स्वास्थ्य जोखिम सूचकांक उच्च है। कृपया किसी विशेषज्ञ से सलाह लें।",
                ask_dosage: "आप दिन में कितनी बार यह दवा लेते हैं?",
                trust: "फार्माकेयर आपकी सुरक्षा सुनिश्चित करने के लिए रीयल-टाइम रिफिल और एआई जोखिम स्कोरिंग का उपयोग करता है।",
                out_of_stock: "यह दवा वर्तमान में स्टॉक में नहीं है।",
                expired: "यह दवा समाप्त (expired) हो गई है और इसे बेचा नहीं जा सकता।",
                prescription_success: "नुस्खे (Prescription) की सफलतापूर्वक पुष्टि हो गई! मैंने दवा आपके कार्ट में जोड़ दी है। आपको कितनी मात्रा चाहिए?",
                prescription_failed: "मैं नुस्खे के विवरण की पुष्टि नहीं कर सका। कृपया सुनिश्चित करें कि डॉक्टर का नाम, दवा का नाम और तारीख स्पष्ट रूप से दिखाई दे रहे हैं।"
            },
            mr: {
                welcome: "आज मी तुमच्या आरोग्याशी संबंधित गरजांमध्ये कशी मदत करू शकतो?",
                searching: "औषधे शोधत आहे...",
                not_found: "मला त्याशी जुळणारे कोणतेही औषध सापडले नाही.",
                added: "तुमच्या कार्टमध्ये यशस्वीरित्या जोडले गेले.",
                prescription_needed: "या औषधासाठी डॉक्टरांच्या प्रिस्क्रिप्शनची आवश्यकता आहे. कृपया उजव्या बाजूच्या पॅनेलचा वापर करून ते अपलोड करा.",
                removed: "मी ते तुमच्या कार्टमधून काढून टाकले आहे.",
                refill_needed: "तुमच्या डोसवर आधारित, तुम्हाला लवकरच रिफिलची आवश्यकता भासू शकते.",
                interaction_warning: "सूचना: या औषधांमध्ये संभाव्य दुष्परिणामांची शक्यता आहे.",
                risk_high: "सावधान: तुमचा आरोग्य जोखीम निर्देशांक उच्च आहे. कृपया तज्ञांचा सल्ला घ्या.",
                ask_dosage: "तुम्ही दिवसातून किती वेळा हे औषध घेता?",
                trust: "तुमच्या सुरक्षेसाठी फार्माकेअर रीयल-टाइम प्रेडिक्टिव रिफिल आणि एआई रिस्क स्कोरिंग वापरते.",
                out_of_stock: "हे औषध सध्या स्टॉक मध्ये नाही.",
                expired: "हे औषध कालबाह्य (expired) झाले आहे आणि विकले जाऊ शकत नाही.",
                prescription_success: "प्रिस्क्रिप्शनची यशस्वीरित्या पडताळणी झाली! मी तुमच्या कार्टमध्ये औषध जोडले आहे. तुम्हाला किती डोस पाहिजे?",
                prescription_failed: "मी प्रिस्क्रिप्शन तपशीलांची पडताळणी करू शकलो नाही. कृपया डॉक्टरांचे नाव, औषधाचे नाव आणि तारीख स्पष्ट असल्याचे सुनिश्चित करा."
            }
        };
        return responses[lang] || responses.en;
    }
};
