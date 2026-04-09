import { LanguageDetector } from './languageDetector.js';
import { IntentEngine } from './intentEngine.js';
import { ActionExecutor } from './actionExecutor.js';
import { HealthEngine } from './healthEngine.js';
import Store from '../context/State.js';
import api from '../services/api.js';

export const ChatController = {
    state: {
        language: 'en',
        context: null,
        lastResult: JSON.parse(localStorage.getItem('chat_last_result')) || null,
        history: []
    },

    saveState() {
        if (this.state.lastResult) {
            localStorage.setItem('chat_last_result', JSON.stringify(this.state.lastResult));
        } else {
            localStorage.removeItem('chat_last_result');
        }
    },

    async processMessage(text) {
        // ... (rest of implementation remains same but calls saveState)
        // 1. Detect Language
        const lang = LanguageDetector.detect(text);
        this.state.language = lang;
        const responses = LanguageDetector.getResponses(lang);

        // 2. Handle Multiturn Context (Dosage)
        if (this.state.context === 'AWAITING_DOSAGE' && this.state.lastResult?.id) {
            const dosage = parseInt(text.match(/\d+/)?.[0]);
            if (!isNaN(dosage)) {
                await HealthEngine.setDosage(this.state.lastResult.id, dosage);
                this.state.context = null;
                this.saveState();
                return {
                    botMsg: responses.added + " " + responses.refill_needed,
                    type: 'system'
                };
            }
        }

        // 3. Update History & Call AI API
        try {
            this.state.history.push({ role: 'user', content: text });
            // keep history size reasonable (last 10 messages)
            if (this.state.history.length > 10) this.state.history.shift();

            const res = await api.chat(text, {
                context: this.state.context,
                last_item: this.state.lastResult,
                history: this.state.history
            });

            // Gemini/Llama might return a structured response (action + message) or just a message
            let botMsg = res.message || responses.welcome;
            this.state.history.push({ role: 'assistant', content: botMsg });
            if (this.state.history.length > 10) this.state.history.shift();
            let type = 'text';
            let data = res.data || null;

            if (res.action === 'upload_prescription') {
                this.state.context = 'AWAITING_PRESCRIPTION';
                this.state.lastResult = res.data;
                this.saveState();
                type = 'prescription_upload';
            } else if (res.action === 'add_to_cart') {
                const execution = await ActionExecutor.execute({
                    intent: 'ADD_TO_CART',
                    entities: [res.medicine_name || res.medicine_id],
                    qty: res.qty || 1
                }, this.state);

                botMsg = res.message || execution.message;
                if (execution.status === 'success') {
                    botMsg += " " + responses.ask_dosage;
                    this.state.context = 'AWAITING_DOSAGE';
                    this.state.lastResult = execution.data;
                    this.saveState();
                }
            } else if (res.action === 'remove_from_cart') {
                const execution = await ActionExecutor.execute({
                    intent: 'REMOVE_FROM_CART',
                    entities: [res.medicine_name || res.medicine_id],
                    qty: res.qty || 1
                }, this.state);
                botMsg = res.message || execution.message;
            } else if (res.action === 'clear_cart') {
                const execution = await ActionExecutor.execute({
                    intent: 'CLEAR_CART'
                }, this.state);
                botMsg = res.message || execution.message;
                this.state.lastResult = null;
                this.saveState();
            } else if (res.action === 'track_order') {
                const execution = await ActionExecutor.execute({
                    intent: 'TRACK_ORDER',
                    order_id: res.order_id
                }, this.state);
                botMsg = execution.message;
                type = 'track_info';
                data = execution.data;
            }

            return { botMsg, type, data, action_taken: res.action_taken };
        } catch (error) {
            console.error("Chat API Error:", error);

            // If it's a connection error, give a specific hint
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                return {
                    botMsg: "I'm having trouble connecting to my healthcare records. Please ensure the backend server is running on port 8000.",
                    type: 'text'
                };
            }

            // Fallback to local IntentEngine if Gemini fails for other reasons
            const intentObj = IntentEngine.classify(text);
            const execution = await ActionExecutor.execute(intentObj, this.state);
            return { botMsg: execution.message || responses.welcome, type: 'text' };
        }
    },

    async verifyPrescription(file) {
        const responses = LanguageDetector.getResponses(this.state.language);
        try {
            // Load state from storage if memory is clean
            if (!this.state.lastResult) {
                this.state.lastResult = JSON.parse(localStorage.getItem('chat_last_result'));
            }

            // Try to find the medicine name we were trying to add
            let medName = '';
            if (this.state.lastResult?.medicine_name) {
                medName = this.state.lastResult.medicine_name;
            } else if (this.state.lastResult?.name) {
                medName = this.state.lastResult.name;
            } else if (this.state.lastResult?.id) {
                const medicine = Store.state.medicines.find(m => m.id == this.state.lastResult.id);
                if (medicine) medName = medicine.name;
            }

            console.log(`DEBUG: Uploading prescription for medicine: "${medName}"`);

            const res = await api.uploadPrescription(file, medName);
            if (res.valid) {
                this.state.context = 'VERIFIED_PRESCRIPTION';
                // If we had a pending item, we can now add it
                if (this.state.lastResult?.id) {
                    const medicine = Store.state.medicines.find(m => m.id == this.state.lastResult.id);
                    if (medicine) {
                        await ActionExecutor.execute({
                            intent: 'ADD_TO_CART',
                            entities: [medicine.name],
                            force_bypass_rx: true
                        }, this.state);
                    }
                }
                localStorage.removeItem('chat_last_result'); // Clear after success
                return { botMsg: res.message || responses.prescription_success, type: 'text' };
            } else {
                return { botMsg: res.message || responses.prescription_failed, type: 'text' };
            }
        } catch (error) {
            console.error("Upload Error:", error);
            return { botMsg: responses.prescription_failed, type: 'text' };
        }
    }
};
