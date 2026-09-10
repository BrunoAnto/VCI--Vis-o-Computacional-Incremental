// Navbar: mobile menu toggle
document.getElementById('mobile-menu-btn')?.addEventListener('click', function () {
    document.getElementById('mobile-menu').classList.toggle('hidden');
});

// Navbar: dropdown toggle
document.querySelectorAll('[data-dropdown]').forEach(function (el) {
    var btn = el.querySelector('button');
    var panel = el.querySelector('.dropdown-panel');
    btn.addEventListener('click', function (e) {
        e.stopPropagation();
        document.querySelectorAll('.dropdown-panel').forEach(function (p) {
            if (p !== panel) p.classList.add('hidden');
        });
        panel.classList.toggle('hidden');
    });
});

// Fechar dropdowns ao clicar fora
document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown-panel').forEach(function (p) {
        p.classList.add('hidden');
    });
});

// CSRF token helper para fetch
function getCSRFToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken') || row.includes('csrftoken_'))
        ?.split('=')[1] || '';
}
