(() => {
  const script = document.currentScript;
  const countUrl = script?.dataset.countUrl || document.querySelector("[data-feedback-stat]")?.dataset.countUrl;
  if (!countUrl) return;
  const badge = document.querySelector("[data-feedback-nav-badge]");
  const alertBanner = document.querySelector("[data-feedback-alert]");
  const alertCount = document.querySelector("[data-feedback-alert-count]");
  const stat = document.querySelector("[data-feedback-stat]");
  async function updateCount() {
    try {
      const response = await fetch(countUrl, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!response.ok) return;
      const { count } = await response.json();
      if (badge) { badge.textContent = count; badge.hidden = count < 1; }
      if (alertBanner) {
        alertBanner.hidden = count < 1;
        if (alertCount) alertCount.textContent = count;
      }
      if (stat) {
        const hint = stat.querySelector("em");
        if (hint) hint.textContent = `${count} hội thoại chưa đọc`;
      }
    } catch (_error) {
      // The page can continue working if the notification count is temporarily unavailable.
    }
  }
  updateCount();
  window.setInterval(updateCount, 10000);
})();
