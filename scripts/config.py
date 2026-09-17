# ============================================================
# CONFIG SERVEUR / BOT
# ============================================================

SERVER_HOST = "game02.octoheberg.fr"
SERVER_PORT = 25571
BOT_VERSION = "1.21.11"
RECONNECT = True

# Configuration des bots proposés
BOTS = [
    {"name": "Moisurunautrecom", "console": True, "port": 3000, "role": "leader", "district": "Haute ville"},
    {"name": "nThArOs", "console": False, "port": 3001, "role": "patrol", "district": "place george orwell"},
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
