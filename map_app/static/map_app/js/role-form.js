(function () {
    document.querySelectorAll("[data-perm-group]").forEach(function (box) {
        const button = box.querySelector("[data-toggle-group]");
        if (!button) return;
        button.addEventListener("click", function () {
            const checks = box.querySelectorAll('input[type="checkbox"]');
            const allOn = Array.prototype.every.call(checks, function (el) { return el.checked; });
            checks.forEach(function (el) { el.checked = !allOn; });
            button.textContent = allOn ? "Chọn hết" : "Bỏ chọn";
        });
    });
})();
