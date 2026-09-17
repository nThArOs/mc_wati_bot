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
- ELIZA chatbot (one independent conversation per bot)
- Multi-bot ready: run several bot accounts at once from one process

## Project structure

| File | Responsibility |
|---|---|
| `config.py` | Server address, bot accounts, timing/behaviour settings |
| `points.py` | World data: points of interest, districts, navigation graph |
| `movement.py` | Graph pathfinding, patrol and one-shot travel engine |
| `chest.py` | Chest interaction and delivery logic |
| `commands.py` | Command dispatch (terminal + in-game chat) and the console loop |
| `bot.py` | The `MCBot` class, mineflayer setup and events |
| `main.py` | Entry point: starts every bot listed in `config.BOTS` |

`scripts/Pathfind-chat.py` is kept as a thin shim (`from main import bot`)
so older run configurations still work.

## Installation

### Python

pip install -r requirements.txt

### Node.js

npm install

## Run

python scripts/main.py

## Multi-bot

Edit `config.BOTS` to list the accounts to start:

```python
BOTS = [
    {"name": "pathfinder-bot", "console": True},
    {"name": "second-account", "console": False},
]
```

Each entry needs its own Minecraft/Microsoft account (two bots can't
share a username). Only one entry should have `"console": True` at a
time — that's the one whose terminal reads your typed commands; the
others only respond to in-game chat. Every bot gets its own ELIZA
conversation and its own patrol/travel state, nothing is shared.

## Commands

Available from the terminal (console bot only) and from in-game chat:

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

In-game chat also understands `viens`/`come to me` and a few French
`va à ...` phrasings.

## Roadmap

- **Nether hub travel**: extend the graph so `chemin`/`livraison` can
  reach points outside the town by routing through nether portals
  (portal points paired per dimension, route steps typed `walk` vs
  `portal`, waiting for the dimension change instead of pathfinding
  across it). Not implemented yet — see project notes for the planned
  design.
