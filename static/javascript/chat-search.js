// Isole le module de recherche pour éviter de polluer l'espace global de la page.
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
    // Protège une valeur utilisateur avant son insertion dans le HTML des résultats.
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function buildStartUrl(userId) {
    // Remplace le marqueur de l'URL par l'identifiant de l'utilisateur sélectionné.
    return startUrlTemplate.replace(SENTINEL, String(userId));
  }

  function renderHint(message) {
    // Affiche un message d'état lorsque la recherche ne peut pas produire de résultats.
    resultsContainer.innerHTML = `<p class="chat-search-hint">${escapeHtml(message)}</p>`;
  }

  function renderResults(users) {
    // Reconstruit la liste des utilisateurs retournés par l'API de recherche.
    if (users.length === 0) {
      resultsContainer.innerHTML = `<p class="chat-search-empty">Aucun utilisateur trouvé.</p>`;
      return;
    }
    resultsContainer.innerHTML = "";
    // Transforme chaque utilisateur en lien de démarrage de conversation.
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
    // Lance une recherche annulable afin qu'une saisie rapide ne mélange pas les réponses.
    if (currentController) {
      currentController.abort();
    }
    currentController = new AbortController();

    fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
      signal: currentController.signal,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      // Vérifie la réponse réseau avant de convertir son corps en JSON.
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Recherche indisponible pour le moment.");
        }
        return response.json();
      })
      // Rend les utilisateurs retournés par l'API.
      .then(function (data) {
        renderResults(data.users);
      })
      // Ignore les recherches annulées et signale les autres erreurs réseau.
      .catch(function (error) {
        if (error.name !== "AbortError") {
          renderHint("Recherche indisponible pour le moment.");
        }
      });
  }

  // Affiche immédiatement les utilisateurs disponibles, puis affine la liste
  // au fur et à mesure de la saisie.
  performSearch("");

  // Réagit à chaque saisie en appliquant une temporisation pour limiter les requêtes.
  input.addEventListener("input", function () {
    const query = input.value.trim();
    window.clearTimeout(debounceTimer);

    if (query.length === 0) {
      performSearch("");
      return;
    }

    // Attend une courte pause de frappe avant d'interroger le backend.
    debounceTimer = window.setTimeout(function () {
      performSearch(query);
    }, 250);
  });
})();
