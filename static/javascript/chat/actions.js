"use strict";

import { config, elements } from "./context.js";
import { getCookie, showToast } from "./helpers.js";

// Branche les réactions, suppressions et modifications via délégation d'événements.
export function bindActions(socket, stopTyping, applyReactionUpdate) {
  // Pose ou retire une réaction via WebSocket ou HTTP.
  function submitReaction(url, messageId, reaction) { const body = new FormData(); body.append("message_id", messageId); if (reaction) body.append("reaction", reaction); fetch(url, { method: "POST", headers: { "X-CSRFToken": getCookie("csrftoken") }, body }).then((response) => { if (!response.ok) throw new Error("La réaction n'a pas pu être enregistrée."); return response.json(); }).then(applyReactionUpdate).catch((error) => showToast(error.message)); }
  function setReaction(messageId, reaction) { if (socket.isOpen()) socket.sendEvent({ type: "reaction.set", message_id: messageId, reaction }); else submitReaction(config.reactionSetUrl, messageId, reaction); }
  function removeReaction(messageId) { if (socket.isOpen()) socket.sendEvent({ type: "reaction.remove", message_id: messageId }); else submitReaction(config.reactionRemoveUrl, messageId); }

  // Ouvre l'éditeur inline d'une bulle et restaure son contenu si nécessaire.
  function startInlineEdit(row, messageId) {
    const textEl = row.querySelector(".chat-bubble-text"); const currentText = textEl ? textEl.textContent : ""; const editArea = document.createElement("textarea"); editArea.className = "chat-text-input"; editArea.value = currentText; const bubble = row.querySelector(".chat-bubble"); const original = bubble.innerHTML; bubble.innerHTML = ""; bubble.appendChild(editArea); editArea.focus(); let settled = false;
    // Annule l'édition sans déclencher un envoi différé.
    function cancel() { if (!settled) { settled = true; bubble.innerHTML = original; } }
    // Valide l'édition si le texte a effectivement changé.
    function commit() { if (settled) return; settled = true; const newText = editArea.value.trim(); if (newText && newText !== currentText) socket.sendEvent({ type: "message.edit", message_id: messageId, content: newText }); else bubble.innerHTML = original; }
    editArea.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); commit(); } else if (event.key === "Escape") cancel(); }); editArea.addEventListener("blur", commit);
  }

  // Détermine l'action déclenchée sur une ligne de message dynamique.
  elements.messages.addEventListener("click", (event) => { const row = event.target.closest(".chat-bubble-row"); if (!row) return; const messageId = Number(row.dataset.messageId); const action = event.target.closest("[data-action]"); if (action) { if (action.dataset.action === "delete" && window.confirm("Supprimer ce message ?")) socket.sendEvent({ type: "message.delete", message_id: messageId }); else if (action.dataset.action === "edit") startInlineEdit(row, messageId); return; } const option = event.target.closest(".chat-reaction-option"); if (option) { const reaction = option.dataset.reaction; if (row.querySelector(`.chat-reaction-pill.mine[data-reaction="${reaction}"]`)) removeReaction(messageId); else setReaction(messageId, reaction); return; } const pill = event.target.closest(".chat-reaction-pill"); if (pill) { if (pill.classList.contains("mine")) removeReaction(messageId); return; } row.classList.toggle("show-actions"); });
}
