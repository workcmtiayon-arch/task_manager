(function () {
  "use strict";

  const app = document.getElementById("chat-app");
  if (!app) {
    return;
  }

  // ---------------------------------------------------------------
  // Configuration (lue depuis les attributs data-* du template)
  // ---------------------------------------------------------------

  const config = {
    conversationId: app.dataset.conversationId,
    currentUserId: parseInt(app.dataset.currentUserId, 10),
    currentUsername: app.dataset.currentUsername,
    otherUsername: app.dataset.otherUsername,
    isInvitation: app.dataset.isInvitation === "true",
    messagesUrl: app.dataset.messagesUrl,
    messageSendUrl: app.dataset.messageSendUrl,
    attachmentUrl: app.dataset.attachmentUrl,
    reactionSetUrl: app.dataset.reactionSetUrl,
    reactionRemoveUrl: app.dataset.reactionRemoveUrl,
    conversationListUrl: app.dataset.conversationListUrl,
    invitationsUrl: app.dataset.invitationsUrl,
    loginUrl: app.dataset.loginUrl,
    wsScheme: app.dataset.wsScheme,
    wsHost: app.dataset.wsHost,
  };

  const REACTION_EMOJI = {
    LIKE: "👍",
    LOVE: "❤️",
    LAUGH: "😂",
    WOW: "😮",
    SAD: "😢",
    ANGRY: "😠",
  };
  const REACTION_KEYS = Object.keys(REACTION_EMOJI);

  const messagesEl = document.getElementById("chat-messages");
  const composerEl = document.getElementById("chat-composer");
  const textInput = document.getElementById("chat-text-input");
  const sendBtn = document.getElementById("chat-send-btn");
  const attachmentInput = document.getElementById("chat-attachment-input");
  const attachmentPreview = document.getElementById("chat-attachment-preview");
  const emptyMessagesEl = document.getElementById("chat-empty-messages");
  const connectionStatusEl = document.getElementById("chat-connection-status");
  const typingIndicatorEl = document.getElementById("chat-typing-indicator");

  let oldestMessageId = null;
  let hasMoreHistory = true;
  let isLoadingHistory = false;
  let pendingAttachment = null;
  let typingTimer = null;
  let isTyping = false;
  const readMarked = new Set();

  // ---------------------------------------------------------------
  // Utilitaires
  // ---------------------------------------------------------------

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "chat-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(function () {
      toast.remove();
    }, 3500);
  }

  function isNearBottom() {
    return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 120;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function updateEmptyState() {
    if (!emptyMessagesEl) {
      return;
    }
    emptyMessagesEl.hidden = Boolean(messagesEl.querySelector("[data-message-id]"));
  }

  // ---------------------------------------------------------------
  // Rendu d'un message (création ou mise à jour)
  // ---------------------------------------------------------------

  function buildAttachmentHtml(attachment) {
    if (attachment.is_image) {
      return `
        <div class="chat-attachment">
          <img class="chat-attachment-image" src="${escapeHtml(attachment.file_url)}" alt="${escapeHtml(attachment.file_name)}">
        </div>`;
    }
    const icon = attachment.is_pdf ? "📄" : "📃";
    return `
      <div class="chat-attachment">
        <a class="chat-attachment-file" href="${escapeHtml(attachment.file_url)}" target="_blank" rel="noopener">
          ${icon} ${escapeHtml(attachment.file_name)}
        </a>
      </div>`;
  }

  function buildReactionsHtml(message) {
    const entries = Object.entries(message.reactions || {}).filter(([, userIds]) => userIds.length > 0);
    if (entries.length === 0) {
      return "";
    }
    const pills = entries.map(function ([key, userIds]) {
      const mine = userIds.includes(config.currentUserId) ? " mine" : "";
      return `<span class="chat-reaction-pill${mine}" data-reaction="${key}">${REACTION_EMOJI[key] || key} ${userIds.length}</span>`;
    });
    return `<div class="chat-reactions">${pills.join("")}</div>`;
  }

  function buildReactionPickerHtml() {
    const options = REACTION_KEYS.map(function (key) {
      return `<button type="button" class="chat-reaction-option" data-reaction="${key}" aria-label="Réagir avec ${key.toLowerCase()}" title="${key.toLowerCase()}">${REACTION_EMOJI[key]}</button>`;
    });
    return `<div class="chat-reaction-picker">${options.join("")}</div>`;
  }

  function buildTicksHtml(message) {
    if (message.sender.id !== config.currentUserId) {
      return "";
    }
    const status = message.receipt_status || { delivered: false, read: false };
    if (status.read) {
      return `<span class="chat-ticks read">✓✓</span>`;
    }
    if (status.delivered) {
      return `<span class="chat-ticks">✓✓</span>`;
    }
    return `<span class="chat-ticks">✓</span>`;
  }

  function renderMessageRow(message) {
    const isOwn = message.sender.id === config.currentUserId;
    const row = document.createElement("div");
    row.className = `chat-bubble-row ${isOwn ? "own" : "other"}`;
    row.dataset.messageId = message.id;
    fillMessageRow(row, message, isOwn);
    return row;
  }

  function fillMessageRow(row, message, isOwn) {
    const bodyHtml = message.is_deleted
      ? `<em>Message supprimé</em>`
      : `${message.content ? `<div class="chat-bubble-text">${escapeHtml(message.content).replace(/\n/g, "<br>")}</div>` : ""}
         ${(message.attachments || []).map(buildAttachmentHtml).join("")}`;

    const editedLabel = message.is_edited && !message.is_deleted
      ? `<span class="chat-bubble-edited">· modifié</span>`
      : "";

    const actionsHtml = isOwn && !message.is_deleted
      ? `<div class="chat-bubble-actions">
           <button type="button" class="chat-bubble-action" data-action="edit">Modifier</button>
           <button type="button" class="chat-bubble-action" data-action="delete">Supprimer</button>
         </div>`
      : "";

    row.innerHTML = `
      <div class="chat-bubble ${message.is_deleted ? "deleted" : ""}">
        ${bodyHtml}
        ${buildReactionPickerHtml()}
      </div>
      ${!message.is_deleted ? buildReactionsHtml(message) : ""}
      <div class="chat-bubble-meta">
        <span>${formatTime(message.created_at)}</span>
        ${editedLabel}
        ${buildTicksHtml(message)}
      </div>
      ${actionsHtml}
    `;
  }

  function upsertMessage(message) {
    let row = messagesEl.querySelector(`[data-message-id="${message.id}"]`);
    const wasNearBottom = isNearBottom();

    if (row) {
      const isOwn = message.sender.id === config.currentUserId;
      fillMessageRow(row, message, isOwn);
    } else {
      row = renderMessageRow(message);
      messagesEl.appendChild(row);
      observeForReadReceipt(row, message);
    }

    if (wasNearBottom) {
      scrollToBottom();
    }
    updateEmptyState();
  }

  // ---------------------------------------------------------------
  // Historique (chargement initial + pagination vers le haut)
  // ---------------------------------------------------------------

  function loadHistory(beforeId) {
    if (isLoadingHistory || (!hasMoreHistory && beforeId)) {
      return;
    }
    isLoadingHistory = true;

    let url = `${config.messagesUrl}?limit=50`;
    if (beforeId) {
      url += `&before=${encodeURIComponent(beforeId)}`;
    }

    fetch(url)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Impossible de charger les messages.");
        }
        return response.json();
      })
      .then(function (data) {
        const messages = data.messages;
        if (messages.length === 0) {
          hasMoreHistory = false;
          updateEmptyState();
          return;
        }
        if (messages.length < 50) {
          hasMoreHistory = false;
        }

        if (beforeId) {
          const previousScrollHeight = messagesEl.scrollHeight;
          const fragment = document.createDocumentFragment();
          const pendingRows = messages.map(function (message) {
            const row = renderMessageRow(message);
            fragment.appendChild(row);
            return { row: row, message: message };
          });
          messagesEl.insertBefore(fragment, messagesEl.firstChild);
          messagesEl.scrollTop = messagesEl.scrollHeight - previousScrollHeight;
          // Important : on observe APRÈS insertion dans le DOM, avec la
          // référence directe à chaque ligne. Interroger le DOM par
          // data-message-id ici (avant insertion) échouerait silencieusement,
          // puisque les lignes ne seraient pas encore attachées à #chat-messages.
          pendingRows.forEach(function (entry) {
            observeForReadReceipt(entry.row, entry.message);
          });
        } else {
          messages.forEach(function (message) {
            const row = renderMessageRow(message);
            messagesEl.appendChild(row);
            observeForReadReceipt(row, message);
          });
          scrollToBottom();
        }

        oldestMessageId = messages[0].id;
        updateEmptyState();
      })
      .catch(function () {
        showToast("Impossible de charger les messages.");
      })
      .finally(function () {
        isLoadingHistory = false;
      });
  }

  messagesEl.addEventListener("scroll", function () {
    if (messagesEl.scrollTop < 40 && hasMoreHistory) {
      loadHistory(oldestMessageId);
    }
  });

  // ---------------------------------------------------------------
  // Statuts de lecture (IntersectionObserver)
  // ---------------------------------------------------------------

  const readObserver = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) {
          return;
        }
        const messageId = entry.target.dataset.messageId;
        if (readMarked.has(messageId)) {
          return;
        }
        readMarked.add(messageId);
        readObserver.unobserve(entry.target);
        sendEvent({ type: "message.read", message_id: parseInt(messageId, 10) });
      });
    },
    { root: messagesEl, threshold: 0.6 }
  );

  function observeForReadReceipt(row, message) {
    if (message.sender.id === config.currentUserId || message.is_deleted) {
      return;
    }
    const target = row || messagesEl.querySelector(`[data-message-id="${message.id}"]`);
    if (target) {
      readObserver.observe(target);
    }
  }

  // ---------------------------------------------------------------
  // WebSocket
  // ---------------------------------------------------------------

  let socket = null;
  let reconnectDelay = 1000;
  let intentionalClose = false;

  function connectSocket() {
    const url = `${config.wsScheme}://${config.wsHost}/ws/chat/${config.conversationId}/`;
    socket = new WebSocket(url);

    socket.addEventListener("open", function () {
      reconnectDelay = 1000;
      app.classList.add("is-connected");
      if (connectionStatusEl) connectionStatusEl.textContent = "En ligne";
    });

    socket.addEventListener("message", function (event) {
      const data = JSON.parse(event.data);
      handleServerEvent(data);
    });

    socket.addEventListener("close", function (event) {
      app.classList.remove("is-connected");
      if (connectionStatusEl) connectionStatusEl.textContent = "Connexion en cours…";
      if (event.code === 4001) {
        window.location.href = config.loginUrl;
        return;
      }
      if (event.code === 4003) {
        window.location.href = config.conversationListUrl;
        return;
      }
      if (!intentionalClose) {
        window.setTimeout(connectSocket, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 15000);
      }
    });

    socket.addEventListener("error", function () {
      socket.close();
    });
  }

  function sendEvent(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }

  function handleServerEvent(data) {
    switch (data.type) {
      case "message.new":
      case "message.edited":
      case "message.deleted":
        upsertMessage(data);
        break;
      case "receipt.update":
        applyReceiptUpdate(data);
        break;
      case "reaction.update":
        applyReactionUpdate(data);
        break;
      case "typing.update":
        if (typingIndicatorEl) {
          typingIndicatorEl.hidden = !data.is_typing;
          typingIndicatorEl.textContent = data.is_typing ? `${data.username} écrit…` : "";
        }
        break;
      case "connection.ready":
        if (connectionStatusEl) connectionStatusEl.textContent = "En ligne";
        break;
      case "error":
        showToast(data.detail || "Une erreur est survenue.");
        break;
      default:
        break;
    }
  }

  function applyReceiptUpdate(data) {
    data.message_ids.forEach(function (messageId) {
      const row = messagesEl.querySelector(`[data-message-id="${messageId}"]`);
      if (!row) {
        return;
      }
      const ticksEl = row.querySelector(".chat-ticks");
      if (!ticksEl) {
        return;
      }
      if (data.status === "read") {
        ticksEl.textContent = "✓✓";
        ticksEl.classList.add("read");
      } else if (data.status === "delivered") {
        ticksEl.textContent = "✓✓";
      }
    });
  }

  function applyReactionUpdate(data) {
    const row = messagesEl.querySelector(`[data-message-id="${data.message_id}"]`);
    if (!row) {
      return;
    }
    const existing = row.querySelector(".chat-reactions");
    const html = buildReactionsHtml({ reactions: data.reactions });
    if (existing) {
      existing.outerHTML = html;
    } else if (html) {
      row.querySelector(".chat-bubble").insertAdjacentHTML("afterend", html);
    }
  }

  function setReaction(messageId, reaction) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      sendEvent({ type: "reaction.set", message_id: messageId, reaction: reaction });
      return;
    }
    submitReaction(config.reactionSetUrl, messageId, reaction);
  }

  function removeReaction(messageId) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      sendEvent({ type: "reaction.remove", message_id: messageId });
      return;
    }
    submitReaction(config.reactionRemoveUrl, messageId);
  }

  function submitReaction(url, messageId, reaction) {
    const body = new FormData();
    body.append("message_id", messageId);
    if (reaction) {
      body.append("reaction", reaction);
    }
    fetch(url, { method: "POST", headers: { "X-CSRFToken": getCookie("csrftoken") }, body: body })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("La réaction n'a pas pu être enregistrée.");
        }
        return response.json();
      })
      .then(applyReactionUpdate)
      .catch(function (error) { showToast(error.message); });
  }

  // ---------------------------------------------------------------
  // Composition et envoi
  // ---------------------------------------------------------------

  textInput.addEventListener("input", function () {
    textInput.style.height = "auto";
    textInput.style.height = `${Math.min(textInput.scrollHeight, 120)}px`;
    if (textInput.value.trim() && !isTyping) {
      isTyping = true;
      sendEvent({ type: "typing.start" });
    }
    window.clearTimeout(typingTimer);
    typingTimer = window.setTimeout(stopTyping, 900);
  });

  function stopTyping() {
    if (isTyping) {
      isTyping = false;
      sendEvent({ type: "typing.stop" });
    }
  }

  textInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      composerEl.requestSubmit();
    }
  });

  composerEl.addEventListener("submit", function (event) {
    event.preventDefault();

    if (pendingAttachment) {
      uploadAttachment(pendingAttachment);
      return;
    }

    const text = textInput.value.trim();
    if (!text) {
      return;
    }
    sendTextMessage(text);
  });

  function sendTextMessage(text) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      sendEvent({ type: "message.send", content: text });
      textInput.value = "";
      textInput.style.height = "auto";
      stopTyping();
      textInput.focus();
      return;
    }
    const formData = new FormData();
    formData.append("content", text);
    sendBtn.disabled = true;

    fetch(config.messageSendUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body: formData,
    })
      .then(function (response) {
        if (!response.ok) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            throw new Error(data.detail || "Le message n'a pas pu être envoyé.");
          });
        }
        return response.json();
      })
      .then(function (message) {
        // La diffusion WebSocket peut arriver avant ou après cette réponse.
        // upsertMessage évite le doublon dans les deux cas.
        upsertMessage(message);
        textInput.value = "";
        textInput.style.height = "auto";
        stopTyping();
      })
      .catch(function (error) {
        showToast(error.message || "Le message n'a pas pu être envoyé.");
      })
      .finally(function () {
        sendBtn.disabled = false;
        textInput.focus();
      });
  }

  attachmentInput.addEventListener("change", function () {
    const file = attachmentInput.files[0];
    if (!file) {
      return;
    }
    pendingAttachment = file;
    attachmentPreview.textContent = `Fichier prêt à l'envoi : ${file.name}`;
  });

  function uploadAttachment(file) {
    const formData = new FormData();
    formData.append("file", file);

    sendBtn.disabled = true;
    attachmentPreview.textContent = `Envoi de ${file.name}...`;

    fetch(config.attachmentUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body: formData,
    })
      .then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) {
            throw new Error(text || "Échec de l'envoi de la pièce jointe.");
          });
        }
        return response.json();
      })
      .then(function () {
        // Le message créé est reçu via l'évènement WebSocket "message.new",
        // diffusé par la vue elle-même (voir chat/views.py) : pas besoin
        // de l'ajouter manuellement ici.
        pendingAttachment = null;
        attachmentInput.value = "";
        attachmentPreview.textContent = "";
        // Le backend (conversation_attachment_upload) crée toujours le
        // message avec content="" : la V1 n'associe pas de légende texte
        // à une pièce jointe. On vide donc aussi le champ de texte, pour
        // ne pas laisser affiché un texte qui, en réalité, n'a jamais été
        // envoyé nulle part.
        textInput.value = "";
        textInput.style.height = "auto";
      })
      .catch(function (error) {
        showToast(error.message || "Échec de l'envoi de la pièce jointe.");
      })
      .finally(function () {
        sendBtn.disabled = false;
      });
  }

  // ---------------------------------------------------------------
  // Actions sur un message : éditer / supprimer / réagir
  // (délégation d'évènements : un seul écouteur pour tous les messages,
  //  y compris ceux ajoutés dynamiquement après coup)
  // ---------------------------------------------------------------

  messagesEl.addEventListener("click", function (event) {
    const row = event.target.closest(".chat-bubble-row");
    if (!row) {
      return;
    }
    const messageId = parseInt(row.dataset.messageId, 10);

    const actionBtn = event.target.closest("[data-action]");
    if (actionBtn) {
      const action = actionBtn.dataset.action;
      if (action === "delete") {
        if (window.confirm("Supprimer ce message ?")) {
          sendEvent({ type: "message.delete", message_id: messageId });
        }
      } else if (action === "edit") {
        startInlineEdit(row, messageId);
      }
      return;
    }

    const reactionOption = event.target.closest(".chat-reaction-option");
    if (reactionOption) {
      const reaction = reactionOption.dataset.reaction;
      const alreadyMine = row.querySelector(
        `.chat-reaction-pill.mine[data-reaction="${reaction}"]`
      );
      if (alreadyMine) {
        removeReaction(messageId);
      } else {
        setReaction(messageId, reaction);
      }
      return;
    }

    const reactionPill = event.target.closest(".chat-reaction-pill");
    if (reactionPill) {
      if (reactionPill.classList.contains("mine")) {
        removeReaction(messageId);
      }
      return;
    }

    // Clic/tap direct sur la bulle elle-même (aucun bouton visé) : bascule
    // l'affichage des actions et du sélecteur de réactions. Indispensable
    // sur mobile/tactile, où ":hover" (seul mécanisme ci-dessus) n'existe
    // tout simplement pas.
    row.classList.toggle("show-actions");
  });

  function startInlineEdit(row, messageId) {
    const textEl = row.querySelector(".chat-bubble-text");
    const currentText = textEl ? textEl.textContent : "";

    const editArea = document.createElement("textarea");
    editArea.className = "chat-text-input";
    editArea.value = currentText;

    const bubble = row.querySelector(".chat-bubble");
    const original = bubble.innerHTML;
    bubble.innerHTML = "";
    bubble.appendChild(editArea);
    editArea.focus();

    // Un textarea retiré du DOM déclenche quand même un évènement "blur" :
    // sans ce garde-fou, annuler avec Échap déclencherait ensuite, via ce
    // blur différé, un commit() non désiré sur un élément déjà détaché.
    let settled = false;

    function cancel() {
      if (settled) {
        return;
      }
      settled = true;
      bubble.innerHTML = original;
    }

    function commit() {
      if (settled) {
        return;
      }
      settled = true;
      const newText = editArea.value.trim();
      if (newText && newText !== currentText) {
        sendEvent({ type: "message.edit", message_id: messageId, content: newText });
      } else {
        bubble.innerHTML = original;
      }
    }

    editArea.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        commit();
      } else if (event.key === "Escape") {
        cancel();
      }
    });
    editArea.addEventListener("blur", commit);
  }

  // ---------------------------------------------------------------
  // Démarrage
  // ---------------------------------------------------------------

  loadHistory(null);
  connectSocket();

  window.addEventListener("beforeunload", function () {
    intentionalClose = true;
  });
})();
