/**
 * Main JavaScript functionality for Mock Interview Practice
 */

// Global utilities
window.InterviewApp = {
    // Format timestamp for display
    formatTime: function(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem;
            background: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#2ecc71' : '#3498db'};
            color: white;
            border-radius: 6px;
            z-index: 1001;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    },
    
    // Validate form inputs
    validateForm: function(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.style.borderColor = '#e74c3c';
                isValid = false;
            } else {
                field.style.borderColor = '#ddd';
            }
        });
        
        return isValid;
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Mock Interview Practice app initialized');
    
    // Setup form validation if present
    const setupForm = document.querySelector('.setup-form');
    if (setupForm) {
        setupForm.addEventListener('submit', function(e) {
            if (!InterviewApp.validateForm(this)) {
                e.preventDefault();
                InterviewApp.showNotification('Please fill in all required fields', 'error');
            }
        });
        
        // Real-time validation
        const requiredFields = setupForm.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', function() {
                if (!this.value.trim()) {
                    this.style.borderColor = '#e74c3c';
                } else {
                    this.style.borderColor = '#2ecc71';
                }
            });
        });
    }
    
    // API key security warning
    const apiKeyField = document.getElementById('api_key');
    if (apiKeyField) {
        apiKeyField.addEventListener('focus', function() {
            if (!this.hasAttribute('data-warning-shown')) {
                InterviewApp.showNotification(
                    'Your API key is only used for this session and is not stored permanently', 
                    'info'
                );
                this.setAttribute('data-warning-shown', 'true');
            }
        });
    }
    
    // File upload feedback
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            if (fileName) {
                InterviewApp.showNotification(`File "${fileName}" selected`, 'success');
            }
        });
    });
});

// Handle page visibility changes (useful for WebSocket management)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden - may need to handle WebSocket reconnection');
    } else {
        console.log('Page visible - check connection status');
    }
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    InterviewApp.showNotification('An unexpected error occurred', 'error');
});

// Handle beforeunload for interview pages
window.addEventListener('beforeunload', function(e) {
    if (window.location.pathname.includes('/interview/')) {
        e.preventDefault();
        e.returnValue = 'Are you sure you want to leave the interview?';
        return e.returnValue;
    }
});