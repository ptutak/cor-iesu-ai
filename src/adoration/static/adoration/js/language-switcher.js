/**
 * Language Switcher JavaScript Module
 * Handles interactive language switching functionality with keyboard navigation
 */
(function () {
    'use strict';

    let isDropdownOpen = false;
    let switcher, button, dropdown, options;

    /**
     * Initialize the language switcher
     */
    function init() {
        switcher = document.getElementById('languageSwitcher');
        if (!switcher) return;

        button = switcher.querySelector('.language-switcher-btn');
        dropdown = switcher.querySelector('.language-dropdown');
        options = switcher.querySelectorAll('.language-option');

        if (!button || !dropdown || !options.length) return;

        setupEventListeners();
    }

    /**
     * Set up all event listeners
     */
    function setupEventListeners() {
        // Button click
        button.addEventListener('click', toggleDropdown);

        // Keyboard events
        document.addEventListener('keydown', handleKeyboardNavigation);

        // Close dropdown when page visibility changes
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                closeDropdown();
            }
        });

        // Handle form submissions
        options.forEach(option => {
            option.addEventListener('click', function(e) {
                // Let the form submit naturally
                closeDropdown();
            });
        });
    }

    /**
     * Toggle dropdown open/close
     */
    function toggleDropdown() {
        if (isDropdownOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    /**
     * Open the dropdown
     */
    function openDropdown() {
        if (isDropdownOpen) return;

        switcher.classList.add('show');
        button.setAttribute('aria-expanded', 'true');
        isDropdownOpen = true;

        // Focus first option for keyboard users
        const firstOption = dropdown.querySelector('.language-option');
        if (firstOption && document.activeElement === button) {
            setTimeout(() => firstOption.focus(), 100);
        }

        // Close when clicking outside or focusing outside
        setTimeout(() => {
            document.addEventListener('click', handleOutsideClick);
            document.addEventListener('focusin', handleFocusOut);
        }, 0);
    }

    /**
     * Close the dropdown
     */
    function closeDropdown() {
        if (!isDropdownOpen) return;

        switcher.classList.remove('show');
        button.setAttribute('aria-expanded', 'false');
        isDropdownOpen = false;

        // Remove event listeners
        document.removeEventListener('click', handleOutsideClick);
        document.removeEventListener('focusin', handleFocusOut);
    }

    /**
     * Handle clicks outside the switcher
     */
    function handleOutsideClick(event) {
        if (!switcher.contains(event.target)) {
            closeDropdown();
        }
    }

    /**
     * Handle focus moving outside the switcher
     */
    function handleFocusOut(event) {
        if (!switcher.contains(event.target)) {
            closeDropdown();
        }
    }

    /**
     * Handle keyboard navigation
     */
    function handleKeyboardNavigation(event) {
        // Handle button focus
        if (!isDropdownOpen) {
            if (document.activeElement === button &&
                (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown')) {
                event.preventDefault();
                openDropdown();
            }
            return;
        }

        // Handle dropdown navigation
        const currentFocus = document.activeElement;
        let currentIndex = Array.from(options).indexOf(currentFocus);

        switch (event.key) {
            case 'Escape':
                event.preventDefault();
                closeDropdown();
                button.focus();
                break;

            case 'ArrowDown':
                event.preventDefault();
                if (currentIndex < 0) {
                    options[0]?.focus();
                } else {
                    currentIndex = (currentIndex + 1) % options.length;
                    options[currentIndex]?.focus();
                }
                break;

            case 'ArrowUp':
                event.preventDefault();
                if (currentIndex < 0) {
                    options[options.length - 1]?.focus();
                } else {
                    currentIndex = currentIndex <= 0 ? options.length - 1 : currentIndex - 1;
                    options[currentIndex]?.focus();
                }
                break;

            case 'Home':
                event.preventDefault();
                options[0]?.focus();
                break;

            case 'End':
                event.preventDefault();
                options[options.length - 1]?.focus();
                break;

            case 'Enter':
            case ' ':
                if (currentFocus && currentFocus.classList.contains('language-option')) {
                    event.preventDefault();
                    currentFocus.click();
                }
                break;

            case 'Tab':
                // Allow normal tab behavior but close dropdown
                closeDropdown();
                break;
        }
    }

    /**
     * Public API
     */
    window.LanguageSwitcher = {
        init: init,
        toggle: toggleDropdown,
        open: openDropdown,
        close: closeDropdown
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Make toggle function available globally for backwards compatibility
    window.toggleLanguageDropdown = toggleDropdown;

})();
