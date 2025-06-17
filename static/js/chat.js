// Chat functionality for Conversational AI Builder

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sessionId = document.getElementById('session-id').value;
    const botId = document.getElementById('bot-id').value;

    // Auto-focus message input
    messageInput.focus();

    // Scroll to bottom of messages
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Initial scroll to bottom
    scrollToBottom();



    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
    });

    // Handle Enter key (without Shift)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send message function
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Disable form
        setFormState(false);
        
        // Clear input
        messageInput.value = '';

        // Add user message to UI immediately
        addMessageToUI('user', message);

        // Show typing indicator
        showTypingIndicator();

        // Send to server
        fetch(`/chat/${botId}/send/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            hideTypingIndicator();

            if (data.success) {
                // Add AI response to UI
                addMessageToUI('ai', data.ai_message.content, data.ai_message.audio_url);

                // MANDATORY: Auto-play audio for every AI response
                if (data.ai_message.audio_url) {
                    // Immediate auto-play without delay for seamless experience
                    autoPlayAudio(data.ai_message.audio_url);
                } else {
                    // Log when audio is missing (this should not happen)
                    console.warn('AI response received without audio - this should not happen');
                    if (data.audio_error) {
                        console.error('Audio generation error:', data.audio_error);
                    }
                }

            } else {
                // Show error message
                addErrorMessage(data.error || 'Failed to send message');
            }
        })
        .catch(error => {
            hideTypingIndicator();
            console.error('Error:', error);
            addErrorMessage('Network error. Please try again.');
        })
        .finally(() => {
            setFormState(true);
            messageInput.focus();
        });
    }

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
