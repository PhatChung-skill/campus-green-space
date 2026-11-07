(function () {
  "use strict";

  const eye = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
  const eyeOff = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m3 3 18 18"></path><path d="M10.6 5.1A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a16.8 16.8 0 0 1-4 4.7"></path><path d="M6.2 6.2C3.5 8 2 12 2 12s3.6 7 10 7c1.2 0 2.3-.2 3.3-.6"></path><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"></path></svg>';

  function addToggle(input) {
    if (input.dataset.passwordToggleReady === "true") return;
    input.dataset.passwordToggleReady = "true";

    const wrapper = document.createElement("span");
    wrapper.className = "password-toggle-wrap";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement("button");
    button.className = "password-toggle-button";
    button.type = "button";
    button.setAttribute("aria-label", "Hiện mật khẩu");
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = eye;
    button.addEventListener("click", function () {
      const isVisible = input.type === "text";
      input.type = isVisible ? "password" : "text";
      button.setAttribute("aria-label", isVisible ? "Hiện mật khẩu" : "Ẩn mật khẩu");
      button.setAttribute("aria-pressed", String(!isVisible));
      button.innerHTML = isVisible ? eye : eyeOff;
      input.focus();
    });
    wrapper.appendChild(button);
  }

  function initialize() {
    document.querySelectorAll('input[type="password"]').forEach(addToggle);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
