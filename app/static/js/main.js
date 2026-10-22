// FastAPI Boilerplate v3 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('FastAPI Boilerplate v3 loaded successfully!');
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize navbar
    initializeNavbar();
    
    // Add smooth scrolling
    addSmoothScrolling();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize navbar functionality
 */
function initializeNavbar() {
    // Highlight current page in navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

/**
 * Add smooth scrolling to anchor links
 */
function addSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Utility function to show loading state
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">Loading...</div>
            </div>
        `;
        element.style.display = 'block';
    }
}

/**
 * Utility function to show success message
 */
function showSuccess(elementId, message, data = null) {
    const element = document.getElementById(elementId);
    if (element) {
        let content = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i>
                <strong>Success!</strong> ${message}
        `;
        
        if (data) {
            content += `
                <details class="mt-2">
                    <summary>View Response Data</summary>
                    <pre class="mt-2 mb-0">${JSON.stringify(data, null, 2)}</pre>
                </details>
            `;
        }
        
        content += '</div>';
        element.innerHTML = content;
        element.style.display = 'block';
    }
}

/**
 * Utility function to show error message
 */
function showError(elementId, message, details = null) {
    const element = document.getElementById(elementId);
    if (element) {
        let content = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Error!</strong> ${message}
        `;
        
        if (details) {
            content += `
                <details class="mt-2">
                    <summary>Error Details</summary>
                    <pre class="mt-2 mb-0">${details}</pre>
                </details>
            `;
        }
        
        content += '</div>';
        element.innerHTML = content;
        element.style.display = 'block';
    }
}

/**
 * Generic API call function
 */
async function makeAPICall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        return {
            success: response.ok,
            status: response.status,
            data: data
        };
    } catch (error) {
        return {
            success: false,
            status: 0,
            data: null,
            error: error.message
        };
    }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        return true;
    }
}

/**
 * Show temporary notification
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Export functions for global use
window.FastAPITemplate = {
    showLoading,
    showSuccess,
    showError,
    makeAPICall,
    formatTimestamp,
    copyToClipboard,
    showNotification,
    debounce
};
