"use strict";

import { config, elements, REACTION_EMOJI, REACTION_KEYS } from "./context.js";
import { escapeHtml, formatTime, isNearBottom, scrollToBottom, updateEmptyState } from "./helpers.js";

// Construit le HTML d'une pièce jointe image ou fichier.
export function buildAttachmentHtml(attachment) { if (attachment.is_image) return `<div class="chat-attachment"><img class="chat-attachment-image" src="${escapeHtml(attachment.file_url)}" alt="${escapeHtml(attachment.file_name)}"></div>`; const icon = attachment.is_pdf ? "📄" : "📃"; return `<div class="chat-attachment"><a class="chat-attachment-file" href="${escapeHtml(attachment.file_url)}" target="_blank" rel="noopener">${icon} ${escapeHtml(attachment.file_name)}</a></div>`; }

// Construit les pastilles de réactions d'un message.
export function buildReactionsHtml(message) { const entries = Object.entries(message.reactions || {}).filter(([, ids]) => ids.length > 0); if (!entries.length) return ""; const pills = entries.map(([key, ids]) => `<span class="chat-reaction-pill${ids.includes(config.currentUserId) ? " mine" : ""}" data-reaction="${key}">${REACTION_EMOJI[key] || key} ${ids.length}</span>`); return `<div class="chat-reactions">${pills.join("")}</div>`; }

// Construit le sélecteur des types de réaction disponibles.
export function buildReactionPickerHtml() { const options = REACTION_KEYS.map((key) => `<button type="button" class="chat-reaction-option" data-reaction="${key}" aria-label="${window.taskManagerI18n.reactWith} ${key.toLowerCase()}" title="${key.toLowerCase()}">${REACTION_EMOJI[key]}</button>`); return `<div class="chat-reaction-picker">${options.join("")}</div>`; }

// Construit les coches de livraison et de lecture du message courant.
function buildTicksHtml(message) { if (message.sender.id !== config.currentUserId) return ""; const status = message.receipt_status || { delivered: false, read: false }; return status.read ? `<span class="chat-ticks read">✓✓</span>` : status.delivered ? `<span class="chat-ticks">✓✓</span>` : `<span class="chat-ticks">✓</span>`; }

// Remplit une ligne DOM avec l'état complet d'un message.
export function fillMessageRow(row, message, isOwn) { const body = message.is_deleted ? `<em>${window.taskManagerI18n.deletedMessage}</em>` : `${message.content ? `<div class="chat-bubble-text">${escapeHtml(message.content).replace(/\n/g, "<br>")}</div>` : ""}${(message.attachments || []).map(buildAttachmentHtml).join("")}`; const edited = message.is_edited && !message.is_deleted ? `<span class="chat-bubble-edited">· ${window.taskManagerI18n.edited}</span>` : ""; const actions = isOwn && !message.is_deleted ? `<div class="chat-bubble-actions"><button type="button" class="chat-bubble-action" data-action="edit">${window.taskManagerI18n.edit}</button><button type="button" class="chat-bubble-action" data-action="delete">${window.taskManagerI18n.delete}</button></div>` : ""; row.innerHTML = `<div class="chat-bubble ${message.is_deleted ? "deleted" : ""}">${body}${buildReactionPickerHtml()}</div>${!message.is_deleted ? buildReactionsHtml(message) : ""}<div class="chat-bubble-meta"><span>${formatTime(message.created_at)}</span>${edited}${buildTicksHtml(message)}</div>${actions}`; }

// Crée une ligne DOM prête à être insérée dans l'historique.
export function renderMessageRow(message) { const row = document.createElement("div"); row.className = `chat-bubble-row ${message.sender.id === config.currentUserId ? "own" : "other"}`; row.dataset.messageId = message.id; fillMessageRow(row, message, message.sender.id === config.currentUserId); return row; }

// Insère ou actualise un message en évitant les doublons HTTP/WebSocket.
export function upsertMessage(message, observeForReadReceipt) { let row = elements.messages.querySelector(`[data-message-id="${message.id}"]`); const nearBottom = isNearBottom(); if (row) fillMessageRow(row, message, message.sender.id === config.currentUserId); else { row = renderMessageRow(message); elements.messages.appendChild(row); observeForReadReceipt(row, message); } if (nearBottom) scrollToBottom(); updateEmptyState(); }

// Actualise les coches associées aux accusés reçus.
export function applyReceiptUpdate(data) { data.message_ids.forEach((id) => { const row = elements.messages.querySelector(`[data-message-id="${id}"]`); const ticks = row && row.querySelector(".chat-ticks"); if (!ticks) return; ticks.textContent = "✓✓"; if (data.status === "read") ticks.classList.add("read"); }); }

// Actualise les réactions visibles d'une ligne.
export function applyReactionUpdate(data) { const row = elements.messages.querySelector(`[data-message-id="${data.message_id}"]`); if (!row) return; const html = buildReactionsHtml({ reactions: data.reactions }); const existing = row.querySelector(".chat-reactions"); if (existing) existing.outerHTML = html; else if (html) row.querySelector(".chat-bubble").insertAdjacentHTML("afterend", html); }
