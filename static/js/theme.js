/* Dark mode theme management */

class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('theme-toggle');
        this.currentTheme = localStorage.getItem('theme') || 'dark';
        this.init();
    }

    init() {
        // Apply saved theme on load
        this.applyTheme(this.currentTheme);
        
        // Add click listener to toggle button
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Listen for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
            
            // Apply system preference if no saved preference (default to dark)
            if (!localStorage.getItem('theme')) {
                this.currentTheme = 'dark';
                this.applyTheme(this.currentTheme);
            }
        }
    }

    applyTheme(theme) {
        // Add animation class
        if (this.themeToggle) {
            this.themeToggle.classList.add('animating');
        }
        
        // Apply theme
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            if (this.themeToggle) {
                this.themeToggle.setAttribute('data-tooltip', 'Switch to dark mode');
            }
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (this.themeToggle) {
                this.themeToggle.setAttribute('data-tooltip', 'Switch to light mode');
            }
        }
        
        // Remove animation class after transition
        setTimeout(() => {
            if (this.themeToggle) {
                this.themeToggle.classList.remove('animating');
            }
        }, 300);
        
        this.currentTheme = theme;
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});