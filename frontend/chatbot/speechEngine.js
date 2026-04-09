/**
 * Speech Engine
 * Handles Text-to-Speech (TTS) and Speech-to-Text (STT)
 */

export const SpeechEngine = {
    recognition: null,
    isListening: false,
    _lastText: null,

    initSTT(onResult, onEnd) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Speech Recognition not supported in this browser.");
            return false;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            if (onResult) onResult(text);
        };

        this.recognition.onend = () => {
            this.isListening = false;
            if (onEnd) onEnd();
        };

        return true;
    },

    startListening(lang = 'en-US') {
        if (!this.recognition) return;

        // Map app language to BCP 47 tags
        const langMap = { en: 'en-US', hi: 'hi-IN', mr: 'mr-IN' };
        this.recognition.lang = langMap[lang] || 'en-US';

        try {
            this.recognition.start();
            this.isListening = true;
        } catch (e) {
            console.error("STT Start Error", e);
        }
    },

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    },

    speak(text, lang = 'en') {
        if (!window.speechSynthesis) return;

        // If speaking already, and we call speak again, it usually means we want to STOP
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            // If the text is the same as requested, we just wanted to STOP
            // If text is different, we'll continue below to speak the new text
            if (this._lastText === text) {
                this._lastText = null;
                return;
            }
        }

        this._lastText = text;
        const utterance = new SpeechSynthesisUtterance(text);
        // ... rest of the logic
        const langMap = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };
        utterance.lang = langMap[lang] || 'en-IN';
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => v.lang === utterance.lang) ||
            voices.find(v => v.lang.startsWith(utterance.lang)) ||
            voices[0];
        if (voice) utterance.voice = voice;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onend = () => { this._lastText = null; };

        window.speechSynthesis.speak(utterance);
    }
};
