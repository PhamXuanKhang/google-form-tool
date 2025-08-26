/**
 * Change text and background color correspond to dark/light mode
 * 
 * @param {boolean} isDark 
 */
function applyDarkMode(isDark) {
    const body = document.body;
    body.classList.toggle('bg-dark', isDark);
    body.classList.toggle('text-white', isDark);
    body.classList.toggle('bg-light', !isDark);
    body.classList.toggle('text-dark', !isDark);

    document.querySelectorAll('.navbar').forEach(nav => {
      nav.classList.toggle('bg-dark', isDark);
      nav.classList.toggle('navbar-dark', isDark);
      nav.classList.toggle('bg-light', !isDark);
      nav.classList.toggle('navbar-light', !isDark);
    });

    document.querySelectorAll('footer').forEach(footer => {
        footer.classList.toggle('bg-dark', isDark);
        footer.classList.toggle('text-light', isDark);
        footer.classList.toggle('bg-light', !isDark);
        footer.classList.toggle('text-dark', !isDark);
    });

    const icon = document.getElementById("darkModeIcon");
    if (icon) {
      icon.className = isDark ? "fas fa-sun" : "fas fa-moon";
    }
}

/**
 * Turn on/off dark mode
 */
function toggleDarkMode() {
    let isDark = document.body.classList.contains('bg-dark');
    isDark = !isDark;
    localStorage.setItem('darkMode', isDark);
    applyDarkMode(isDark);
}



function changeLanguage(lang) {
    localStorage.setItem('language', lang);
    document.cookie = "language=" + lang + ";path=/;max-age=" + (30*24*60*60);
    location.reload();
}

/**
 * Get dark mode status from local storage
 */
window.addEventListener('DOMContentLoaded', () => {
    let darkMode = localStorage.getItem('darkMode');
    if (darkMode === null) {
    darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    } else {
    darkMode = (darkMode === 'true');
    }
    applyDarkMode(darkMode);

    const savedLang = localStorage.getItem('language');
    const cookieLang = document.cookie.split('; ').find(row => row.startsWith('language='));
    const currentLang = cookieLang ? cookieLang.split('=')[1] : null;

    // Nếu localStorage có lang nhưng cookie chưa có → set lại
    if (savedLang && savedLang !== currentLang) {
        document.cookie = "language=" + savedLang + ";path=/;max-age=" + (30*24*60*60);
        location.reload();
    }
});