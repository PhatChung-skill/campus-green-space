(function () {
  "use strict";

  const form = document.querySelector("[data-password-change-form]");
  if (!form || !window.fetch) return;

  const feedback = form.querySelector("[data-password-feedback]");
  const submitButton = form.querySelector('button[type="submit"]');
  const defaultButtonText = submitButton.textContent;

  function showFeedback(message, isError) {
    feedback.textContent = message;
    feedback.hidden = false;
    feedback.className = isError
      ? "alert alert-danger py-2 mb-3"
      : "alert alert-success py-2 mb-3";
    feedback.setAttribute("role", isError ? "alert" : "status");
  }

  function clearErrors() {
    form.querySelectorAll("[data-password-error-for]").forEach(function (container) {
      container.replaceChildren();
      container.hidden = true;
      const field = form.elements.namedItem(container.dataset.passwordErrorFor);
      if (field) field.removeAttribute("aria-invalid");
    });
    feedback.textContent = "";
    feedback.hidden = true;
    feedback.className = "mb-3";
    feedback.removeAttribute("role");
  }

  function showFieldErrors(errors) {
    let hasFieldError = false;
    Object.entries(errors || {}).forEach(function ([name, messages]) {
      if (name === "__all__" && Array.isArray(messages)) {
        hasFieldError = true;
        showFeedback(messages.join(" "), true);
        return;
      }
      const container = Array.from(form.querySelectorAll("[data-password-error-for]"))
        .find(function (item) { return item.dataset.passwordErrorFor === name; });
      const field = form.elements.namedItem(name);
      if (!container || !Array.isArray(messages)) return;
      hasFieldError = true;
      container.replaceChildren();
      messages.forEach(function (message) {
        const line = document.createElement("div");
        line.textContent = message;
        container.appendChild(line);
      });
      container.hidden = false;
      if (field) field.setAttribute("aria-invalid", "true");
    });
    if (!hasFieldError) {
      showFeedback("Không thể đổi mật khẩu. Vui lòng kiểm tra lại thông tin.", true);
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearErrors();
    submitButton.disabled = true;
    submitButton.textContent = "Đang cập nhật…";

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        }
      });
      let result;
      try {
        result = await response.json();
      } catch (parseError) {
        showFeedback(
          response.ok
            ? "Máy chủ trả về phản hồi không hợp lệ. Vui lòng thử lại."
            : "Máy chủ gặp lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.",
          true
        );
        return;
      }

      if (response.ok && result.ok) {
        form.reset();
        clearErrors();
        showFeedback(result.message || "Đổi mật khẩu thành công.", false);
      } else if (result.errors) {
        showFieldErrors(result.errors);
      } else {
        showFeedback(result.message || "Không thể đổi mật khẩu. Vui lòng thử lại.", true);
      }
    } catch (error) {
      showFeedback("Không thể kết nối để đổi mật khẩu. Vui lòng thử lại.", true);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = defaultButtonText;
    }
  });
})();
