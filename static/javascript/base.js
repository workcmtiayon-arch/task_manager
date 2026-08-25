document.addEventListener('DOMContentLoaded', function () {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    var toggleBtn = document.getElementById('sidebarToggle');

    if (!sidebar || !overlay || !toggleBtn) {
        return;
    }

    function openSidebar() {
        sidebar.classList.add('is-open');
        overlay.classList.add('is-visible');
        toggleBtn.setAttribute('aria-expanded', 'true');
    }

    function closeSidebar() {
        sidebar.classList.remove('is-open');
        overlay.classList.remove('is-visible');
        toggleBtn.setAttribute('aria-expanded', 'false');
    }

    toggleBtn.addEventListener('click', function () {
        var isOpen = sidebar.classList.contains('is-open');
        if (isOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay.addEventListener('click', closeSidebar);

    window.addEventListener('resize', function () {
        if (window.innerWidth > 960) {
            closeSidebar();
        }
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });

    // Logout confirmation modal
    var signoutLink = document.querySelector('.signout-link');
    var logoutOverlay = document.getElementById('logout-confirm-overlay');
    var confirmBtn = document.getElementById('confirmSignoutBtn');
    var logoutCancelBtns = logoutOverlay ? Array.from(logoutOverlay.querySelectorAll('.logout-cancel, .modal__close')) : [];

    if (signoutLink && logoutOverlay && confirmBtn) {
        signoutLink.addEventListener('click', function (e) {
            e.preventDefault();
            var href = signoutLink.getAttribute('href');
            logoutOverlay.hidden = false;
            // allow CSS transition
            requestAnimationFrame(function () { logoutOverlay.classList.add('is-visible'); });
            confirmBtn.dataset.href = href || '';
            // focus first actionable element
            (logoutCancelBtns[0] || confirmBtn).focus();
        });

        function closeLogoutModal() {
            logoutOverlay.classList.remove('is-visible');
            setTimeout(function () { logoutOverlay.hidden = true; confirmBtn.removeAttribute('data-href'); }, 180);
            signoutLink.focus();
        }

        logoutCancelBtns.forEach(function (btn) { btn.addEventListener('click', closeLogoutModal); });

        logoutOverlay.addEventListener('click', function (e) {
            if (e.target === logoutOverlay) closeLogoutModal();
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && logoutOverlay && !logoutOverlay.hidden) {
                closeLogoutModal();
            }
        });

        confirmBtn.addEventListener('click', function () {
            var href = confirmBtn.dataset.href;
            if (href) {
                // follow the link to perform logout
                window.location.href = href;
            }
        });
    }
});