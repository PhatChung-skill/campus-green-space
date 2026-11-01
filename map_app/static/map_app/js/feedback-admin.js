(() => {
  window.setTimeout(() => {
    document.querySelectorAll(".content > .flash.is-gone").forEach((flash) => flash.remove());
  }, 5200);

  const textarea = document.querySelector("#feedback-reply-body");
  const picker = document.querySelector("#feedback-reaction-picker");
  const replyForm = document.querySelector(".feedback-staff-reply");
  if (picker) document.body.append(picker);

  document.querySelectorAll("[data-feedback-emoji]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!textarea) return;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.setRangeText(button.dataset.feedbackEmoji, start, end, "end");
      textarea.focus();
    });
  });

  function startAdminReply(info) {
    if (!replyForm) return;
    const preview = replyForm.querySelector(".feedback-reply-preview");
    if (replyForm.elements.reply_to) replyForm.elements.reply_to.value = info.id;
    if (preview) {
      const senderEl = preview.querySelector("[data-reply-sender]");
      const textEl = preview.querySelector("[data-reply-text]");
      if (senderEl) senderEl.textContent = info.sender;
      if (textEl) textEl.textContent = info.snippet;
      preview.hidden = false;
    }
    textarea?.focus();
    replyForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function cancelAdminReply() {
    if (!replyForm) return;
    const preview = replyForm.querySelector(".feedback-reply-preview");
    if (replyForm.elements.reply_to) replyForm.elements.reply_to.value = "";
    if (preview) preview.hidden = true;
  }

  function jumpToAdminMessage(messageId) {
    const target = document.querySelector(`[data-feedback-message="${messageId}"]`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.remove("is-highlighted");
    void target.offsetWidth;
    target.classList.add("is-highlighted");
    window.setTimeout(() => target.classList.remove("is-highlighted"), 1600);
  }

  document.addEventListener("click", (event) => {
    const replyTrigger = event.target.closest("[data-reply-trigger]");
    if (replyTrigger) {
      event.preventDefault();
      startAdminReply({
        id: replyTrigger.dataset.messageId,
        sender: replyTrigger.dataset.sender,
        snippet: replyTrigger.dataset.snippet,
      });
      return;
    }
    const cancelBtn = event.target.closest(".feedback-staff-reply .feedback-reply-cancel");
    if (cancelBtn) {
      event.preventDefault();
      cancelAdminReply();
      return;
    }
    const jumpBtn = event.target.closest("[data-jump-to]");
    if (jumpBtn) {
      event.preventDefault();
      jumpToAdminMessage(jumpBtn.dataset.jumpTo);
      return;
    }
    const toggle = event.target.closest("[data-reaction-picker-toggle]");
    if (toggle) {
      event.stopPropagation();
      openPickerFor(toggle.closest("[data-feedback-reactions]"), toggle);
      return;
    }
    if (!event.target.closest("#feedback-reaction-picker, [data-reaction-picker-toggle]")) closePicker();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closePicker();
      const preview = replyForm?.querySelector(".feedback-reply-preview");
      if (preview && !preview.hidden) {
        cancelAdminReply();
      }
    }
  });

  document.querySelector(".feedback-messages")?.addEventListener("scroll", closePicker, { passive: true });
  document.querySelector(".main")?.addEventListener("scroll", closePicker, { passive: true });
  window.addEventListener("resize", closePicker, { passive: true });

  picker?.querySelectorAll("[data-reaction-value]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = document.querySelector(`[data-feedback-reactions][data-message-id="${picker.dataset.messageId}"]`);
      if (form) toggleReaction(form, button.dataset.reactionValue);
    });
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-feedback-reactions]");
    if (!form) return;
    event.preventDefault();
    const emoji = event.submitter?.value;
    if (emoji) toggleReaction(form, emoji);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-feedback-action], [data-feedback-reply]");
    if (!form) return;
    event.preventDefault();
    if (form.matches("[data-feedback-reply]")) {
      sendReply(form);
    } else {
      submitAction(form, event.submitter);
    }
  });

  const toast = document.querySelector("[data-feedback-toast]");
  let toastTimer;
  function showToast(message, isError = false) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => { toast.hidden = true; }, 3000);
  }

  async function postForm(form, submitter) {
    const payload = new FormData(form);
    if (submitter?.name) payload.set(submitter.name, submitter.value);
    const csrf = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    return fetch(window.location.href, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: payload,
      credentials: "same-origin",
    });
  }

  async function sendReply(form) {
    const sendButton = form.querySelector(".feedback-send");
    sendButton.disabled = true;
    try {
      const response = await postForm(form);
      const data = await response.json();
      if (!response.ok) { showToast(data.detail || "Chưa gửi được phản hồi.", true); return; }
      document.querySelector("[data-feedback-empty]")?.remove();
      document.querySelector(".feedback-staff-messages")?.insertAdjacentHTML("beforeend", data.html);
      form.elements.body.value = "";
      if (form.elements.image) form.elements.image.value = "";
      cancelAdminReply();
      const fileLabel = form.querySelector(".feedback-file-name");
      if (fileLabel) fileLabel.textContent = "Ảnh tối đa 5 MB";
      const pane = document.querySelector(".feedback-staff-messages");
      if (pane) pane.scrollTop = pane.scrollHeight;
      showToast("Đã gửi phản hồi cho khách.");
    } catch (_error) {
      showToast("Không kết nối được để gửi phản hồi.", true);
    } finally {
      sendButton.disabled = false;
    }
  }

  async function submitAction(form, submitter) {
    const action = submitter?.value || form.elements.action?.value;
    const submitButton = submitter || form.querySelector("button[type='submit']");
    if (submitButton) submitButton.disabled = true;
    try {
      const response = await postForm(form, submitter);
      const data = await response.json();
      if (!response.ok) { showToast(data.detail || "Không thực hiện được thao tác.", true); return; }
      if (action === "delete") {
        window.location.assign(data.redirect_url);
      } else if (action === "delete_message") {
        form.closest("[data-feedback-message]")?.remove();
        if (data.empty) {
          const empty = document.createElement("p");
          empty.className = "feedback-welcome";
          empty.dataset.feedbackEmpty = "";
          empty.textContent = "Hội thoại chưa có nội dung.";
          document.querySelector(".feedback-staff-messages")?.append(empty);
        }
        showToast("Đã xóa tin nhắn.");
      } else if (action === "mark_read") {
        if (submitButton) submitButton.textContent = "Đã đánh dấu đã đọc";
        showToast("Đã đánh dấu hội thoại là đã đọc.");
      }
    } catch (_error) {
      showToast("Không kết nối được để thực hiện thao tác.", true);
    } finally {
      if (submitButton?.isConnected) submitButton.disabled = false;
    }
  }

  async function toggleReaction(form, emoji) {
    if (form.classList.contains("is-saving")) return;
    const payload = new FormData(form);
    payload.set("emoji", emoji);
    const csrf = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
    closePicker();
    form.classList.add("is-saving");
    try {
      const response = await fetch(window.location.href, {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        body: payload,
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok) return;
      renderSummary(form, data.reaction_summary, data.reaction_total);
    } catch (_error) {
      // Keep the current summary intact if the reaction request cannot reach the server.
    } finally {
      form.classList.remove("is-saving");
    }
  }

  function renderSummary(form, reactions, total) {
    const summary = form.querySelector(".feedback-reaction-summary");
    summary.replaceChildren();
    reactions.filter((reaction) => reaction.count > 0).forEach((reaction) => {
      const button = document.createElement("button");
      button.type = "submit";
      button.name = "emoji";
      button.value = reaction.emoji;
      button.className = `feedback-reaction${reaction.reacted ? " is-reacted" : ""}`;
      button.setAttribute("aria-pressed", String(reaction.reacted));
      button.setAttribute("aria-label", `${reaction.label} · ${reaction.count}`);
      button.title = `Bấm để thả hoặc gỡ ${reaction.label}`;
      button.textContent = reaction.emoji;
      summary.append(button);
    });
    if (total) {
      const count = document.createElement("span");
      count.className = "feedback-reaction-total";
      count.textContent = total;
      summary.append(count);
    }
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "feedback-reaction-add";
    toggle.dataset.reactionPickerToggle = "";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Mở danh sách emoji cảm xúc");
    toggle.title = "Thả cảm xúc";
    toggle.textContent = "☺ +";
    summary.append(toggle);
  }

  function openPickerFor(form, toggle) {
    const isThisOpen = picker && !picker.hidden && picker.dataset.messageId === form.dataset.messageId;
    closePicker();
    if (!picker || isThisOpen) return;
    picker.dataset.messageId = form.dataset.messageId;
    picker.hidden = false;
    picker.style.visibility = "hidden";
    const rect = toggle.getBoundingClientRect();
    const width = picker.offsetWidth;
    const height = picker.offsetHeight;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const article = form.closest(".feedback-message")?.getBoundingClientRect();
    const messagePane = document.querySelector(".feedback-messages")?.getBoundingClientRect();
    let top = article ? article.bottom + 8 : rect.bottom + 8;
    if (messagePane && top + height > messagePane.bottom - 8 && article) top = article.top - height - 8;
    if (messagePane && top < messagePane.top + 8) top = rect.bottom + 8;
    top = Math.max(8, Math.min(top, window.innerHeight - height - 8));
    picker.style.left = `${left}px`;
    picker.style.top = `${top}px`;
    picker.style.visibility = "visible";
    toggle.setAttribute("aria-expanded", "true");
    const active = new Set(Array.from(form.querySelectorAll(".feedback-reaction-summary button[name='emoji']"), (button) => button.value));
    picker.querySelectorAll("[data-reaction-value]").forEach((button) => {
      const selected = active.has(button.dataset.reactionValue);
      button.classList.toggle("is-reacted", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
  }

  function closePicker() {
    if (!picker) return;
    picker.hidden = true;
    picker.style.visibility = "";
    delete picker.dataset.messageId;
    document.querySelectorAll("[data-reaction-picker-toggle]").forEach((toggle) => toggle.setAttribute("aria-expanded", "false"));
  }
})();
