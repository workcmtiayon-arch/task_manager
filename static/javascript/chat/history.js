"use strict";

import { config, elements, state } from "./context.js";
import { showToast, scrollToBottom, updateEmptyState } from "./helpers.js";
import { renderMessageRow, upsertMessage, applyReceiptUpdate, applyReactionUpdate } from "./render.js";

// Construit l'observateur des messages entrants visibles et fournit les opérations d'historique.
export function createHistory(sendEvent) {
  const readMarked = new Set();
  const readObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const messageId = entry.target.dataset.messageId;
      if (readMarked.has(messageId)) return;
      readMarked.add(messageId);
      readObserver.unobserve(entry.target);
      sendEvent({ type: "message.read", message_id: Number(messageId) });
    });
  }, { root: elements.messages, threshold: 0.6 });

  // Observe un message entrant uniquement lorsqu'il doit être marqué comme lu.
  function observeForReadReceipt(row, message) { if (message.sender.id !== config.currentUserId && !message.is_deleted && row) readObserver.observe(row); }

  // Insère l'historique initial ou une page antérieure sans perdre le défilement.
  function loadHistory(beforeId) {
    if (state.isLoadingHistory || (!state.hasMoreHistory && beforeId)) return;
    state.isLoadingHistory = true;
    let url = `${config.messagesUrl}?limit=50`;
    if (beforeId) url += `&before=${encodeURIComponent(beforeId)}`;
      fetch(url).then((response) => { if (!response.ok) throw new Error(window.taskManagerI18n.cannotLoadMessages); return response.json(); }).then((data) => {
      const messages = data.messages;
      if (!messages.length) { state.hasMoreHistory = false; updateEmptyState(); return; }
      if (messages.length < 50) state.hasMoreHistory = false;
      if (beforeId) {
        const previousHeight = elements.messages.scrollHeight;
        const fragment = document.createDocumentFragment();
        const rows = messages.map((message) => { const row = renderMessageRow(message); fragment.appendChild(row); return { row, message }; });
        elements.messages.insertBefore(fragment, elements.messages.firstChild);
        elements.messages.scrollTop = elements.messages.scrollHeight - previousHeight;
        rows.forEach(({ row, message }) => observeForReadReceipt(row, message));
      } else {
        messages.forEach((message) => { const row = renderMessageRow(message); elements.messages.appendChild(row); observeForReadReceipt(row, message); });
        scrollToBottom();
      }
      state.oldestMessageId = messages[0].id;
      updateEmptyState();
    }).catch(() => showToast(window.taskManagerI18n.cannotLoadMessages)).finally(() => { state.isLoadingHistory = false; });
  }

  // Active la pagination quand le lecteur atteint le début de l'historique.
  elements.messages.addEventListener("scroll", () => { if (elements.messages.scrollTop < 40 && state.hasMoreHistory) loadHistory(state.oldestMessageId); });

  return {
    loadHistory,
    observeForReadReceipt,
    upsertMessage: (message) => upsertMessage(message, observeForReadReceipt),
    applyReceiptUpdate,
    applyReactionUpdate,
  };
}
