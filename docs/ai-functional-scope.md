# Module AI — cadrage fonctionnel

## 1. Objectif

L’assistant AI aide un utilisateur à organiser ses projets, ses tâches et ses sous-tâches depuis un espace de conversation intégré à Task Manager.

L’assistant doit rester un outil d’aide : aucune modification des données ne doit être appliquée sans confirmation explicite de l’utilisateur.

## 2. Utilisateurs concernés

- Un utilisateur authentifié.
- Chaque utilisateur ne peut consulter et manipuler que ses propres projets, tâches et sous-tâches.
- Un utilisateur non authentifié ne peut pas utiliser l’assistant.

## 3. Périmètre du MVP

### Consultation et compréhension

- Résumer un projet et son avancement.
- Lister les tâches en retard, à faire ou en cours.
- Identifier les tâches sans échéance.
- Expliquer l’état global d’un projet à partir de ses tâches et sous-tâches.

### Préparation d’actions

- Proposer une décomposition d’un objectif en tâches et sous-tâches.
- Proposer des échéances ou un ordre de priorité, sans les enregistrer automatiquement.
- Préparer la création ou la modification d’une tâche sous forme de proposition lisible.

### Conversation

- Envoyer une demande textuelle.
- Recevoir une réponse textuelle contextualisée.
- Conserver l’historique de la conversation pour l’utilisateur.
- Afficher les erreurs de service de manière compréhensible.

## 4. Actions nécessitant une confirmation

Les opérations suivantes pourront être proposées par l’assistant, mais ne seront exécutées qu’après confirmation claire :

- créer un projet, une tâche ou une sous-tâche ;
- modifier un titre, une description, un statut ou une date ;
- supprimer une tâche ou une sous-tâche ;
- réorganiser les sous-tâches.

La confirmation devra présenter précisément les changements prévus avant leur application.

## 5. Hors périmètre du MVP

- Accès aux données d’autres utilisateurs.
- Envoi automatique d’e-mails ou de messages externes.
- Exécution d’actions irréversibles sans confirmation.
- Analyse de fichiers ou de pièces jointes.
- Remplacement du chat temps réel entre utilisateurs.
- Entraînement ou personnalisation permanente du modèle avec les données de l’utilisateur.

## 6. Règles fonctionnelles principales

1. Le contexte transmis au fournisseur AI est limité aux données nécessaires à la demande.
2. Les données appartenant à un autre utilisateur ne doivent jamais apparaître dans le contexte ou la réponse.
3. Une réponse AI peut être informative ou proposer une action, mais une proposition n’est pas une modification.
4. Toute action confirmée doit être validée côté serveur avec les permissions Django habituelles.
5. Une réponse doit signaler clairement lorsqu’elle ne dispose pas d’informations suffisantes.
6. Le système doit gérer l’indisponibilité, le délai d’attente et les erreurs de quota du fournisseur AI.
7. Le comportement doit fonctionner en français et en anglais, selon la langue de l’utilisateur.

## 7. Critères d’acceptation du MVP

- Un utilisateur connecté peut ouvrir l’espace AI et envoyer une demande.
- Une demande reçoit une réponse basée uniquement sur ses propres projets et tâches.
- L’historique d’une conversation est conservé et réaffichable.
- Une demande de modification produit une proposition de changement avec une confirmation explicite.
- Une modification confirmée est contrôlée et appliquée côté serveur.
- Un utilisateur ne peut pas lire ou modifier les conversations, projets ou tâches d’un autre utilisateur.
- Les erreurs de fournisseur AI sont affichées sans exposer de clé API ni de détail sensible.
- Des tests couvrent les permissions, le contexte utilisateur, les propositions et les confirmations.

## 8. Découpage technique prévu après validation

1. Configurer le fournisseur AI et les variables d’environnement.
2. Créer les modèles de conversation et de message.
3. Implémenter un service de construction du contexte utilisateur.
4. Ajouter l’endpoint sécurisé de conversation.
5. Remplacer la prévisualisation par l’interface fonctionnelle.
6. Ajouter les propositions et confirmations d’actions.
7. Ajouter les tests, les limites d’usage et la documentation.
