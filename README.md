# Mineflayer Python Bot

Minecraft bot written in Python using Mineflayer through the
JavaScript bridge.

## Features

- Pathfinder (forced to follow built roads, no digging/tower shortcuts)
- Auto eat
- Points of interest, districts (quartiers) and a navigation graph
- `chemin`/`route` : one-shot travel to a point, shortest path over the graph
- `patrouille` : endless patrol, either the whole town or a single district
- `livraison` : empty a chest near a point and deliver its contents to another
- Come to player, home command
- Agent de conversation LLM via Ollama (une conversation indépendante par bot)
- Double authentification Microsoft (2FA / MFA) avec persistance des jetons
- Générateur de jetons TOTP 2FA (RFC 6238 / Microsoft Authenticator)
- Isolation des dossiers de profils de jetons par bot (`tokens/<nom_du_bot>`)
- Web inventory viewer (port 3000 ou configurable)
- Multi-bot ready : gestion multi-comptes unifiée ou flotte échelonnée

## Project structure

| File | Responsibility |
|---|---|
| `config.py` | Server address, bot accounts, timing/behaviour settings |
| `points.py` | World data: points of interest, districts, navigation graph |
| `movement.py` | Graph pathfinding, patrol and one-shot travel engine |
| `chest.py` | Chest interaction and delivery logic |
| `commands.py` | Command dispatch (terminal + in-game chat) and the console loop |
| `bot.py` | The `MCBot` class, mineflayer setup and events. Also the entry point used by the orchestrator (subprocess, env-var driven) |
| `llm_agent.py` | Conversation agent backed by Ollama, used as the chat fallback |
| `main.py` | Entry point: starts every bot listed in `config.BOTS` |
| `orchestrator.py` | Multi-bot fleet manager with staggered startup and chat routing |
| `utils/auth_manager.py` | OAuth2 device code handler, token cache and TOTP 2FA |

## Configuration 2FA & Jetons

Copiez `.env.example` en `.env` pour personnaliser les options :

- `AUTH_TOKENS_DIR` : Répertoire de stockage des jetons OAuth (par défaut `./tokens`).
- `AUTO_OPEN_BROWSER` : Ouvre automatiquement la page Microsoft Device Login (`true`/`false`).
- `MICROSOFT_TOTP_SECRET` : Clé secrète Base32 pour générer automatiquement le code 2FA TOTP.
- `ENABLE_HEADLESS_AUTH` : Active la connexion 100% autonome via Playwright/Selenium en tâche de fond.

## Configuration Agent de conversation (LLM)

L'agent de chat tourne sur [Ollama](https://ollama.com) en local :

```bash
ollama serve
ollama pull llama3.1
```

- `OLLAMA_HOST` : URL du serveur Ollama (par défaut `http://localhost:11434`).
- `OLLAMA_MODEL` : Modèle utilisé pour la conversation (par défaut `llama3.1`).

Si Ollama n'est pas installé ou injoignable, le bot répond juste "Salut !" au spawn et ignore silencieusement les messages de chat sans commande.

## Installation

### Python

```bash
pip install -r requirements.txt
```

### Node.js

```bash
npm install
```

## Run

### Mode Bot Unique (Unitaire)
```bash
python scripts/main.py
```

### Mode Flotte Multi-Bots (Orchestrateur BotManager)
```bash
python scripts/orchestrator.py
```

Dans la console de l'orchestrateur :
- `status` : Affiche l'état des processus et ports de chaque bot.
- `all: <commande>` : Diffuse un ordre à tous les bots (ex. `all: go home`, `all: stop`).
- `<nom_du_bot>: <cmd>` : Pilote un bot précis (ex. `bot-patrol-1: patrouille Haute ville`).
- `fleet patrol` : Lance les patrouilles sectorielles sur les quartiers assignés.
- In-game : utilisez les préfixes `!all <action>` ou `!<nom_du_bot> <action>`.

### Multi-bot classique (via config.BOTS)

Modifiez `config.BOTS` pour lister les comptes à démarrer :

```python
BOTS = [
    {"name": "pathfinder-bot", "console": True},
    {"name": "second-account", "console": False},
]
```

Chaque entrée nécessite son propre compte Minecraft/Microsoft. Un seul bot doit avoir `"console": True` à la fois (celui qui écoute la console du terminal).

## Commands

### Commandes Générales (Terminal & Chat en jeu)

- `go <point|player>` / `go home` — walk straight to a destination
- `home` — alias for `go home`
- `chemin <point>` / `route <point>` — walk to a point following the graph
- `patrouille` / `patrouille <quartier>` — endless patrol, town-wide or one district
- `livraison <point>` — empty the nearest chest at `<point>` and deliver it
- `quartiers` — list known districts
- `players` — list visible players
- `say <message>` — chat
- `stop` — cancel the current task
- `quit` — disconnect

In-game chat also understands `viens`/`come to me` et les commandes en français (`va à ...`).

### Commandes Console 2FA

- `auth status` / `statut auth` : Affiche l'état des jetons en cache et du 2FA.
- `auth totp` : Génère le jeton TOTP actuel et affiche le temps restant avant expiration.
- `auth clear` : Supprime les jetons en cache pour forcer une nouvelle validation 2FA.

## Roadmap

- **Nether hub travel**: extend the graph so `chemin`/`livraison` can
  reach points outside the town by routing through nether portals
  (portal points paired per dimension, route steps typed `walk` vs
  `portal`, waiting for the dimension change instead of pathfinding
  across it).
