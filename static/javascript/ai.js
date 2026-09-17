document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('ai-assistant-form');
    var input = document.getElementById('ai-assistant-input');
    var send = document.getElementById('ai-assistant-send');
    var windowEl = document.querySelector('.ai-chat-window');
    var conversationId = null;
    if (!form || !input || !send || !windowEl) return;

    function addMessage(text, kind) {
        var message = document.createElement('div');
        message.className = 'ai-chat-message ai-chat-message--' + kind;
        message.textContent = text;
        windowEl.appendChild(message);
        windowEl.scrollTop = windowEl.scrollHeight;
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var content = input.value.trim();
        if (!content) return;
        addMessage(content, 'user');
        input.value = '';
        send.disabled = true;
        fetch(form.dataset.chatUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value},
            body: JSON.stringify({content: content, conversation_id: conversationId})
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) throw new Error(data.detail || 'Unable to contact Gemini.');
                return data;
            });
        }).then(function (data) {
            conversationId = data.conversation_id;
            addMessage(data.answer, 'assistant');
        }).catch(function (error) {
            addMessage(error.message, 'system');
        }).finally(function () {
            send.disabled = false;
            input.focus();
        });
    });
});
