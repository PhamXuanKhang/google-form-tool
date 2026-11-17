/**
 * Theme handling. The initial theme is applied by an inline script in
 * base.html before first paint; this file wires the toggle button and keeps
 * following the OS preference until the user picks a theme explicitly.
 */
const THEME_KEY = 'theme';

function readStoredTheme() {
    try {
        const stored = localStorage.getItem(THEME_KEY);
        if (stored === 'light' || stored === 'dark') return stored;
        const legacy = localStorage.getItem('darkMode');
        if (legacy === 'true') return 'dark';
        if (legacy === 'false') return 'light';
    } catch (error) {
        // Storage can be unavailable; fall back to the OS preference.
    }
    return null;
}

function systemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

/**
 * Apply a theme to the document and sync the toggle button.
 *
 * @param {'light'|'dark'} theme
 */
function applyTheme(theme) {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    root.setAttribute('data-bs-theme', theme);

    const isDark = theme === 'dark';
    const icon = document.getElementById('darkModeIcon');
    if (icon) {
        icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    }
    const button = document.getElementById('theme-toggle');
    if (button) {
        button.setAttribute('aria-pressed', String(isDark));
    }
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

/**
 * Turn on/off dark mode
 */
function toggleDarkMode() {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    try {
        localStorage.setItem(THEME_KEY, next);
    } catch (error) {
        // The choice still applies for this page view.
    }
    applyTheme(next);
}

/**
 * Show a message in the shared toast.
 *
 * @param {string} message
 * @param {'info'|'success'|'error'|'warning'} type
 */
function showToast(message, type = 'info') {
    const toastElement = document.getElementById('statusToast');
    const toastMessage = document.getElementById('toast-message');
    if (!toastElement || !toastMessage || !window.bootstrap) {
        console.warn(message);
        return;
    }
    toastMessage.textContent = message;
    toastElement.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-info', 'text-bg-warning');
    const classes = { success: 'text-bg-success', error: 'text-bg-danger', warning: 'text-bg-warning' };
    toastElement.classList.add(classes[type] || 'text-bg-info');
    bootstrap.Toast.getOrCreateInstance(toastElement).show();
}

window.toggleDarkMode = toggleDarkMode;
window.showToast = showToast;

window.addEventListener('DOMContentLoaded', () => {
    applyTheme(readStoredTheme() || systemTheme());

    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
            if (!readStoredTheme()) {
                applyTheme(event.matches ? 'dark' : 'light');
            }
        });
    }
});
