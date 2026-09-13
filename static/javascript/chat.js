// Point d'entrée compact conservant le chemin de chargement historique du chat.
(function () {
  "use strict";
  import("./chat/main.js").catch(function (error) {
    console.error("Impossible de charger les modules du chat.", error);
  });
})();
