# GEMINI.md - Spécifications, Architecture et Normes du Projet mc_wati_bot

Ce document sert de référence pour le projet **mc_wati_bot**. Il décrit le principe de fonctionnement du bot, recense les conventions de nommage appliquées, et formalise les règles d'architecture et de normalisation du code.

---

## 1. Principe du Projet

### 1.1 Présentation Générale
**mc_wati_bot** est un agent autonome pour Minecraft (version 1.21.x) conçu en Python. Il utilise la bibliothèque Node.js **Mineflayer** par l'intermédiaire d'un bridge inter-langage (`javascript` pour Python).

Le bot est capable de se connecter à un serveur Minecraft distant ou local, de s'authentifier (notamment via Microsoft), de percevoir son environnement, de naviguer de manière autonome dans le monde, d'interagir avec les joueurs et de répondre à des ordres complexes formulés en langage naturel ou via des commandes dédiées.

### 1.2 Fonctionnalités Principales
- **Navigation Intelligente & Pathfinding** : Déplacement autonome reposant sur `mineflayer-pathfinder` avec calcul d'objectifs tridimensionnels (`GoalNear`).
- **Topologie Urbaine & Patrouilles (Graphes)** :
  - Définition de points d'intérêt (`POINTS_INTERET`), de quartiers (`QUARTIERS`) et d'un maillage de circulation (`GRAPH`).
  - Patrouille cyclique ou ponctuelle le long des arêtes du graphe urbain via un parcours en profondeur (DFS) ou le calcul du plus court chemin (algorithme BFS).
  - Détection automatique du point d'entrée le plus proche pour démarrer un trajet sans téléportation ni déplacement incohérent.
- **Interactions Joueurs** :
  - Localisation dynamique des entités de joueurs par nom ou UUID (`find_player`, `find_player_uuid`).
  - Suivi et ralliement vers un joueur sur sollicitation textuelle (ex. *"viens"*, *"come to me"*).
- **Double Interface de Contrôle** :
  - Console REPL interactive dans le terminal (`terminal_loop`).
  - Réception et interprétation des messages du chat in-game Minecraft (`messagestr`).
- **Chatbot Conversationnel de Repli (ELIZA)** :
  - Intégration du moteur classique ELIZA (`eliza.py` et script `doctor.txt`).
  - Lorsque le bot reçoit un message qui ne correspond à aucune commande connue, ELIZA prend le relais pour maintenir une conversation vivante.
- **Survie & Besoins Vitaux** :
  - Gestion automatique de la nourriture via le plugin `mineflayer-auto-eat` avec seuil de déclenchement configurable.
- **Supervision en Temps Réel** :
  - Serveur web HTTP local embarqué (`mineflayer-web-inventory`) exposant l'inventaire du bot sur le port 3000.
- **Tolérance aux Pannes & Reconnexion** :
  - Détection des déconnexions et kicks avec boucle de reconnexion automatique paramétrable.

---

## 2. Conventions de Nommage

L'ensemble de la base de code suit des conventions claires, uniformes et adaptées aux interactions hybrides Python/Node.js.

### 2.1 Arborescence & Fichiers
- **Dossiers** : Minuscules strictes, mots simples ou composés sans séparateur (`config`, `eliza`, `scripts`, `utils`).
- **Scripts exécutables / Points d'entrée** : Kebab-case ou notation hybride historiquement conservée (`scripts/Pathfind-chat.py`, `scripts/multi-bot.py`).
- **Modules utilitaires et bibliothèques** : `snake_case` (`utils/vec3_conversion.py`, `eliza/eliza.py`).
- **Fichiers de données et de templates** : Suffixes `.txt` ajoutés aux formats natifs (`package.json.txt`, `requirements.txt.txt`, `points.py.txt`, `server.py.txt`) afin de prévenir les règles d'exclusion `.gitignore` (notamment sur `*.json` lié aux tokens d'authentification) ou pour servir de gabarits.

### 2.2 Classes
- **Notation** : `PascalCase` (UpperCamelCase).
- **Exemples** : `MCBot`, `Eliza`, `Key`, `Decomp`.

### 2.3 Fonctions et Méthodes
- **Notation** : `snake_case`.
- **Verbes d'action** : Priorité aux préfixes explicites (`start_`, `go_`, `find_`, `build_`, `cancel_`, `handle_`, `run_`).
- **Exemples** :
  - `start_bot()`
  - `go_to_coords(x, y, z, mode, message)`
  - `go_to_destination(destination)`
  - `shortest_graph_path(start, target)`
  - `build_patrol_route(allowed_points, start_point)`
