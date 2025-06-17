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

            // Additional mobile compatibility checks
            const userAgent = navigator.userAgent.toLowerCase();
            const isIOS = /iphone|ipad|ipod/.test(userAgent);
            const isAndroid = /android/.test(userAgent);

            if (isIOS) {
                console.log('✅ Web Speech API supported on iOS device');
                // iOS has some limitations with continuous recognition
            } else if (isAndroid) {
                console.log('✅ Web Speech API supported on Android device');
                // Android generally has better speech recognition support
            } else {
                console.log('✅ Web Speech API supported on desktop');
            }
        } else {
            this.isSupported = false;
            console.warn('❌ Web Speech API not supported in this browser');
        }
    }

    setupRecognition() {
        if (!this.isSupported) return;

        // Create recognition instance
        this.recognition = new this.SpeechRecognition();

        // Detect mobile devices for optimized settings
        this.isMobile = this.detectMobile();

        // Configure recognition settings optimized for mobile compatibility
        this.recognition.continuous = !this.isMobile;     // Disable continuous on mobile to prevent repetition
        this.recognition.interimResults = !this.isMobile; // Disable interim results on mobile for stability
        this.recognition.lang = 'en-US';                  // Default language
        this.recognition.maxAlternatives = 1;             // Only need best result

        // Mobile-specific optimizations
        if (this.isMobile) {
            this.maxListeningTime = 10000; // Shorter timeout for mobile (10 seconds)
        }

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

    detectMobile() {
        // Comprehensive mobile detection
        const userAgent = navigator.userAgent.toLowerCase();
        const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isSmallScreen = window.innerWidth <= 768;

        const isMobile = isMobileUA || (isTouchDevice && isSmallScreen);
        console.log(`📱 Device detection: ${isMobile ? 'Mobile' : 'Desktop'} (UA: ${isMobileUA}, Touch: ${isTouchDevice}, Small: ${isSmallScreen})`);

        return isMobile;
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

    async startListening() {
        if (!this.isSupported || this.isListening) return;

        try {
            console.log('🎤 Starting speech recognition...');

            // Request microphone permission explicitly (especially important for mobile)
            if (this.isMobile) {
                await this.requestMicrophonePermission();
            }

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

    async requestMicrophonePermission() {
        try {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // Stop the stream immediately - we just needed permission
                stream.getTracks().forEach(track => track.stop());
                console.log('📱 Microphone permission granted');
            }
        } catch (error) {
            console.warn('📱 Microphone permission request failed:', error);
            throw new Error('Microphone permission required for voice input');
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
        if (this.isMobile) {
            // Mobile-optimized result handling - simpler and more reliable
            this.handleMobileResults(event);
        } else {
            // Desktop result handling with interim results
            this.handleDesktopResults(event);
        }
    }

    handleMobileResults(event) {
        // For mobile: only process final results to prevent repetition
        let finalTranscript = '';

        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            }
        }

        if (finalTranscript) {
            console.log('📱 Mobile final speech result:', finalTranscript);

            // Clean up the transcript (remove extra spaces, trim)
            finalTranscript = finalTranscript.trim().replace(/\s+/g, ' ');

            // For mobile, replace the entire input content to prevent duplication
            const existingText = this.originalText.trim();
            const newText = existingText + (existingText ? ' ' : '') + finalTranscript;

            this.inputElement.value = newText;
            this.inputElement.focus();
            this.inputElement.setSelectionRange(this.inputElement.value.length, this.inputElement.value.length);

            // Stop listening after getting final result on mobile
            setTimeout(() => {
                if (this.isListening) {
                    this.stopListening();
                }
            }, 500);
        }
    }

    handleDesktopResults(event) {
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
            console.log('💻 Desktop final speech result:', newFinalTranscript);
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
            console.log('⏳ Desktop interim speech result:', interimTranscript);

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
        let shouldShowError = true;

        switch (event.error) {
            case 'no-speech':
                if (this.isMobile) {
                    // On mobile, no-speech is common and less concerning
                    errorMessage = 'No speech detected. Tap the microphone to try again.';
                } else {
                    errorMessage += 'No speech detected. Please try again.';
                }
                break;
            case 'audio-capture':
                errorMessage += 'Microphone not accessible. Please check permissions.';
                break;
            case 'not-allowed':
                errorMessage += 'Microphone permission denied. Please allow microphone access.';
                break;
            case 'network':
                if (this.isMobile) {
                    errorMessage += 'Network error. Check your connection and try again.';
                } else {
                    errorMessage += 'Network error. Please check your connection.';
                }
                break;
            case 'aborted':
                // Don't show error for aborted - it's usually intentional
                shouldShowError = false;
                break;
            case 'service-not-allowed':
                errorMessage += 'Speech service not available. Please try again later.';
                break;
            default:
                errorMessage += event.error;
        }

        if (shouldShowError) {
            this.showError(errorMessage);
        }
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

        // Mobile-specific handling: prevent auto-restart issues
        if (this.isMobile) {
            // On mobile, ensure we don't accidentally restart
            setTimeout(() => {
                if (this.recognition) {
                    this.recognition.abort(); // Ensure complete stop
                }
            }, 100);
        }

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
            listening: this.isListening,
            isMobile: this.isMobile
        };
    }

    // Get mobile-specific usage tips
    getMobileUsageTips() {
        if (!this.isMobile) return null;

        return {
            tips: [
                "Speak clearly and at normal volume",
                "Keep your device close to your mouth",
                "Avoid background noise when possible",
                "Tap the microphone button to start/stop",
                "Speech will stop automatically after a pause"
            ],
            limitations: [
                "Continuous listening may not work on all mobile browsers",
                "Some mobile browsers require user interaction to start recording",
                "Background apps may interfere with microphone access"
            ]
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
