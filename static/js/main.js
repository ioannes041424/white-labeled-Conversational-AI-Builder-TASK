/**
 * Main JavaScript utilities for Conversational AI Builder
 *
 * This file provides core frontend functionality including:
 * - Bootstrap component initialization
 * - Form validation and UX enhancements
 * - UI utilities and helper functions
 * - Global event handlers and keyboard shortcuts
 * - Toast notification system
 *
 * Architecture:
 * - Uses vanilla JavaScript for better performance
 * - Integrates with Bootstrap 5 components
 * - Provides global AIBuilder utility namespace
 * - Handles progressive enhancement patterns
 */

// Wait for DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', function() {

    // ========================================
    // BOOTSTRAP COMPONENT INITIALIZATION
    // ========================================

    /**
     * Initialize Bootstrap tooltips for all elements with data-bs-toggle="tooltip"
     * Tooltips provide helpful hints and additional information on hover
     */
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    /**
     * Initialize Bootstrap popovers for all elements with data-bs-toggle="popover"
     * Popovers provide more detailed information in a dismissible overlay
     */
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // ========================================
    // ALERT AND NOTIFICATION MANAGEMENT
    // ========================================

    /**
     * Auto-dismiss Bootstrap alerts after 5 seconds
     * This improves UX by automatically clearing success/info messages
     * while allowing users to manually dismiss them earlier if needed
     */
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // ========================================
    // FORM VALIDATION AND UX ENHANCEMENTS
    // ========================================

    /**
     * Enhanced form validation using Bootstrap's validation classes
     * Provides real-time feedback and prevents submission of invalid forms
     * Uses HTML5 validation API with Bootstrap styling
     */
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            // Check if form passes HTML5 validation
            if (!form.checkValidity()) {
                event.preventDefault();  // Prevent form submission
                event.stopPropagation(); // Stop event bubbling
            }
            // Add Bootstrap validation styling classes
            form.classList.add('was-validated');
        });
    });

    /**
     * Smooth scrolling for internal anchor links
     * Enhances navigation UX by providing smooth transitions
     * instead of jarring jumps to page sections
     */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',  // Smooth animation
                    block: 'start'       // Align to top of viewport
                });
            }
        });
    });

    /**
     * Loading button states for better user feedback
     * Shows spinner and disables button during async operations
     * Prevents double-clicks and provides visual feedback
     */
    document.querySelectorAll('.btn-loading').forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            // Show loading state with spinner
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
            this.disabled = true;

            // Fallback: Re-enable after 3 seconds if not manually reset
            // This prevents buttons from being permanently disabled
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 3000);
        });
    });

    // Character counter for textareas
    document.querySelectorAll('textarea[maxlength]').forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        const counter = document.createElement('div');
        counter.className = 'form-text text-end';
        counter.innerHTML = `<span class="char-count">0</span>/${maxLength} characters`;
        textarea.parentNode.appendChild(counter);

        const charCountSpan = counter.querySelector('.char-count');
        
        textarea.addEventListener('input', function() {
            const currentLength = this.value.length;
            charCountSpan.textContent = currentLength;
            
            if (currentLength > maxLength * 0.9) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-warning');
            }
            
            if (currentLength >= maxLength) {
                counter.classList.add('text-danger');
                counter.classList.remove('text-warning');
            } else {
                counter.classList.remove('text-danger');
            }
        });
    });

    // Confirmation dialogs
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Auto-resize textareas
    document.querySelectorAll('textarea.auto-resize').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
        
        // Initial resize
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    });

    // Copy to clipboard functionality
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-target'));
            if (target) {
                const text = target.textContent || target.value;
                navigator.clipboard.writeText(text).then(() => {
                    // Show success feedback
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    this.classList.add('btn-success');
                    this.classList.remove('btn-outline-secondary');
                    
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.classList.remove('btn-success');
                        this.classList.add('btn-outline-secondary');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                });
            }
        });
    });

    // Theme toggle (if implemented)
    const themeToggle = document.querySelector('#theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    // Search functionality
    const searchInput = document.querySelector('#search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const searchableItems = document.querySelectorAll('.searchable-item');
            
            searchableItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit forms
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeForm = document.querySelector('form:focus-within');
            if (activeForm) {
                const submitBtn = activeForm.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.click();
                }
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) {
                    modal.hide();
                }
            }
        }
    });
});

// Utility functions
window.AIBuilder = {
    // Show toast notification
    showToast: function(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
        const toast = this.createToast(message, type);
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },

    createToastContainer: function() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    },

    createToast: function(message, type) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        
        const iconMap = {
            success: 'fa-check-circle text-success',
            error: 'fa-exclamation-triangle text-danger',
            warning: 'fa-exclamation-circle text-warning',
            info: 'fa-info-circle text-info'
        };
        
        const icon = iconMap[type] || iconMap.info;
        
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas ${icon} me-2"></i>
                <strong class="me-auto">Notification</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        return toast;
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Debounce function
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }
};
