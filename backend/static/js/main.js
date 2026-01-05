/**
 * AgriSecure Dashboard - Custom JavaScript
 */

// Utility functions
const AgriSecure = {
    // Show loading spinner
    showLoading: function(element) {
        element.innerHTML = '<div class="flex justify-center py-4"><div class="spinner w-8 h-8 border-4 border-agri-200 border-t-agri-600 rounded-full"></div></div>';
    },

    // Format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('it-IT', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Format number
    formatNumber: function(num, decimals = 1) {
        if (num === null || num === undefined) return '-';
        return Number(num).toFixed(decimals);
    },

    // Show toast notification
    toast: function(message, type = 'info') {
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };

        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all transform translate-y-0`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // Confirm dialog
    confirm: function(message) {
        return window.confirm(message);
    },

    // AJAX helper
    ajax: async function(url, options = {}) {
        const defaults = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            }
        };

        // Add CSRF token for POST requests
        if (options.method === 'POST') {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            if (csrfToken) {
                defaults.headers['X-CSRFToken'] = csrfToken;
            }
        }

        const config = { ...defaults, ...options };
        
        try {
            const response = await fetch(url, config);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('AJAX Error:', error);
            throw error;
        }
    }
};

// Auto-refresh functionality
let autoRefreshInterval = null;

function startAutoRefresh(seconds = 60) {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        location.reload();
    }, seconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Add card hover effects
    document.querySelectorAll('.card-hover').forEach(card => {
        card.style.transition = 'all 0.2s ease';
    });

    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Confirm delete actions
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Handle form submissions with loading state
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span> Caricamento...';
            }
        });
    });
});

// Export for use in templates
window.AgriSecure = AgriSecure;
