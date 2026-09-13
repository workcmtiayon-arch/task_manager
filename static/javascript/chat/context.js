"use strict";

// Centralise la configuration DOM et l'état mutable partagé par les modules du chat.
const app = document.getElementById("chat-app");
const config = app ? {
  conversationId: app.dataset.conversationId,
  currentUserId: Number(app.dataset.currentUserId),
  otherUserId: Number(app.dataset.otherUserId),
  messagesUrl: app.dataset.messagesUrl,
  messageSendUrl: app.dataset.messageSendUrl,
  attachmentUrl: app.dataset.attachmentUrl,
  reactionSetUrl: app.dataset.reactionSetUrl,
  reactionRemoveUrl: app.dataset.reactionRemoveUrl,
  conversationListUrl: app.dataset.conversationListUrl,
  loginUrl: app.dataset.loginUrl,
  wsScheme: app.dataset.wsScheme,
  wsHost: app.dataset.wsHost,
} : null;
const elements = app ? {
  messages: document.getElementById("chat-messages"),
  composer: document.getElementById("chat-composer"),
  textInput: document.getElementById("chat-text-input"),
  sendButton: document.getElementById("chat-send-btn"),
  attachmentInput: document.getElementById("chat-attachment-input"),
  attachmentPreview: document.getElementById("chat-attachment-preview"),
  emptyMessages: document.getElementById("chat-empty-messages"),
  connectionStatus: document.getElementById("chat-connection-status"),
  typingIndicator: document.getElementById("chat-typing-indicator"),
} : null;
const REACTION_EMOJI = { LIKE: "👍", LOVE: "❤️", LAUGH: "😂", WOW: "😮", SAD: "😢", ANGRY: "😠" };
const REACTION_KEYS = Object.keys(REACTION_EMOJI);
const state = { oldestMessageId: null, hasMoreHistory: true, isLoadingHistory: false, pendingAttachment: null, typingTimer: null, presenceCheckTimer: null, isTyping: false, intentionalClose: false, reconnectDelay: 1000 };

export { app, config, elements, REACTION_EMOJI, REACTION_KEYS, state };
