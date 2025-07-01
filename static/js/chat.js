/**
 * Chat functionality for Conversational AI Builder
 *
 * This module handles the real-time chat interface including:
 * - Message sending and receiving via AJAX
 * - Real-time UI updates and message display
 * - Audio playback for AI responses
 * - Speech recognition integration
 * - Markdown formatting for AI responses
 * - Auto-scroll and typing indicators
 *
 * Architecture:
 * - Event-driven design with proper error handling
 * - Integration with Django backend via JSON API
 * - Automatic audio playback for AI responses
 * - Progressive enhancement for speech features
 * - Responsive design with mobile support
 */

document.addEventListener('DOMContentLoaded', function() {

    // ========================================
    // DOM ELEMENT REFERENCES
    // ========================================

    // Core chat elements
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages-container');
    const loadingIndicator = document.getElementById('loading-indicator');

    // Session and bot identification from Django template
    const sessionId = document.getElementById('session-id').value;
    const botId = document.getElementById('bot-id').value;

    // ========================================
    // INITIAL SETUP AND UX ENHANCEMENTS
    // ========================================

    /**
     * Auto-focus the message input for immediate typing
     * Improves UX by allowing users to start typing immediately
     */
    messageInput.focus();

    /**
     * Scroll to bottom of messages container
     * Ensures the latest messages are always visible
     */
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Perform initial scroll to show latest messages
    scrollToBottom();



    // ========================================
    // EVENT HANDLERS FOR MESSAGE SENDING
    // ========================================

    /**
     * Handle form submission (when user clicks send button)
     * Prevents default form submission and uses AJAX instead
     */
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });

    /**
     * Handle Enter key for quick message sending
     * Enter alone sends message, Shift+Enter adds new line
     * This provides intuitive keyboard shortcuts for users
     */
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // ========================================
    // CORE MESSAGE SENDING FUNCTIONALITY
    // ========================================

    /**
     * Main function to send user messages and handle AI responses
     *
     * Process Flow:
     * 1. Validate and prepare user message
     * 2. Update UI with user message immediately
     * 3. Send AJAX request to Django backend
     * 4. Process AI response and update UI
     * 5. Auto-play generated audio response
     * 6. Handle errors and edge cases
     *
     * This function integrates with:
     * - Django SendMessageView for backend processing
     * - ConversationManager for AI response generation
     * - GoogleCloudTTSService for audio synthesis
     */
    function sendMessage() {
        const message = messageInput.value.trim();

        // Validate message content
        if (!message) return;

        // Update UI state to prevent double-sending
        setFormState(false);

        // Clear input immediately for better UX
        messageInput.value = '';

        // Add user message to UI immediately (optimistic update)
        addMessageToUI('user', message);

        // Show typing indicator while AI processes
        showTypingIndicator();

        // Send AJAX request to Django backend
        fetch(`/chat/${botId}/send/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()  // Django CSRF protection
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId  // Link to conversation session
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            hideTypingIndicator();

            if (data.success) {
                // Add AI response to UI with audio support
                addMessageToUI('ai', data.ai_message.content, data.ai_message.audio_url);

                // MANDATORY: Auto-play audio for every AI response
                // This is a core feature of the conversational AI experience
                if (data.ai_message.audio_url) {
                    // Immediate auto-play for seamless voice interaction
                    autoPlayAudio(data.ai_message.audio_url);
                } else {
                    // Log when audio is missing (should not happen in normal operation)
                    console.warn('⚠️ AI response received without audio - this should not happen');
                    if (data.audio_error) {
                        console.error('🔊 Audio generation error:', data.audio_error);
                    }
                }

            } else {
                // Handle server-side errors
                addErrorMessage(data.error || 'Failed to send message');
            }
        })
        .catch(error => {
            // Handle network and client-side errors
            hideTypingIndicator();
            console.error('❌ Network error:', error);
            addErrorMessage('Network error. Please try again.');
        })
        .finally(() => {
            // Always restore form state and focus
            setFormState(true);
            messageInput.focus();
        });
    }

    /**
     * Expose sendMessage globally for speech recognition integration
     * This allows the speech recognition module to trigger message sending
     * after converting speech to text
     */
    window.chatSendMessage = sendMessage;

    // Add message to UI
    function addMessageToUI(type, content, audioUrl = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });

        let audioButton = '';
        if (audioUrl) {
            audioButton = `
                <button class="btn btn-sm btn-outline-primary ms-2 play-audio-btn"
                        data-audio-url="${audioUrl}"
                        title="Play clean voice response (without markdown formatting)">
                    <i class="fas fa-play"></i>
                </button>
            `;
        }

        const icon = type === 'user' ? 'fa-user' : 'fa-robot';
        const sender = type === 'user' ? 'You' : document.querySelector('h5').textContent.replace('Chat with ', '');

        // Format content based on message type
        let formattedContent;
        if (type === 'ai') {
            formattedContent = formatMarkdown(content);
        } else {
            formattedContent = escapeHtml(content);
        }

        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${formattedContent}</div>
                <div class="message-meta">
                    <small class="text-muted">
                        <i class="fas ${icon} me-1"></i>${sender}
                        • ${timeString}
                        ${audioButton}
                    </small>
                </div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();

        // Add audio functionality if present
        if (audioUrl) {
            const audioBtn = messageDiv.querySelector('.play-audio-btn');
            audioBtn.addEventListener('click', function() {
                playAudio(audioUrl, this);
            });
        }
    }

    // Format markdown content
    function formatMarkdown(text) {
        // Escape HTML first
        text = escapeHtml(text);

        // Convert markdown to HTML
        // Bold text **text** or __text__
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');

        // Italic text *text* or _text_
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        text = text.replace(/_(.*?)_/g, '<em>$1</em>');

        // Code blocks ```code```
        text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline code `code`
        text = text.replace(/`(.*?)`/g, '<code>$1</code>');

        // Headers
        text = text.replace(/^### (.*$)/gm, '<h6>$1</h6>');
        text = text.replace(/^## (.*$)/gm, '<h5>$1</h5>');
        text = text.replace(/^# (.*$)/gm, '<h4>$1</h4>');

        // Split into paragraphs first
        const paragraphs = text.split(/\n\s*\n/);
        const formattedParagraphs = [];

        for (let para of paragraphs) {
            para = para.trim();
            if (!para) continue;

            // Check if this paragraph contains list items
            const listItems = para.match(/^[\s]*[-*+]\s+(.*)$/gm);
            if (listItems) {
                // Format as unordered list
                const listContent = listItems.map(item => {
                    const content = item.replace(/^[\s]*[-*+]\s+/, '');
                    return `<li>${content}</li>`;
                }).join('');
                formattedParagraphs.push(`<ul>${listContent}</ul>`);
            } else {
                // Check for numbered lists
                const numberedItems = para.match(/^[\s]*\d+\.\s+(.*)$/gm);
                if (numberedItems) {
                    const listContent = numberedItems.map(item => {
                        const content = item.replace(/^[\s]*\d+\.\s+/, '');
                        return `<li>${content}</li>`;
                    }).join('');
                    formattedParagraphs.push(`<ol start="1">${listContent}</ol>`);
                } else {
                    // Regular paragraph - handle line breaks
                    if (!para.match(/^<(h[1-6]|ul|ol|pre)/)) {
                        para = para.replace(/\n/g, '<br>');
                        para = `<p>${para}</p>`;
                    } else {
                        para = para.replace(/\n/g, '<br>');
                    }
                    formattedParagraphs.push(para);
                }
            }
        }

        text = formattedParagraphs.join('');

        // Links [text](url)
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

        // Clean up empty paragraphs
        text = text.replace(/<p>\s*<\/p>/g, '');

        return text;
    }

    // Show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message typing-indicator-message';
        typingDiv.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <small class="text-muted ms-2">AI is thinking...</small>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        scrollToBottom();
        loadingIndicator.style.display = 'block';
    }

    // Hide typing indicator
    function hideTypingIndicator() {
        const typingIndicator = messagesContainer.querySelector('.typing-indicator-message');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        loadingIndicator.style.display = 'none';
    }

    // Add error message
    function addErrorMessage(error) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-2';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${escapeHtml(error)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        messagesContainer.appendChild(errorDiv);
        scrollToBottom();

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    // Set form state (enabled/disabled)
    function setFormState(enabled) {
        messageInput.disabled = !enabled;
        sendBtn.disabled = !enabled;
        
        if (enabled) {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        } else {
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
    }

    // Auto-play audio (for new AI responses) - Enhanced for better reliability
    function autoPlayAudio(audioUrl) {
        try {
            console.log('Attempting to auto-play AI voice response:', audioUrl);

            // Create audio element for auto-play
            const audio = new Audio(audioUrl);
            audio.volume = 0.9; // Good volume for voice responses
            audio.preload = 'auto'; // Preload for faster playback

            // Add event listeners for better debugging
            audio.addEventListener('loadstart', () => {
                console.log('Audio loading started');
            });

            audio.addEventListener('canplay', () => {
                console.log('Audio can start playing');
            });

            audio.addEventListener('error', (e) => {
                console.error('Audio loading error:', e);
                showAudioFallbackNotification();
            });

            // Attempt to play immediately
            const playPromise = audio.play();

            if (playPromise !== undefined) {
                playPromise.then(() => {
                    console.log('✅ Auto-playing AI voice response successfully');

                    // Add visual indicator that audio is playing
                    showAudioPlayingIndicator();

                    // Clean up when audio ends
                    audio.addEventListener('ended', () => {
                        console.log('Auto-play audio finished');
                        hideAudioPlayingIndicator();
                    });

                }).catch(error => {
                    console.warn('Auto-play prevented by browser policy:', error.message);
                    showAudioFallbackNotification();
                });
            }
        } catch (error) {
            console.error('Error in auto-play function:', error);
            showAudioFallbackNotification();
        }
    }

    // Show notification when auto-play fails
    function showAudioFallbackNotification() {
        // Try to use the global toast function if available
        if (typeof AIBuilder !== 'undefined' && AIBuilder.showToast) {
            AIBuilder.showToast('🔊 Voice response ready - click the play button to hear it', 'info');
        } else {
            // Fallback: show a simple browser notification
            console.log('🔊 Voice response available - click play button to hear');
        }
    }

    // Visual indicator for audio playing
    function showAudioPlayingIndicator() {
        // Add a subtle visual indicator that audio is playing
        const indicator = document.createElement('div');
        indicator.id = 'audio-playing-indicator';
        indicator.className = 'audio-playing-indicator';
        indicator.innerHTML = '<i class="fas fa-volume-up"></i> Playing voice response...';
        indicator.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 123, 255, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            z-index: 1050;
            animation: fadeIn 0.3s ease-in;
        `;
        document.body.appendChild(indicator);
    }

    function hideAudioPlayingIndicator() {
        const indicator = document.getElementById('audio-playing-indicator');
        if (indicator) {
            indicator.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 300);
        }
    }

    // Play audio (for manual replay)
    function playAudio(audioUrl, button) {
        const audioPlayer = document.getElementById('audio-player');
        const audioModal = new bootstrap.Modal(document.getElementById('audioModal'));

        // Set audio source and show modal
        audioPlayer.src = audioUrl;
        audioModal.show();

        // Update button state
        button.classList.add('playing');
        button.innerHTML = '<i class="fas fa-pause"></i>';

        // Play audio
        audioPlayer.play().catch(error => {
            console.error('Error playing audio:', error);
            AIBuilder.showToast('Error playing audio', 'error');
        });

        // Reset button when audio ends
        audioPlayer.addEventListener('ended', function() {
            button.classList.remove('playing');
            button.innerHTML = '<i class="fas fa-play"></i>';
        });

        // Reset button when modal is closed
        document.getElementById('audioModal').addEventListener('hidden.bs.modal', function() {
            audioPlayer.pause();
            audioPlayer.currentTime = 0;
            button.classList.remove('playing');
            button.innerHTML = '<i class="fas fa-play"></i>';
        });
    }

    // Handle existing audio buttons
    document.querySelectorAll('.play-audio-btn').forEach(button => {
        button.addEventListener('click', function() {
            const audioUrl = this.getAttribute('data-audio-url');
            playAudio(audioUrl, this);
        });
    });



    // Get CSRF token
    function getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Auto-resize message input
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Handle paste events (for potential file uploads in future)
    messageInput.addEventListener('paste', function() {
        // Future enhancement: handle pasted images/files
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + L to clear chat (if implemented)
        if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
            e.preventDefault();
            // Future enhancement: clear chat functionality
        }
        
        // Ctrl/Cmd + / to focus message input
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            messageInput.focus();
        }
    });

    // Connection status monitoring
    let isOnline = navigator.onLine;
    
    window.addEventListener('online', function() {
        if (!isOnline) {
            isOnline = true;
            AIBuilder.showToast('Connection restored', 'success');
        }
    });
    
    window.addEventListener('offline', function() {
        isOnline = false;
        AIBuilder.showToast('Connection lost. Messages will be sent when connection is restored.', 'warning');
    });

    // Visibility change handling (pause/resume functionality)
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            messageInput.focus();
        }
    });
});
