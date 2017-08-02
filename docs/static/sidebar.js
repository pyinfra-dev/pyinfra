(function() {
    var sidebar;
    var sidebarTop;
    var wasSticky = false;

    function onScroll(ev) {
        if (!wasSticky && window.scrollY > sidebarTop) {
            sidebar.style.position = 'fixed';
            sidebar.style.top = '0';
            wasSticky = true;
        } else if (wasSticky && window.scrollY < sidebarTop) {
            sidebar.style.position = 'relative';
            sidebar.style.top = 'auto';
            wasSticky = false;
        }
    }

    window.addEventListener('load', function() {
        sidebar = document.querySelector('.sphinxsidebarwrapper');
        sidebarTop = sidebar.offsetTop - 14;

        if (sidebar.clientHeight < window.innerHeight) {
            window.addEventListener('scroll', onScroll);
        }
    });
})();