- **Méthodes internes / privées** : Préfixées d'un tiret bas `_` (`_match_decomp_r()`).

### 2.4 Variables et Paramètres
- **Variables locales et arguments** : `snake_case` descriptif (`bot_name`, `server_host`, `patrol_active`, `task_generation`, `nearest_dist`).
- **Variables mathématiques / coordonnées** : Abréviations courtes standardisées (`x`, `y`, `z`, `px`, `pz`, `dist`, `v`, `e`).

### 2.5 Constantes et Paramètres de Configuration
- **Notation** : `UPPER_SNAKE_CASE`.
- **Exemples** :
  - `SERVER_HOST`, `SERVER_PORT`, `BOT_NAME`, `BOT_VERSION`, `RECONNECT`
  - `WEB_INVENTORY_PORT`, `PATROL_WAIT`, `PATROL_RADIUS`
  - `HOME`, `POINTS_INTERET`, `QUARTIERS`, `GRAPH`

### 2.6 États et Modes Métier
- **Notation** : Chaînes de caractères en majuscules strictes.
- **Exemples** : `"IDLE"`, `"HOME"`, `"POINT"`, `"PLAYER"`, `"PATROL_ROUTE"`.

### 2.7 Clés de Données & Toponymes
- **Coordonnées géométriques** : Clés minuscules `"x"`, `"y"`, `"z"`.
- **Points d'intérêt** : Chaînes en minuscules, gestion bilingue et tolérance aux accents (`"usine a fer"` / `"usine à fer"`, `"cathedral"` / `"cathedrale"`).
- **Quartiers** : Libellés textuels descriptifs (`"Haute ville"`, `"place george orwell"`, `"quartier du theatre"`).

---

## 3. Règles d'Architecture du Code

### 3.1 Bridge Inter-Langage (Python ↔ JavaScript)
- L'intégration s'effectue via le package Python `javascript` :
  ```python
  from javascript import require, On, off
  ```
- Les modules Node.js (`mineflayer`, `mineflayer-pathfinder`, `mineflayer-auto-eat`, `mineflayer-web-inventory`, `vec3`) sont importés dynamiquement au début du script.
- La gestion des événements Mineflayer s'effectue au moyen du décorateur `@On(instance, "event_name")` au sein d'une méthode dédiée (`start_events()`).
- La limite d'écouteurs Node.js (`EventEmitter`) doit être expressément débrayée avec `self.bot.setMaxListeners(0)` pour éviter les avertissements de fuite mémoire lors des mises à jour continues d'objectifs de pathfinding.

### 3.2 Modèle de Concurrence et Multithreading
- **Thread Principal** : Initialise la connexion et maintient la boucle événementielle Node.js.
- **Threads Démons (`daemon=True`)** :
  - Dédiés aux écoutes bloquantes (ex. console utilisateur `terminal_loop`).
  - Dédiés aux temporisations asynchrones (ex. `continue_patrol` avec `time.sleep()`).
- **Gestion des Conflits Asynchrones (Task Generation Pattern)** :
  - Pour éviter les courses critiques lorsqu'une commande interrompt une autre tâche asynchrone, un compteur `self.task_generation` est incrémenté à chaque nouveau mouvement ou annulation (`cancel_task()`, `new_task()`).
  - Tout callback différé (ex. temporisation avant prochaine étape de patrouille) doit vérifier la validité de sa génération via `self.task_valid(generation)` avant d'agir.

### 3.3 Découpage Modulaire et Résolution des Dépendances
Le projet est architecturé autour de modules clairs :
- `config/` : Centralisation des paramètres réseau, coordonnées et points d'intérêt.
- `utils/` : Fonctions d'aide purement algorithmiques ou de formatage (`vec3_conversion.py`).
- `eliza/` : Moteur conversationnel autonome et scripts de dialogue (`doctor.txt`).
- `scripts/` : Scripts de déploiement et exécution directe (`Pathfind-chat.py`, `multi-bot.py`).
- **Règle de portabilité d'exécution** : Des miroirs locaux des dossiers utilitaires (`scripts/eliza`, `scripts/utils`) accompagnent les scripts afin que l'exécution soit fonctionnelle que le script soit lancé depuis la racine du projet ou depuis le sous-dossier `scripts/`.

