# Mineflayer Python Bot

Minecraft bot written in Python using Mineflayer through the
JavaScript bridge.

## Features

- Pathfinder
- Auto eat
- Patrol system (graphe urbain & quartiers)
- Points of interest
- Come to player
- Home command
- ELIZA chatbot
- Double authentification Microsoft (2FA / MFA) avec persistance des jetons
- Générateur de jetons TOTP 2FA (RFC 6238 / Microsoft Authenticator)
- Isolation des dossiers de profils de jetons par bot (`tokens/<nom_du_bot>`)
- Web inventory viewer (port 3000)

## Configuration 2FA & Jetons

Copiez `.env.example` en `.env` pour personnaliser les options :

- `AUTH_TOKENS_DIR` : Répertoire de stockage des jetons OAuth (par défaut `./tokens`).
- `AUTO_OPEN_BROWSER` : Ouvre automatiquement la page Microsoft Device Login (`true`/`false`).
- `MICROSOFT_TOTP_SECRET` : Clé secrète Base32 pour générer automatiquement le code 2FA TOTP.
- `ENABLE_HEADLESS_AUTH` : Active la connexion 100% autonome via Selenium en tâche de fond.

## Commandes Console 2FA

- `auth status` / `statut auth` : Affiche l'état des jetons en cache et du 2FA.
- `auth totp` : Génère le jeton TOTP actuel et affiche le temps restant avant expiration.
- `auth clear` : Supprime les jetons en cache pour forcer une nouvelle validation 2FA.

## Installation

### Python

```bash
pip install -r requirements.txt.txt
```

### Node.js

```bash
npm install
```

## Run

### Mode Bot Unique (Unitaire)
```bash
python scripts/Pathfind-chat.py
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
