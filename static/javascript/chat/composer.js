"use strict";

import { config, elements, state } from "./context.js";
import { getCookie, showToast } from "./helpers.js";

// Branche la saisie, l'envoi texte et le téléversement de pièces jointes.
export function bindComposer(socket, upsertMessage) {
  // Termine l'indicateur de saisie après une pause ou un envoi.
  function stopTyping() { if (state.isTyping) { state.isTyping = false; socket.sendEvent({ type: "typing.stop" }); } }

  // Diffuse l'état de saisie pendant que l'utilisateur écrit.
  elements.textInput.addEventListener("input", () => { elements.textInput.style.height = "auto"; elements.textInput.style.height = `${Math.min(elements.textInput.scrollHeight, 120)}px`; if (elements.textInput.value.trim() && !state.isTyping) { state.isTyping = true; socket.sendEvent({ type: "typing.start" }); } window.clearTimeout(state.typingTimer); state.typingTimer = window.setTimeout(stopTyping, 900); });

  // Envoie avec Entrée tout en conservant Maj+Entrée pour les retours à la ligne.
  elements.textInput.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); elements.composer.requestSubmit(); } });

  // Envoie le message par WebSocket ou utilise le fallback HTTP.
  function sendTextMessage(text) {
    if (socket.isOpen()) { socket.sendEvent({ type: "message.send", content: text }); elements.textInput.value = ""; elements.textInput.style.height = "auto"; stopTyping(); elements.textInput.focus(); return; }
    const body = new FormData(); body.append("content", text); elements.sendButton.disabled = true;
    fetch(config.messageSendUrl, { method: "POST", headers: { "X-CSRFToken": getCookie("csrftoken") }, body }).then((response) => { if (!response.ok) return response.json().catch(() => ({})).then((data) => { throw new Error(data.detail || "Le message n'a pas pu être envoyé."); }); return response.json(); }).then((message) => { upsertMessage(message); elements.textInput.value = ""; elements.textInput.style.height = "auto"; stopTyping(); }).catch((error) => showToast(error.message || "Le message n'a pas pu être envoyé.")).finally(() => { elements.sendButton.disabled = false; elements.textInput.focus(); });
  }

  // Envoie une pièce jointe au backend puis remet le composeur à zéro.
  function uploadAttachment(file) {
    const body = new FormData(); body.append("file", file); elements.sendButton.disabled = true; elements.attachmentPreview.textContent = `Envoi de ${file.name}...`;
    fetch(config.attachmentUrl, { method: "POST", headers: { "X-CSRFToken": getCookie("csrftoken") }, body }).then((response) => { if (!response.ok) return response.text().then((text) => { throw new Error(text || "Échec de l'envoi de la pièce jointe."); }); return response.json(); }).then(() => { state.pendingAttachment = null; elements.attachmentInput.value = ""; elements.attachmentPreview.textContent = ""; elements.textInput.value = ""; elements.textInput.style.height = "auto"; }).catch((error) => showToast(error.message || "Échec de l'envoi de la pièce jointe.")).finally(() => { elements.sendButton.disabled = false; });
  }

  // Mémorise le fichier sélectionné avant sa confirmation par l'utilisateur.
  elements.attachmentInput.addEventListener("change", () => { const file = elements.attachmentInput.files[0]; if (!file) return; state.pendingAttachment = file; elements.attachmentPreview.textContent = `Fichier prêt à l'envoi : ${file.name}`; });

  // Intercepte la soumission pour choisir entre pièce jointe et texte.
  elements.composer.addEventListener("submit", (event) => { event.preventDefault(); if (state.pendingAttachment) { uploadAttachment(state.pendingAttachment); return; } const text = elements.textInput.value.trim(); if (text) sendTextMessage(text); });
  return { stopTyping };
}
