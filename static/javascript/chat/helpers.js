"use strict";

import { app, elements, state } from "./context.js";

// Protège une valeur externe avant son insertion dans le DOM.
export function escapeHtml(value) { const div = document.createElement("div"); div.textContent = value == null ? "" : String(value); return div.innerHTML; }

// Formate les horodatages ISO renvoyés par le backend.
export function formatTime(value) { return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }

// Récupère le cookie CSRF utilisé par les appels POST de secours.
export function getCookie(name) { const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)")); return match ? decodeURIComponent(match[2]) : null; }

// Affiche brièvement un message d'erreur ou d'information.
export function showToast(message) { const toast = document.createElement("div"); toast.className = "chat-toast"; toast.textContent = message; document.body.appendChild(toast); window.setTimeout(function () { toast.remove(); }, 3500); }

// Met à jour l'état de présence de l'autre utilisateur.
export function updatePresence(isOnline) { window.clearTimeout(state.presenceCheckTimer); app.classList.toggle("is-other-online", isOnline); if (elements.connectionStatus) elements.connectionStatus.textContent = isOnline ? window.taskManagerI18n.online : window.taskManagerI18n.offline; }

// Prépare le repli hors ligne si aucune présence n'est annoncée.
export function startPresenceCheck() { window.clearTimeout(state.presenceCheckTimer); state.presenceCheckTimer = window.setTimeout(function () { if (!app.classList.contains("is-other-online") && elements.connectionStatus) elements.connectionStatus.textContent = window.taskManagerI18n.offline; }, 3000); }

// Indique si la zone de messages est proche de son bas.
export function isNearBottom() { return elements.messages.scrollHeight - elements.messages.scrollTop - elements.messages.clientHeight < 120; }

// Positionne la zone de messages sur son dernier élément.
export function scrollToBottom() { elements.messages.scrollTop = elements.messages.scrollHeight; }

// Actualise l'affichage de la conversation vide.
export function updateEmptyState() { if (elements.emptyMessages) elements.emptyMessages.hidden = Boolean(elements.messages.querySelector("[data-message-id]")); }
