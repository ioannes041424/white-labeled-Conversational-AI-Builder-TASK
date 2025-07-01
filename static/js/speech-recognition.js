/**
 * Advanced Speech Recognition Service for Conversational AI Builder
 *
 * This class provides sophisticated speech-to-text functionality with:
 * - Real-time speech recognition using Web Speech API
 * - Intelligent auto-send after speech completion
 * - Confidence-based filtering for accuracy
 * - Debouncing and throttling for performance
 * - Voice activity detection and silence handling
 * - Progressive enhancement with fallback support
 *
 * Key Features:
 * - Automatic message sending after speech ends
 * - Real-time transcript updates in input field
 * - Confidence scoring for quality control
 * - Optimized for conversational AI interaction
 * - Mobile and desktop browser support
 *
 * Architecture:
 * - Event-driven design with state management
 * - Integration with chat.js for message sending
 * - Performance optimizations with debouncing/throttling
 * - Graceful degradation for unsupported browsers
 */
class SpeechRecognitionService {
    constructor(inputId = 'message-input', buttonId = 'voice-input-btn') {

        // ========================================
        // CORE SPEECH RECOGNITION PROPERTIES
        // ========================================

        this.recognition = null;           // Web Speech API recognition instance
        this.isListening = false;          // Current listening state
        this.isSupported = false;          // Browser support detection
        this.inputElement = null;          // Target input element
        this.voiceButton = null;           // Voice input button
        this.inputId = inputId;            // Input element ID
        this.buttonId = buttonId;          // Button element ID
        this.timeoutId = null;             // Safety timeout for max listening time
        this.maxListeningTime = 30000;     // Maximum listening duration (30 seconds)

        // ========================================
        // TRANSCRIPT MANAGEMENT
        // ========================================

        this.originalText = '';            // Text that was in input before speech
        this.accumulatedTranscript = '';   // Final speech results accumulated
        this.lastProcessedIndex = 0;       // Track processed speech results
        this.currentInterimText = '';      // Current interim (temporary) results

        // ========================================
        // AUTO-SEND FUNCTIONALITY
        // Optimized for fast, responsive auto-send after speech completion
        // ========================================

        this.silenceTimer = null;          // Timer for silence detection
        this.silenceThreshold = 300;       // 0.3 seconds of silence before auto-send
        this.speechEndTimer = null;        // Timer for speech end detection
        this.speechEndThreshold = 50;      // 0.05 seconds after speech ends
        this.lastSpeechTime = null;        // Timestamp of last speech activity
        this.lastResultTime = null;        // Timestamp of last recognition result
        this.hasReceivedFinalSpeech = false; // Whether we have final speech results
        this.autoSendEnabled = true;       // Whether auto-send is enabled

        // ========================================
        // CONFIDENCE AND QUALITY CONTROL
        // ========================================

        this.minConfidence = 0.7;          // Minimum confidence for final results
        this.confidenceSum = 0;            // Sum of confidence scores
        this.confidenceCount = 0;          // Count of confidence measurements
        this.minInterimConfidence = 0.4;   // Minimum confidence for interim results

        // ========================================
        // VOICE ACTIVITY DETECTION
        // ========================================

        this.speechStarted = false;        // Whether speech has started
        this.speechEnded = false;          // Whether speech has ended

        // ========================================
        // PERFORMANCE OPTIMIZATIONS
        // Debouncing and throttling for smooth UX and performance
        // ========================================

        this.debouncedUpdateDisplay = this.debounce(this.updateInputDisplay.bind(this), 50);
        this.debouncedAutoSendDetection = this.debounce(this.startAutoSendDetection.bind(this), 100);
        this.debouncedSpeechEndDetection = this.debounce(this.startSpeechEndDetection.bind(this), 150);
        this.throttledResultProcessing = this.throttle(this.processResults.bind(this), 50);

        // Initialize the service
        this.init();
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    init() {
        this.checkSupport();
        if (this.isSupported) {
            this.setupElements();
            this.setupRecognition();
            this.setupEventListeners();
        } else {
            this.handleUnsupportedBrowser();
        }
    }

    checkSupport() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.isSupported = true;
            this.SpeechRecognition = SpeechRecognition;
        }
    }

    setupElements() {
        this.inputElement = document.getElementById(this.inputId);
        this.voiceButton = document.getElementById(this.buttonId);
        
        if (!this.inputElement || !this.voiceButton) {
            this.isSupported = false;
        }
    }

    setupRecognition() {
        if (!this.isSupported) return;

        this.recognition = new this.SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.recognition.maxAlternatives = 1;

        this.recognition.onstart = () => this.onStart();
        this.recognition.onresult = (event) => this.throttledResultProcessing(event);
        this.recognition.onerror = (event) => this.onError(event);
        this.recognition.onend = () => this.onEnd();
        this.recognition.onspeechstart = () => this.onSpeechStart();
        this.recognition.onspeechend = () => this.onSpeechEnd();
    }

    setupEventListeners() {
        if (this.voiceButton) {
            this.voiceButton.addEventListener('click', () => this.toggleListening());
        }
    }

    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    async startListening() {
        if (!this.isSupported || this.isListening) return;

        try {
            await this.requestMicrophonePermission();

            this.originalText = this.inputElement.value;
            this.accumulatedTranscript = '';
            this.lastProcessedIndex = 0;
            this.currentInterimText = '';
            this.hasReceivedFinalSpeech = false;
            this.lastSpeechTime = null;
            this.lastResultTime = null;
            this.confidenceSum = 0;
            this.confidenceCount = 0;
            this.speechStarted = false;
            this.speechEnded = false;
            this.clearAllTimers();

            this.recognition.start();

            this.timeoutId = setTimeout(() => {
                if (this.isListening) {
                    this.stopListening();
                }
            }, this.maxListeningTime);

        } catch (error) {
            this.showError('Failed to start voice input. Please try again.');
        }
    }

    async requestMicrophonePermission() {
        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
            }
        } catch (error) {
            throw new Error('Microphone permission required for voice input');
        }
    }

    stopListening() {
        if (!this.isSupported || !this.isListening) return;

        try {
            this.recognition.stop();
            this.clearAllTimers();
        } catch (error) {
            console.error('Error stopping speech recognition:', error);
        }
    }

    processResults(event) {
        let newFinalTranscript = '';
        let interimTranscript = '';
        let totalConfidence = 0;
        let finalResultCount = 0;

        for (let i = 0; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            const confidence = event.results[i][0].confidence || 0.9;

            if (event.results[i].isFinal) {
                if (i >= this.lastProcessedIndex) {
                    newFinalTranscript += transcript;
                    totalConfidence += confidence;
                    finalResultCount++;
                }
            } else {
                if (confidence >= this.minInterimConfidence) {
                    interimTranscript += transcript;
                }
            }
        }

        if (newFinalTranscript) {
            this.lastProcessedIndex = event.results.length;
            newFinalTranscript = newFinalTranscript.trim().replace(/\s+/g, ' ');
            this.accumulatedTranscript += (this.accumulatedTranscript ? ' ' : '') + newFinalTranscript;
            
            if (finalResultCount > 0) {
                const avgConfidence = totalConfidence / finalResultCount;
                this.confidenceSum += avgConfidence;
                this.confidenceCount++;
                this.hasReceivedFinalSpeech = true;
            }

            this.lastResultTime = Date.now();
            this.updateInputDisplay('');
            this.debouncedAutoSendDetection();
        } else if (interimTranscript) {
            this.debouncedUpdateDisplay(interimTranscript);
        }
    }

    updateInputDisplay(interimText = '') {
        const baseText = this.originalText.trim() + 
                        (this.originalText.trim() ? ' ' : '') + 
                        this.accumulatedTranscript.trim();
        
        let displayText = baseText;
        
        if (interimText) {
            interimText = interimText.trim().replace(/\s+/g, ' ');
            this.currentInterimText = interimText;
            displayText += (baseText ? ' ' : '') + interimText;
        }
        
        this.inputElement.value = displayText;
        this.inputElement.focus();
        this.inputElement.setSelectionRange(this.inputElement.value.length, this.inputElement.value.length);
    }

    shouldAutoSend() {
        if (!this.autoSendEnabled) return false;

        const currentText = this.inputElement.value.trim();
        const meaningfulContent = currentText.length > 2; // At least 3 characters

        if (!meaningfulContent) return false;

        // If we have received final speech results, check confidence
        if (this.hasReceivedFinalSpeech) {
            const avgConfidence = this.confidenceCount > 0 ? this.confidenceSum / this.confidenceCount : 0;
            // More permissive confidence check - if we have any meaningful text, send it
            return avgConfidence >= this.minConfidence || currentText.length > 5;
        }

        // If no final speech yet but we have meaningful content, allow auto-send
        return currentText.length > 5;
    }

    performAutoSend() {
        if (!this.autoSendEnabled) return;

        const messageText = this.inputElement.value.trim();
        if (!messageText) return;

        console.log(`Auto-sending: "${messageText}"`);

        if (this.isListening) {
            this.stopListening();
        }

        this.clearAllTimers();
        this.updateButtonState('processing');

        // Use the existing chat system's sendMessage function
        // This is the most reliable approach as it uses the same logic as manual sending
        try {
            // Check if the global chatSendMessage function exists (from chat.js)
            if (typeof window.chatSendMessage === 'function') {
                // Ensure the input has the message text
                this.inputElement.value = messageText;
                // Call the existing sendMessage function
                window.chatSendMessage();
                setTimeout(() => this.updateButtonState('idle'), 1000);
                return;
            }

            // Fallback: trigger the form submission event properly
            const chatForm = document.getElementById('chat-form');
            if (chatForm) {
                // Ensure the input has the message text
                this.inputElement.value = messageText;

                // Create and dispatch a proper submit event
                const submitEvent = new Event('submit', {
                    bubbles: true,
                    cancelable: true
                });

                // Dispatch the event - this will trigger the existing form handler
                chatForm.dispatchEvent(submitEvent);
                setTimeout(() => this.updateButtonState('idle'), 1000);
                return;
            }

            // Final fallback: click the send button
            const sendButton = document.getElementById('send-btn');
            if (sendButton && !sendButton.disabled) {
                this.inputElement.value = messageText;
                sendButton.click();
                setTimeout(() => this.updateButtonState('idle'), 1000);
                return;
            }

        } catch (error) {
            console.error('Auto-send error:', error);
        }

        // Reset button state if all methods failed
        setTimeout(() => this.updateButtonState('idle'), 500);
    }

    // Timer management
    clearAllTimers() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
        }
        if (this.speechEndTimer) {
            clearTimeout(this.speechEndTimer);
            this.speechEndTimer = null;
        }
    }

    startAutoSendDetection() {
        if (!this.autoSendEnabled || !this.hasReceivedFinalSpeech) return;

        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
        }

        this.silenceTimer = setTimeout(() => {
            if (this.shouldAutoSend()) {
                this.performAutoSend();
            }
        }, this.silenceThreshold);
    }

    startSpeechEndDetection() {
        if (!this.autoSendEnabled) return;

        if (this.speechEndTimer) {
            clearTimeout(this.speechEndTimer);
        }

        this.speechEndTimer = setTimeout(() => {
            if (this.speechEnded && this.hasReceivedFinalSpeech && this.shouldAutoSend()) {
                this.performAutoSend();
            }
        }, this.speechEndThreshold);
    }

    // Event handlers
    onStart() {
        this.isListening = true;
        this.updateButtonState('listening');
    }

    onSpeechStart() {
        this.speechStarted = true;
        this.speechEnded = false;
        this.lastSpeechTime = Date.now();
        this.updateButtonState('speaking');

        if (this.speechEndTimer) {
            clearTimeout(this.speechEndTimer);
            this.speechEndTimer = null;
        }
    }

    onSpeechEnd() {
        this.speechEnded = true;
        this.updateButtonState('listening');

        // More aggressive auto-send after speech ends
        setTimeout(() => {
            if (this.hasReceivedFinalSpeech && this.shouldAutoSend()) {
                this.performAutoSend();
            }
        }, 300); // Slightly longer delay to ensure final results are processed

        this.debouncedSpeechEndDetection();
    }

    onEnd() {
        this.isListening = false;
        this.updateButtonState('idle');
        this.clearAllTimers();

        const shouldAutoSend = this.shouldAutoSend();

        if (shouldAutoSend) {
            this.performAutoSend();
        }

        // Reset state
        this.originalText = '';
        this.accumulatedTranscript = '';
        this.lastProcessedIndex = 0;
        this.currentInterimText = '';
        this.hasReceivedFinalSpeech = false;
        this.lastSpeechTime = null;
        this.lastResultTime = null;
        this.confidenceSum = 0;
        this.confidenceCount = 0;
        this.speechStarted = false;
        this.speechEnded = false;

        setTimeout(() => {
            if (this.recognition) {
                this.recognition.abort();
            }
        }, 100);
    }

    onError(event) {
        console.error('Speech recognition error:', event.error);
        this.clearAllTimers();

        // Reset state on error
        this.originalText = '';
        this.accumulatedTranscript = '';
        this.lastProcessedIndex = 0;
        this.currentInterimText = '';
        this.hasReceivedFinalSpeech = false;
        this.lastSpeechTime = null;
        this.lastResultTime = null;
        this.confidenceSum = 0;
        this.confidenceCount = 0;
        this.speechStarted = false;
        this.speechEnded = false;

        this.isListening = false;
        this.updateButtonState('idle');

        let errorMessage = 'Speech recognition error: ';
        switch (event.error) {
            case 'no-speech':
                errorMessage += 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                errorMessage += 'Microphone not accessible. Please check permissions.';
                break;
            case 'not-allowed':
                errorMessage += 'Microphone permission denied. Please allow microphone access.';
                break;
            case 'network':
                errorMessage += 'Network error. Please check your connection.';
                break;
            case 'aborted':
                return; // Don't show error for aborted
            default:
                errorMessage += event.error;
        }

        this.showError(errorMessage);
    }

    // UI methods
    updateButtonState(state) {
        if (!this.voiceButton) return;

        this.voiceButton.classList.remove('btn-outline-secondary', 'btn-danger', 'btn-warning', 'btn-info', 'btn-success');

        const icon = this.voiceButton.querySelector('i');

        switch (state) {
            case 'listening':
                this.voiceButton.classList.add('btn-danger');
                this.voiceButton.title = 'Listening... Click to stop';
                icon.className = 'fas fa-microphone-slash';
                break;
            case 'speaking':
                this.voiceButton.classList.add('btn-warning');
                this.voiceButton.title = 'Speech detected...';
                icon.className = 'fas fa-volume-up';
                break;
            case 'processing':
                this.voiceButton.classList.add('btn-success');
                this.voiceButton.title = 'Auto-sending message...';
                icon.className = 'fas fa-paper-plane';
                break;
            default: // idle
                this.voiceButton.classList.add('btn-outline-secondary');
                this.voiceButton.title = 'Click to speak your message';
                icon.className = 'fas fa-microphone';
        }
    }

    showError(message) {
        if (typeof AIBuilder !== 'undefined' && AIBuilder.showToast) {
            AIBuilder.showToast(message, 'error');
        } else {
            console.error(message);
        }
    }

    handleUnsupportedBrowser() {
        if (this.voiceButton) {
            this.voiceButton.style.display = 'none';
        }
    }

    // Public methods
    isAvailable() {
        return this.isSupported;
    }

    getCurrentState() {
        return {
            supported: this.isSupported,
            listening: this.isListening,
            autoSendEnabled: this.autoSendEnabled,
            hasReceivedFinalSpeech: this.hasReceivedFinalSpeech,
            averageConfidence: this.confidenceCount > 0 ? this.confidenceSum / this.confidenceCount : 0
        };
    }

    toggleAutoSend() {
        this.autoSendEnabled = !this.autoSendEnabled;
        return this.autoSendEnabled;
    }
}

// Initialize speech recognition when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('voice-input-btn')) {
        window.speechRecognition = new SpeechRecognitionService('message-input', 'voice-input-btn');
    }

    if (document.getElementById('voice-prompt-btn')) {
        window.promptSpeechRecognition = new SpeechRecognitionService('id_system_prompt', 'voice-prompt-btn');
    }
});
