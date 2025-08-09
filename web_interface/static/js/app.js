// FreqTrade Web Interface JavaScript

// Global variables
let currentTheme = 'light';
let notificationCount = 0;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load user preferences
    loadUserPreferences();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize auto-refresh if enabled
    initializeAutoRefresh();
    
    // Add keyboard shortcuts
    addKeyboardShortcuts();
    
    // Initialize notification system
    initializeNotifications();
}

// User preferences
function loadUserPreferences() {
    const savedTheme = localStorage.getItem('freqtrade_theme');
    if (savedTheme) {
        currentTheme = savedTheme;
        applyTheme(currentTheme);
    }
    
    const autoRefresh = localStorage.getItem('freqtrade_auto_refresh');
    if (autoRefresh === 'true') {
        enableAutoRefresh();
    }
}

function saveUserPreferences() {
    localStorage.setItem('freqtrade_theme', currentTheme);
}

// Theme management
function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(currentTheme);
    saveUserPreferences();
}

function applyTheme(theme) {
    const body = document.body;
    const navbar = document.querySelector('.navbar');
    
    if (theme === 'dark') {
        body.classList.add('bg-dark-mode');
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-dark');
            navbar.classList.add('navbar-dark', 'bg-secondary');
        }
    } else {
        body.classList.remove('bg-dark-mode');
        if (navbar) {
            navbar.classList.remove('navbar-dark', 'bg-secondary');
            navbar.classList.add('navbar-dark', 'bg-dark');
        }
    }
}

// Tooltip initialization
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"], [title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-refresh functionality
let autoRefreshInterval = null;

function initializeAutoRefresh() {
    const autoRefreshEnabled = localStorage.getItem('freqtrade_auto_refresh') === 'true';
    if (autoRefreshEnabled) {
        enableAutoRefresh();
    }
}

function enableAutoRefresh() {
    if (autoRefreshInterval) return;
    
    autoRefreshInterval = setInterval(() => {
        refreshPageData();
    }, 30000); // Refresh every 30 seconds
    
    localStorage.setItem('freqtrade_auto_refresh', 'true');
    showNotification('Auto-refresh enabled', 'info');
}

function disableAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    
    localStorage.setItem('freqtrade_auto_refresh', 'false');
    showNotification('Auto-refresh disabled', 'info');
}

function toggleAutoRefresh() {
    if (autoRefreshInterval) {
        disableAutoRefresh();
    } else {
        enableAutoRefresh();
    }
}

function refreshPageData() {
    // Only refresh if we're on a data-heavy page and not in a modal
    const modals = document.querySelectorAll('.modal.show');
    if (modals.length > 0) return;
    
    const currentPage = window.location.pathname;
    const refreshablePages = ['/', '/containers', '/strategies', '/pairlists', '/configs'];
    
    if (refreshablePages.includes(currentPage)) {
        // Soft refresh - only update specific components
        softRefreshData();
    }
}

function softRefreshData() {
    // This would update specific components without a full page reload
    // For now, we'll just show a subtle indicator
    const indicator = document.createElement('div');
    indicator.className = 'position-fixed top-0 end-0 m-3 alert alert-info alert-dismissible fade show';
    indicator.style.zIndex = '9999';
    indicator.innerHTML = `
        <i class="fas fa-sync-alt fa-spin"></i> Refreshing data...
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        if (indicator.parentNode) {
            indicator.remove();
        }
    }, 2000);
}

// Keyboard shortcuts
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or F5 - Refresh
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            location.reload();
        }
        
        // Ctrl+N - Create new (if on relevant page)
        if (e.ctrlKey && e.key === 'n') {
            const createBtn = document.querySelector('a[href*="create"], button[onclick*="create"]');
            if (createBtn) {
                e.preventDefault();
                createBtn.click();
            }
        }
        
        // Escape - Close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
        
        // Ctrl+A - Toggle auto-refresh
        if (e.ctrlKey && e.key === 'a' && !e.target.tagName.match(/INPUT|TEXTAREA|SELECT/)) {
            e.preventDefault();
            toggleAutoRefresh();
        }
    });
}

// Notification system
function initializeNotifications() {
    // Request notification permission if not already granted
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
    `;
    
    const icon = getNotificationIcon(type);
    notification.innerHTML = `
        <i class="${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 150);
        }
    }, duration);
    
    // Browser notification for important messages
    if (type === 'danger' || type === 'warning') {
        showBrowserNotification(message, type);
    }
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'fas fa-check-circle',
        'danger': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle',
        'primary': 'fas fa-bell'
    };
    return icons[type] || icons.info;
}

function showBrowserNotification(message, type) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const title = type === 'danger' ? 'Error' : type === 'warning' ? 'Warning' : 'FreqTrade';
        new Notification(title, {
            body: message,
            icon: '/static/favicon.ico',
            tag: 'freqtrade-notification'
        });
    }
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const units = [
        { name: 'day', seconds: 86400 },
        { name: 'hour', seconds: 3600 },
        { name: 'minute', seconds: 60 },
        { name: 'second', seconds: 1 }
    ];
    
    for (const unit of units) {
        const count = Math.floor(seconds / unit.seconds);
        if (count > 0) {
            return `${count} ${unit.name}${count !== 1 ? 's' : ''}`;
        }
    }
    
    return '0 seconds';
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// Form validation helpers
function validateJSON(jsonString) {
    try {
        JSON.parse(jsonString);
        return { valid: true };
    } catch (error) {
        return { valid: false, error: error.message };
    }
}

function validateConfigurationFile(config) {
    const errors = [];
    const warnings = [];
    
    // Required fields
    const requiredFields = ['strategy', 'exchange', 'timeframe'];
    requiredFields.forEach(field => {
        if (!config[field]) {
            errors.push(`Missing required field: ${field}`);
        }
    });
    
    // Exchange validation
    if (config.exchange) {
        if (!config.exchange.name) {
            errors.push('Exchange name is required');
        }
        
        if (!config.exchange.pair_whitelist || config.exchange.pair_whitelist.length === 0) {
            warnings.push('No trading pairs specified');
        }
    }
    
    return { errors, warnings };
}

// Loading states
function showLoadingSpinner(element) {
    const spinner = document.createElement('div');
    spinner.className = 'text-center';
    spinner.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    element.innerHTML = '';
    element.appendChild(spinner);
}

function hideLoadingSpinner(element) {
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.parentNode.remove();
    }
}

// Search functionality
function initializeSearch(inputSelector, targetSelector) {
    const searchInput = document.querySelector(inputSelector);
    const targets = document.querySelectorAll(targetSelector);
    
    if (!searchInput || targets.length === 0) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        targets.forEach(target => {
            const text = target.textContent.toLowerCase();
            const matches = text.includes(searchTerm);
            target.style.display = matches ? '' : 'none';
        });
    });
}

// Export functionality
function exportTableToCSV(tableSelector, filename) {
    const table = document.querySelector(tableSelector);
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
    }).join('\\n');
    
    downloadFile(csv, filename, 'text/csv');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// API helpers
async function fetchWithTimeout(url, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// Make functions globally available
window.FreqTradeApp = {
    toggleTheme,
    toggleAutoRefresh,
    showNotification,
    formatBytes,
    formatDuration,
    formatCurrency,
    formatPercentage,
    validateJSON,
    validateConfigurationFile,
    exportTableToCSV,
    downloadFile,
    fetchWithTimeout,
    initializeSearch,
    showLoadingSpinner,
    hideLoadingSpinner
};
