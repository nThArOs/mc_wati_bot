# ============================================================
# CONFIG SERVEUR / BOT
# ============================================================

SERVER_HOST = "game02.octoheberg.fr"
SERVER_PORT = 25571
BOT_VERSION = "1.21.11"
RECONNECT = True

# Un compte Minecraft/Microsoft différent est nécessaire pour
# chaque bot (deux comptes ne peuvent pas partager un pseudo).
# Un seul bot avec "console": True à la fois : c'est celui qui
# lira les commandes tapées dans le terminal. Les autres ne
# répondent qu'au chat en jeu.
BOTS = [
    {"name": "pathfinder-bot", "console": True},
    # {"name": "pathfinder-bot-2", "console": False},
]

# Maison : indépendante des autres destinations
HOME = {
    "x": 1802,
    "y": 130,
    "z": -1328,
}


# ============================================================
# PATROUILLE / TRAJETS
# ============================================================

PATROL_WAIT = 1

PATROL_STUCK_CHECK_INTERVAL = 5
PATROL_STUCK_MIN_DISTANCE = 1.5
PATROL_STUCK_CHECKS = 3


# ============================================================
# LIVRAISON
# ============================================================

DELIVERY_DESTINATION = "salle des coffres"
CHEST_SEARCH_RADIUS = 8
