/**
 * Smart Course Registration - Main JavaScript
 * Utility functions for enhanced UX
 */

(function () {
    'use strict';

    // ============================================
    // Toast Notification System
    // ============================================

    const Toast = {
        container: null,

        init() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.className = 'toast-container';
                document.body.appendChild(this.container);
            }
        },

        show(message, type = 'info', duration = 4000) {
            this.init();

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;

            const icons = {
                success: 'fa-check-circle',
                error: 'fa-exclamation-circle',
                warning: 'fa-exclamation-triangle',
                info: 'fa-info-circle'
            };

            toast.innerHTML = `
                <div class="toast-icon">
                    <i class="fas ${icons[type]}"></i>
                </div>
                <div class="toast-content">
                    <div class="toast-title">${this.getTitle(type)}</div>
                    <div class="toast-message">${message}</div>
                </div>
                <button class="toast-close" aria-label="Close">
                    <i class="fas fa-times"></i>
                </button>
            `;

            this.container.appendChild(toast);

            // Close button functionality
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', () => this.remove(toast));

            // Auto remove after duration
            if (duration > 0) {
                setTimeout(() => this.remove(toast), duration);
            }

            return toast;
        },

        getTitle(type) {
            const titles = {
                success: 'Success',
                error: 'Error',
                warning: 'Warning',
                info: 'Info'
            };
            return titles[type] || 'Notification';
        },

        remove(toast) {
            toast.classList.add('toast-exit');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        },

        success(message, duration) {
            return this.show(message, 'success', duration);
        },

        error(message, duration) {
            return this.show(message, 'error', duration);
        },

        warning(message, duration) {
            return this.show(message, 'warning', duration);
        },

        info(message, duration) {
            return this.show(message, 'info', duration);
        }
    };

    // Make Toast globally available
    window.Toast = Toast;

    // ============================================
    // Dark Mode Toggle
    // ============================================

    const DarkMode = {
        init() {
            // Check for saved theme preference or default to light mode
            const savedTheme = localStorage.getItem('theme') || 'light';
            this.setTheme(savedTheme);

            // Create toggle button if it doesn't exist
            this.createToggleButton();
        },

        createToggleButton() {
            const navbar = document.querySelector('.navbar-nav');
            if (!navbar) return;

            // Check if button already exists
            if (document.getElementById('darkModeToggle')) return;

            const li = document.createElement('li');
            li.className = 'nav-item';

            const button = document.createElement('button');
            button.id = 'darkModeToggle';
            button.className = 'nav-link btn btn-link';
            button.setAttribute('aria-label', 'Toggle dark mode');
            button.innerHTML = '<i class="fas fa-moon"></i>';
            button.style.border = 'none';
            button.style.background = 'none';

            button.addEventListener('click', () => this.toggle());

            li.appendChild(button);
            navbar.appendChild(li);
        },

        setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            this.updateToggleIcon(theme);
        },

        updateToggleIcon(theme) {
            const toggleBtn = document.getElementById('darkModeToggle');
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
                }
            }
        },

        toggle() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
        },

        getCurrentTheme() {
            return document.documentElement.getAttribute('data-theme');
        }
    };

    // Make DarkMode globally available
    window.DarkMode = DarkMode;

    // ============================================
    // Loading State Utilities
    // ============================================

    const Loading = {
        show(element, text = 'Loading...') {
            if (!element) return;

            element.disabled = true;
            element.setAttribute('data-original-text', element.textContent);
            element.classList.add('btn-loading');

            if (text) {
                element.textContent = text;
            }
        },

        hide(element) {
            if (!element) return;

            element.disabled = false;
            element.classList.remove('btn-loading');

            const originalText = element.getAttribute('data-original-text');
            if (originalText) {
                element.textContent = originalText;
                element.removeAttribute('data-original-text');
            }
        },

        showSpinner(container) {
            if (!container) return;

            const spinner = document.createElement('div');
            spinner.className = 'spinner-lg';
            spinner.style.margin = '2rem auto';
            spinner.style.display = 'block';

            container.innerHTML = '';
            container.appendChild(spinner);
        }
    };

    // Make Loading globally available
    window.Loading = Loading;

    // ============================================
    // Smooth Scrolling
    // ============================================

    function initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href === '#') return;

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ============================================
    // Form Validation Enhancement
    // ============================================

    function enhanceFormValidation() {
        const forms = document.querySelectorAll('form');

        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');

            inputs.forEach(input => {
                input.addEventListener('invalid', function (e) {
                    e.preventDefault();
                    this.classList.add('form-error');

                    setTimeout(() => {
                        this.classList.remove('form-error');
                    }, 400);
                });

                input.addEventListener('input', function () {
                    if (this.validity.valid) {
                        this.classList.remove('is-invalid');
                        this.classList.add('is-valid');
                    }
                });
            });
        });
    }

    // ============================================
    // Active Navigation Link
    // ============================================

    function setActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href) && href !== '/') {
                link.classList.add('active');
            }
        });
    }

    // ============================================
    // Auto-dismiss Alerts
    // ============================================

    function autoDismissAlerts() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

        alerts.forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    }

    // ============================================
    // Utility Functions
    // ============================================

    // Debounce function
    function debounce(func, wait) {
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

    // Throttle function
    function throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Format number with commas
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Animate counter
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = formatNumber(Math.floor(target));
                clearInterval(timer);
            } else {
                element.textContent = formatNumber(Math.floor(current));
            }
        }, 16);
    }

    // Copy to clipboard
    function copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                Toast.success('Copied to clipboard!');
            }).catch(() => {
                Toast.error('Failed to copy to clipboard');
            });
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                Toast.success('Copied to clipboard!');
            } catch (err) {
                Toast.error('Failed to copy to clipboard');
            }
            document.body.removeChild(textarea);
        }
    }

    // Make utilities globally available
    window.Utils = {
        debounce,
        throttle,
        formatNumber,
        animateCounter,
        copyToClipboard
    };

    // ============================================
    // Page Transition Effect
    // ============================================

    function addPageTransition() {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.classList.add('page-transition');
        }
    }

    // ============================================
    // Initialize on DOM Ready
    // ============================================

    document.addEventListener('DOMContentLoaded', function () {
        // Initialize dark mode
        DarkMode.init();

        // Initialize smooth scrolling
        initSmoothScrolling();

        // Enhance form validation
        enhanceFormValidation();

        // Set active navigation link
        setActiveNavLink();

        // Auto-dismiss alerts
        autoDismissAlerts();

        // Add page transition
        addPageTransition();

        // Convert Django messages to toasts
        const djangoMessages = document.querySelectorAll('.alert.alert-dismissible');
        djangoMessages.forEach(alert => {
            const message = alert.textContent.trim();
            let type = 'info';

            if (alert.classList.contains('alert-success')) type = 'success';
            else if (alert.classList.contains('alert-danger')) type = 'error';
            else if (alert.classList.contains('alert-warning')) type = 'warning';

            // Hide the original alert
            alert.style.display = 'none';

            // Show as toast
            Toast.show(message, type);
        });

        // Add stagger animation to cards
        const cardContainers = document.querySelectorAll('.row.g-4, .row.g-3');
        cardContainers.forEach(container => {
            if (container.children.length > 1 && container.children.length <= 6) {
                container.classList.add('stagger-children');
            }
        });

        // Initialize tooltips if Bootstrap is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        // Initialize popovers if Bootstrap is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
            const popoverTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="popover"]')
            );
            popoverTriggerList.map(function (popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
            });
        }

        console.log('🚀 SmartReg UI initialized successfully!');
    });

    // ============================================
    // Handle AJAX Errors Globally
    // ============================================

    window.addEventListener('unhandledrejection', function (event) {
        console.error('Unhandled promise rejection:', event.reason);
        Toast.error('An unexpected error occurred. Please try again.');
    });

})();