### 3.4 Dispatcheur Centralisé de Commandes
- Toutes les instructions (qu'elles proviennent de l'entrée console terminal ou du chat multijoueur) convergent vers un dispatcheur unique : `handle_command(self, command, sender=None)`.
- Cela garantit une stricte parité des fonctionnalités entre l'opérateur local et les joueurs in-game.

### 3.5 Résilience Réseau
- L'événement de fin de connexion (`@On(self.bot, "end")`) prend en charge la purge des ressources, la temporisation de sécurité (`time.sleep(2)`) et la relance automatique via `start_bot()` si le drapeau `self.reconnect` est actif.

### 3.6 Automatisation des Commits par l'Agent IA
- Après chaque évolution, correctif ou fonctionnalité finalisée avec succès :
  1. Lancer la suite de tests unitaires (`python -m pytest tests/`).
  2. Si les tests passent, exécuter un commit Git propre regroupant les fichiers modifiés et créés.
  3. Formater le message selon la norme Conventional Commits (ex. `feat(auth): ...`, `feat(orchestrator): ...`, `fix(pathfind): ...`).
  4. Indiquer le hash et le message du commit dans la réponse finale.

---

## 4. Normalisation et Règles de Style du Code

### 4.1 Découpage Visuel et Bannières de Sections
Le code source utilise un partitionnement vertical rigoureux basé sur des bannières de commentaires de **60 caractères** :
```python
# ============================================================
# NOM DE SECTION MAJEURE (ex: LIBRARIES, CONFIG, BOT, EVENTS)
# ============================================================

# ----------------------------------------------------
# Sous-section ou commande spécifique
# ----------------------------------------------------
```
Chaque grande responsabilité (Utilitaires, Pathfinding, Destinations, Joueurs, Graphe, Commandes, Événements) doit être isolée par ce schéma de bannières.

### 4.2 Standardisation de la Journalisation (Logging)
Les journaux d'activité en console doivent utiliser `simple_chalk` pour apporter un retour visuel instantané et sémantique :
- **Préfixe obligatoire** : `[<nom_du_bot>] <message>` via la méthode centrale `self.log()`.
- **Code couleur sémantique** :
  - `chalk.green` : Succès opérationnel, arrivée à destination, connexion établie, symbole de validation `✓`.
  - `chalk.red` / `chalk.redBright` : Erreurs critiques, échecs de pathfinding, expulsions (`kicked`).
  - `chalk.yellow` : Alertes, messages chat entrants, annulation ou arrêt de tâche (`✓ Tâche arrêtée`).
  - `chalk.magenta` : Coordonnées de ciblage et trajectoires de déplacement.
  - `chalk.cyan` / `chalk.cyanBright` : Métadonnées d'itinéraires, relances réseau, répliques ELIZA.
  - `chalk.gray` : Lignes d'aide, synthèses secondaires, listes contextuelles.

### 4.3 Traitement des Exceptions
- Les interactions avec le bridge Node.js ou les entités Minecraft non garanties (entité hors champ, joueur déconnecté) doivent être systématiquement encapsulées dans des blocs `try...except`.
- Les erreurs non critiques sont capturées avec logging explicite en rouge ou passées sous silence (`except Exception: pass`) si l'échec d'une opération secondaire (comme envoyer un message de chat en déconnexion) ne doit pas planter le processus.

### 4.4 Formatage & Espacement PEP 8
- **Indentation** : 4 espaces stricts (pas de tabulations).
- **Aération verticale** :
  - 2 lignes vides entre les définitions de classes, méthodes et fonctions majeures.
  - Sauts de ligne intentionnels au sein des méthodes pour détacher les blocs logiques.
- **Multiligne** : Découpage systématique des appels de fonctions à arguments multiples et des chaînes de formatage longues pour respecter la lisibilité.

### 4.5 Bilinguisme et Langue de Rédaction
- **Code technique** : En anglais (noms de fonctions, variables, structures de données, classes).
- **Interface utilisateur / In-game** : En français (messages envoyés sur le chat Minecraft, feedbacks de patrouille et confirmations vocales du bot).
- **Interpréteur de commandes** : Prise en charge conjointe des alias en français et en anglais (ex. `patrouille` / `patrol`, `home` / `maison`, `va à` / `go`).
