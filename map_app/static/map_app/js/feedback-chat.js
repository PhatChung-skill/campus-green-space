(() => {
  const root = document.querySelector(".feedback-chat");
  if (!root) return;
  const launcher = root.querySelector(".feedback-launcher");
  const panel = root.querySelector(".feedback-panel");
  const closeButton = root.querySelector(".feedback-close");
  const form = root.querySelector(".feedback-compose");
  const messageList = root.querySelector(".feedback-messages");
  const status = root.querySelector(".feedback-status");
  const category = root.querySelector("#feedback-category");
  const fileInput = root.querySelector('input[name="image"]');
  const fileName = root.querySelector(".feedback-file-name");
  const unreadDot = root.querySelector(".feedback-unread-dot");
  const replyPreview = form?.querySelector(".feedback-reply-preview");
  const replyCancelBtn = replyPreview?.querySelector(".feedback-reply-cancel");
  const apiUrl = root.dataset.apiUrl;
  let isOpen = false;
  let hasConversation = false;

  const csrfToken = () => form?.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
  const post = (data) => fetch(apiUrl, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
    body: data,
    credentials: "same-origin",
  });

  function startReply(info) {
    if (!form || !replyPreview) return;
    if (form.elements.reply_to) form.elements.reply_to.value = info.id;
    const senderEl = replyPreview.querySelector("[data-reply-sender]");
    const textEl = replyPreview.querySelector("[data-reply-text]");
    if (senderEl) senderEl.textContent = info.sender;
    if (textEl) textEl.textContent = info.snippet;
    replyPreview.hidden = false;
    form.elements.body?.focus();
  }

  function cancelReply() {
    if (!form) return;
    if (form.elements.reply_to) form.elements.reply_to.value = "";
    if (replyPreview) replyPreview.hidden = true;
  }

  replyCancelBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    cancelReply();
  });

  function jumpToMessage(messageId) {
    const target = messageList.querySelector(`[data-message-id="${messageId}"]`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.remove("is-highlighted");
    void target.offsetWidth;
    target.classList.add("is-highlighted");
    window.setTimeout(() => target.classList.remove("is-highlighted"), 1600);
  }

  function buildMessage(message) {
    const item = document.createElement("article");
    item.className = `feedback-message${message.is_staff ? "" : " is-mine"}`;
    item.dataset.messageId = message.id;

    if (message.reply_to) {
      const quote = document.createElement("div");
      quote.className = "feedback-quote-box";
      quote.dataset.jumpTo = message.reply_to.id;
      quote.title = "Bấm để xem tin nhắn gốc";

      const quoteInner = document.createElement("div");
      quoteInner.className = "feedback-quote-inner";

      const quoteSender = document.createElement("div");
      quoteSender.className = "feedback-quote-sender";
      const iconSpan = document.createElement("span");
      iconSpan.className = "feedback-quote-icon";
      iconSpan.textContent = "↩ ";
      quoteSender.append(iconSpan, document.createTextNode(message.reply_to.sender));

      const quoteBody = document.createElement("div");
      quoteBody.className = "feedback-quote-body";
      quoteBody.textContent = message.reply_to.body || (message.reply_to.has_image ? "[Hình ảnh]" : "[Tin nhắn]");

      quoteInner.append(quoteSender, quoteBody);
      quote.append(quoteInner);
      quote.addEventListener("click", () => jumpToMessage(message.reply_to.id));
      item.append(quote);
    }

    if (message.body) {
      const body = document.createElement("p");
      body.className = "feedback-message-body";
      body.textContent = message.body;
      item.append(body);
    }
    if (message.image) {
      const image = document.createElement("img");
      image.src = message.image;
      image.alt = "Ảnh đính kèm trong hội thoại";
      image.loading = "lazy";
      item.append(image);
    }
    const meta = document.createElement("small");
    meta.className = "feedback-message-meta";
    meta.textContent = `${message.is_staff ? (message.sender || "Nhân viên hỗ trợ") : "Bạn"} · ${message.created_at}`;
    item.append(meta);

    const actionsBar = document.createElement("div");
    actionsBar.className = "feedback-message-actions-bar";

    const reactions = document.createElement("div");
    reactions.className = "feedback-message-reactions";
    const summary = document.createElement("div");
    summary.className = "feedback-reaction-summary";
    const activeReactions = message.reactions.filter((reaction) => reaction.count > 0);
    activeReactions.forEach((reaction) => {
      summary.append(makeReactionButton(message.id, reaction));
    });
    const totalReactions = activeReactions.reduce((total, reaction) => total + reaction.count, 0);
    if (totalReactions) {
      const total = document.createElement("span");
      total.className = "feedback-reaction-total";
      total.textContent = totalReactions;
      summary.append(total);
    }

    const picker = document.createElement("div");
    picker.className = "feedback-reaction-picker";
    picker.hidden = true;
    picker.setAttribute("role", "group");
    picker.setAttribute("aria-label", "Chọn emoji cảm xúc");
    message.reactions.forEach((reaction) => picker.append(makeReactionButton(message.id, reaction)));

    const pickerToggle = document.createElement("button");
    pickerToggle.type = "button";
    pickerToggle.className = "feedback-reaction-add";
    pickerToggle.textContent = "☺ +";
    pickerToggle.title = "Thả cảm xúc";
    pickerToggle.setAttribute("aria-label", "Mở danh sách emoji cảm xúc");
    pickerToggle.setAttribute("aria-expanded", "false");
    pickerToggle.addEventListener("click", () => {
      const opening = picker.hidden;
      closeReactionPickers();
      picker.hidden = !opening;
      pickerToggle.setAttribute("aria-expanded", String(opening));
    });

    summary.append(pickerToggle);
    reactions.append(summary, picker);

    const subactions = document.createElement("div");
    subactions.className = "feedback-message-subactions";

    const replyBtn = document.createElement("button");
    replyBtn.type = "button";
    replyBtn.className = "feedback-reply-btn";
    replyBtn.title = "Trả lời tin nhắn này";
    replyBtn.setAttribute("aria-label", "Trả lời tin nhắn này");
    const quoteMark = document.createElement("span");
    quoteMark.className = "feedback-quote-mark";
    quoteMark.textContent = "”";
    replyBtn.append(quoteMark, document.createTextNode(" Trả lời"));
    replyBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      startReply({
        id: message.id,
        sender: message.is_staff ? (message.sender || "Nhân viên hỗ trợ") : "Bạn",
        snippet: message.body || (message.image ? "[Hình ảnh]" : "[Tin nhắn]"),
      });
    });
    subactions.append(replyBtn);

    actionsBar.append(reactions, subactions);
    item.append(actionsBar);
    return item;
  }

  function makeReactionButton(messageId, reaction) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `feedback-reaction${reaction.reacted ? " is-reacted" : ""}`;
    button.setAttribute("aria-pressed", String(reaction.reacted));
    button.setAttribute("aria-label", `${reaction.emoji} · ${reaction.count}`);
    button.title = reaction.reacted ? "Gỡ cảm xúc" : "Thả cảm xúc";
    button.append(document.createTextNode(reaction.emoji));
    button.addEventListener("click", () => toggleReaction(messageId, reaction.emoji, button));
    return button;
  }

  function closeReactionPickers() {
    root.querySelectorAll(".feedback-reaction-picker").forEach((picker) => { picker.hidden = true; });
    root.querySelectorAll(".feedback-reaction-add").forEach((button) => button.setAttribute("aria-expanded", "false"));
  }

  function addMessage(message) {
    messageList.append(buildMessage(message));
  }

  async function toggleReaction(messageId, emoji, button) {
    const payload = new FormData();
    payload.set("action", "react");
    payload.set("message_id", messageId);
    payload.set("emoji", emoji);
    button.disabled = true;
    try {
      const response = await post(payload);
      const data = await response.json();
      if (!response.ok) { status.textContent = data.detail || "Chưa cập nhật được cảm xúc."; return; }
      closeReactionPickers();
      const current = messageList.querySelector(`[data-message-id="${messageId}"]`);
      if (current) current.replaceWith(buildMessage(data.message));
      status.textContent = "";
    } catch (_error) {
      status.textContent = "Không kết nối được để cập nhật cảm xúc.";
    } finally {
      button.disabled = false;
    }
  }

  async function refreshMessages() {
    if (!form) return;
    try {
      const response = await fetch(apiUrl, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!response.ok) return;
      const data = await response.json();
      if (isOpen && data.has_unread) await markRead();
      const welcome = messageList.querySelector(".feedback-welcome");
      messageList.replaceChildren();
      if (welcome && !data.messages.length) messageList.append(welcome);
      data.messages.forEach(addMessage);
      hasConversation = data.messages.length > 0;
      if (category) {
        category.value = data.category || "feedback";
        category.disabled = hasConversation;
        category.closest(".feedback-category-wrap").hidden = hasConversation;
      }
      unreadDot.hidden = !data.has_unread || isOpen;
      messageList.scrollTop = messageList.scrollHeight;
    } catch (_error) {
      // Keep the current conversation visible when the network is temporarily unavailable.
    }
  }

  async function markRead() {
    if (!form) return;
    const payload = new FormData();
    payload.set("action", "mark_read");
    try { await post(payload); } catch (_error) { /* A later refresh will retry when the panel opens. */ }
  }

  async function setOpen(value) {
    isOpen = value;
    panel.hidden = !value;
    launcher.setAttribute("aria-expanded", String(value));
    if (value) {
      if (form) await markRead();
      await refreshMessages();
      root.querySelector("textarea")?.focus();
    }
  }

  launcher.addEventListener("click", () => setOpen(panel.hidden));
  closeButton?.addEventListener("click", () => setOpen(false));
  document.addEventListener("click", (event) => {
    if (isOpen && !event.target.closest(".feedback-message-reactions")) closeReactionPickers();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isOpen) {
      if (replyPreview && !replyPreview.hidden) {
        cancelReply();
        return;
      }
      closeReactionPickers();
      setOpen(false);
    }
  });

  root.querySelectorAll("[data-emoji]").forEach((button) => button.addEventListener("click", () => {
    const input = form.elements.body;
    const start = input.selectionStart;
    const end = input.selectionEnd;
    input.setRangeText(button.dataset.emoji, start, end, "end");
    input.focus();
  }));

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file && file.size > 5 * 1024 * 1024) {
      fileInput.value = "";
      fileName.textContent = "Hình ảnh tối đa 5 MB";
      status.textContent = "Hình ảnh tối đa 5 MB.";
      return;
    }
    status.textContent = "";
    fileName.textContent = file ? file.name : "Ảnh tối đa 5 MB";
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "";
    const submit = form.querySelector(".feedback-send");
    const body = form.elements.body.value.trim();
    const file = fileInput.files[0];
    if (!body && !file) { status.textContent = "Hãy nhập tin nhắn hoặc chọn ảnh."; return; }
    if (body.length > 3000) { status.textContent = "Nội dung tối đa 3.000 ký tự."; return; }
    const payload = new FormData(form);
    if (!hasConversation) payload.set("category", category.value);
    submit.disabled = true;
    try {
      const response = await post(payload);
      const data = await response.json();
      if (!response.ok) { status.textContent = data.detail || "Chưa gửi được tin nhắn. Vui lòng thử lại."; return; }
      form.elements.body.value = "";
      fileInput.value = "";
      fileName.textContent = "Ảnh tối đa 5 MB";
      cancelReply();
      hasConversation = true;
      await refreshMessages();
    } catch (_error) {
      status.textContent = "Không kết nối được. Vui lòng thử gửi lại.";
    } finally {
      submit.disabled = false;
    }
  });

  refreshMessages();
  window.setInterval(refreshMessages, 20000);
})();
