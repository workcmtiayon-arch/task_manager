"use strict";

import { app, config, elements, state } from "./context.js";
import { showToast, updatePresence } from "./helpers.js";
import { applyReactionUpdate } from "./render.js";
import { createHistory } from "./history.js";
import { createSocketController } from "./socket.js";
import { bindComposer } from "./composer.js";
import { bindActions } from "./actions.js";

// Initialise les modules de la conversation uniquement lorsque son conteneur existe.
function initializeChat() {
  if (!app || !config || !elements.messages) return;
  let history;
  let composer;
  const handleServerEvent = (data) => {
    switch (data.type) {
      case "message.new": case "message.edited": case "message.deleted": history.upsertMessage(data); break;
      case "receipt.update": history.applyReceiptUpdate(data); break;
      case "reaction.update": history.applyReactionUpdate(data); break;
      case "typing.update": elements.typingIndicator.hidden = !data.is_typing; elements.typingIndicator.textContent = data.is_typing ? `${data.username} écrit…` : ""; break;
      case "presence.update": if (Number(data.user_id) === config.otherUserId) updatePresence(Boolean(data.is_online)); break;
      case "presence.request": if (Number(data.requester_id) !== config.currentUserId) socket.sendEvent({ type: "presence.announce" }); break;
      case "connection.ready": if (elements.connectionStatus && !app.classList.contains("is-other-online")) elements.connectionStatus.textContent = "Vérification du statut…"; break;
      case "error": showToast(data.detail || "Une erreur est survenue."); break;
      default: break;
    }
  };
  const socket = createSocketController(handleServerEvent, () => composer && composer.stopTyping());
  history = createHistory(socket.sendEvent);
  composer = bindComposer(socket, history.upsertMessage);
  bindActions(socket, composer.stopTyping, applyReactionUpdate);
  history.loadHistory(null);
  socket.connect();
  // Empêche une reconnexion pendant la fermeture volontaire de la page.
  window.addEventListener("beforeunload", () => { state.intentionalClose = true; });
}

initializeChat();
