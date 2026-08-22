(function () {
  "use strict";

  const input = document.getElementById("chat-search-input");
  const resultsContainer = document.getElementById("chat-search-results");
  if (!input || !resultsContainer) {
    return;
  }

  const searchUrl = resultsContainer.dataset.searchUrl;
  const startUrlTemplate = resultsContainer.dataset.startUrlTemplate;
  const SENTINEL = "999999999";

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function buildStartUrl(userId) {
    return startUrlTemplate.replace(SENTINEL, String(userId));
  }

  function renderHint(message) {
    resultsContainer.innerHTML = `<p class="chat-search-hint">${escapeHtml(message)}</p>`;
  }

  function renderResults(users) {
    if (users.length === 0) {
      resultsContainer.innerHTML = `<p class="chat-search-empty">Aucun utilisateur trouvé.</p>`;
      return;
    }
    resultsContainer.innerHTML = "";
    users.forEach(function (user) {
      const link = document.createElement("a");
      link.href = buildStartUrl(user.id);
      link.className = "chat-search-result";
      link.innerHTML = `
        <span class="chat-avatar">${escapeHtml(user.username.slice(0, 1).toUpperCase())}</span>
        <span>${escapeHtml(user.username)}</span>
      `;
      resultsContainer.appendChild(link);
    });
  }

  let debounceTimer = null;
  let currentController = null;

  function performSearch(query) {
    if (currentController) {
      currentController.abort();
    }
    currentController = new AbortController();

    fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
      signal: currentController.signal,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Recherche indisponible pour le moment.");
        }
        return response.json();
      })
      .then(function (data) {
        renderResults(data.users);
      })
      .catch(function (error) {
        if (error.name !== "AbortError") {
          renderHint("Recherche indisponible pour le moment.");
        }
      });
  }

  // Affiche immédiatement les utilisateurs disponibles, puis affine la liste
  // au fur et à mesure de la saisie.
  performSearch("");

  input.addEventListener("input", function () {
    const query = input.value.trim();
    window.clearTimeout(debounceTimer);

    if (query.length === 0) {
      performSearch("");
      return;
    }

    debounceTimer = window.setTimeout(function () {
      performSearch(query);
    }, 250);
  });
})();
