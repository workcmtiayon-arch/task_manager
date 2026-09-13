"use strict";

import { app, config, elements, state } from "./context.js";
import { startPresenceCheck } from "./helpers.js";

// Crée le contrôleur WebSocket isolé du rendu et du composeur.
export function createSocketController(handleServerEvent, stopTyping) {
  let socket = null;

  // Envoie une commande JSON lorsque le socket est ouvert.
  function sendEvent(payload) { if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload)); }

  // Ouvre le socket, gère les événements réseau et programme les reconnexions.
  function connect() {
    const url = `${config.wsScheme}://${config.wsHost}/ws/chat/${config.conversationId}/`;
    socket = new WebSocket(url);
    socket.addEventListener("open", () => { state.reconnectDelay = 1000; if (elements.connectionStatus) elements.connectionStatus.textContent = "Vérification du statut…"; startPresenceCheck(); sendEvent({ type: "presence.announce" }); sendEvent({ type: "presence.request" }); });
    socket.addEventListener("message", (event) => handleServerEvent(JSON.parse(event.data)));
    socket.addEventListener("close", (event) => { stopTyping(); window.clearTimeout(state.presenceCheckTimer); app.classList.remove("is-other-online"); if (elements.connectionStatus) elements.connectionStatus.textContent = "Statut indisponible"; if (event.code === 4001) { window.location.href = config.loginUrl; return; } if (event.code === 4003) { window.location.href = config.conversationListUrl; return; } if (!state.intentionalClose) { window.setTimeout(connect, state.reconnectDelay); state.reconnectDelay = Math.min(state.reconnectDelay * 2, 15000); } });
    socket.addEventListener("error", () => socket.close());
  }

  // Indique si le canal temps réel peut recevoir une commande.
  function isOpen() { return Boolean(socket && socket.readyState === WebSocket.OPEN); }
  return { connect, sendEvent, isOpen };
}
