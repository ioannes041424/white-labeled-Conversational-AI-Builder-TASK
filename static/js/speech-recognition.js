/**
 * Web Speech API Integration for Conversational AI Builder
 * Provides speech-to-text functionality using browser's native Web Speech API
 * No API keys required - completely free!
 */

class SpeechRecognitionService {
    constructor(inputId = 'message-input', buttonId = 'voice-input-btn') {
        this.recognition = null;
        this.isListening = false;
        this.isSupported = false;
        this.inputElement = null;
        this.voiceButton = null;
        this.inputId = inputId;
        this.buttonId = buttonId;
        this.timeoutId = null;
        this.maxListeningTime = 30000; // 30 seconds max listening time
        this.originalText = ''; // Store original text before speech recognition
        this.finalTranscript = ''; // Store accumulated final results

        this.init();
    }

    init() {
        // Check browser support
        this.checkSupport();

        // Get DOM elements
        this.inputElement = document.getElementById(this.inputId);
        this.voiceButton = document.getElementById(this.buttonId);

        if (this.isSupported && this.voiceButton && this.inputElement) {
            this.setupRecognition();
            this.attachEventListeners();
        } else {
            this.handleUnsupportedBrowser();
        }
    }

    checkSupport() {
        // Check for Web Speech API support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (SpeechRecognition) {
            this.isSupported = true;
            this.SpeechRecognition = SpeechRecognition;
            console.log('✅ Web Speech API supported');
        } else {
            this.isSupported = false;
            console.warn('❌ Web Speech API not supported in this browser');
        }
    }

    setupRecognition() {
        if (!this.isSupported) return;

        // Create recognition instance
        this.recognition = new this.SpeechRecognition();

        // Configure recognition settings
        this.recognition.continuous = true;           // Keep listening until manually stopped
        this.recognition.interimResults = true;       // Show interim results
        this.recognition.lang = 'en-US';             // Default language
        this.recognition.maxAlternatives = 1;        // Only need best result
        
        // Set up event handlers
        this.recognition.onstart = () => this.onStart();
        this.recognition.onresult = (event) => this.onResult(event);
        this.recognition.onerror = (event) => this.onError(event);
        this.recognition.onend = () => this.onEnd();
        this.recognition.onspeechstart = () => this.onSpeechStart();
        this.recognition.onspeechend = () => this.onSpeechEnd();
        this.recognition.onaudiostart = () => this.onAudioStart();
        this.recognition.onaudioend = () => this.onAudioEnd();
    }

    attachEventListeners() {
        if (!this.voiceButton) return;

        this.voiceButton.addEventListener('click', () => {
            if (this.isListening) {
                this.stopListening();
            } else {
                this.startListening();
            }
        });

        // Keyboard shortcut: Ctrl/Cmd + M to start voice input
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
                e.preventDefault();
                if (!this.isListening) {
                    this.startListening();
                }
            }
        });
    }

    startListening() {
        if (!this.isSupported || this.isListening) return;

        try {
            console.log('🎤 Starting speech recognition...');

            // Store the original text in the input field
            this.originalText = this.inputElement.value;
            this.finalTranscript = '';

            this.recognition.start();

            // Set timeout to automatically stop after max time
            this.timeoutId = setTimeout(() => {
                if (this.isListening) {
                    console.log('⏰ Speech recognition timeout - stopping automatically');
                    this.stopListening();
                }
            }, this.maxListeningTime);

        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.showError('Failed to start voice input. Please try again.');
        }
    }

    stopListening() {
        if (!this.isSupported || !this.isListening) return;

        try {
            console.log('🛑 Stopping speech recognition...');
            this.recognition.stop();

            // Clear timeout
            if (this.timeoutId) {
                clearTimeout(this.timeoutId);
                this.timeoutId = null;
            }
        } catch (error) {
            console.error('Error stopping speech recognition:', error);
        }
    }

    // Event Handlers
    onStart() {
        console.log('🎤 Speech recognition started');
        this.isListening = true;
        this.updateButtonState('listening');
        // Only show initial notification, no ongoing status messages
    }

    onResult(event) {
        let newFinalTranscript = '';
        let interimTranscript = '';

        // Process all results
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;

            if (event.results[i].isFinal) {
                newFinalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        // Handle final results - add to our accumulated final transcript
        if (newFinalTranscript) {
            console.log('✅ Final speech result:', newFinalTranscript);
            this.finalTranscript += newFinalTranscript;

            // Update input with original text + all final results
            const combinedText = this.originalText.trim() +
                                (this.originalText.trim() ? ' ' : '') +
                                this.finalTranscript.trim();
            this.inputElement.value = combinedText;

            // Focus input for potential editing
            this.inputElement.focus();
            this.inputElement.setSelectionRange(this.inputElement.value.length, this.inputElement.value.length);
        }

        // Handle interim results - show them temporarily
        if (interimTranscript) {
            console.log('⏳ Interim speech result:', interimTranscript);

            // Show original text + final results + current interim
            const displayText = this.originalText.trim() +
                               (this.originalText.trim() ? ' ' : '') +
                               this.finalTranscript.trim() +
                               (this.finalTranscript.trim() ? ' ' : '') +
                               interimTranscript.trim();
            this.inputElement.value = displayText;
        }
    }

    onError(event) {
        console.error('Speech recognition error:', event.error);

        // Reset transcript variables on error
        this.originalText = '';
        this.finalTranscript = '';

        let errorMessage = 'Voice input error: ';
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
                errorMessage += 'Speech recognition was aborted.';
                break;
            default:
                errorMessage += event.error;
        }

        this.showError(errorMessage);
    }

    onEnd() {
        console.log('🏁 Speech recognition ended');
        this.isListening = false;
        this.updateButtonState('idle');

        // Clear timeout
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        // Reset transcript variables for next session
        this.originalText = '';
        this.finalTranscript = '';

        // Don't automatically restart - user must click button again
        // This prevents the annoying auto-restart behavior

        // Clear any lingering status messages after a delay
        setTimeout(() => {
            this.clearStatus();
        }, 3000);
    }

    onSpeechStart() {
        console.log('🗣️ Speech detected');
        this.updateButtonState('speaking');
        // No notification - just visual feedback
    }

    onSpeechEnd() {
        console.log('🤐 Speech ended');
        this.updateButtonState('listening'); // Back to listening, not processing
        // No notification - keep listening for more speech
    }

    onAudioStart() {
        console.log('🔊 Audio capture started');
    }

    onAudioEnd() {
        console.log('🔇 Audio capture ended');
    }

    // UI Helper Methods
    updateButtonState(state) {
        if (!this.voiceButton) return;

        // Remove all state classes
        this.voiceButton.classList.remove('btn-outline-secondary', 'btn-danger', 'btn-warning', 'btn-info');
        
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
                this.voiceButton.classList.add('btn-info');
                this.voiceButton.title = 'Processing speech...';
                icon.className = 'fas fa-spinner fa-spin';
                break;
            default: // idle
                this.voiceButton.classList.add('btn-outline-secondary');
                this.voiceButton.title = 'Click to speak your message';
                icon.className = 'fas fa-microphone';
        }
    }

    showStatus(message, type = 'info') {
        // Use existing toast system if available
        if (typeof AIBuilder !== 'undefined' && AIBuilder.showToast) {
            AIBuilder.showToast(message, type);
        } else {
            console.log(`🎤 ${message}`);
        }
    }

    showError(message) {
        this.showStatus(message, 'error');
    }

    clearStatus() {
        // Clear any status messages if needed
    }

    handleUnsupportedBrowser() {
        if (this.voiceButton) {
            this.voiceButton.style.display = 'none';
            console.warn('Voice input not available in this browser');
        }
    }

    // Public methods for external use
    isAvailable() {
        return this.isSupported;
    }

    getCurrentState() {
        return {
            supported: this.isSupported,
            listening: this.isListening
        };
    }
}

// Initialize speech recognition when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize for chat pages (message input)
    if (document.getElementById('voice-input-btn')) {
        window.speechRecognition = new SpeechRecognitionService('message-input', 'voice-input-btn');
        console.log('🎤 Speech recognition service initialized for chat');
    }

    // Initialize for bot creation/edit pages (system prompt input)
    if (document.getElementById('voice-prompt-btn')) {
        window.promptSpeechRecognition = new SpeechRecognitionService('id_system_prompt', 'voice-prompt-btn');
        console.log('🎤 Speech recognition service initialized for system prompt');
    }
});
