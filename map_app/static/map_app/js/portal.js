(function () {
    const toggle = document.querySelector(".nav-toggle");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".nav-overlay");

    function setOpen(open) {
        if (!sidebar) return;
        sidebar.classList.toggle("is-open", open);
        document.body.classList.toggle("nav-open", open);
        if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
        if (overlay) overlay.hidden = !open;
    }

    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            setOpen(!sidebar.classList.contains("is-open"));
        });
    }
    if (overlay) {
        overlay.addEventListener("click", function () { setOpen(false); });
    }
    document.querySelectorAll(".sidebar .nav a").forEach(function (link) {
        link.addEventListener("click", function () {
            if (window.matchMedia("(max-width: 900px)").matches) setOpen(false);
        });
    });

    document.querySelectorAll(".flash").forEach(function (el) {
        window.setTimeout(function () {
            el.classList.add("is-gone");
        }, 5000);
    });
})();
