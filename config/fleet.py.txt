# ============================================================
# CONFIGURATION DE LA FLOTTE DE BOTS (mc_wati_bot)
# ============================================================

# Liste des instances déployées par l'orchestrateur
FLEET_CONFIG = [
    {
        "name": "bot-leader",
        "role": "leader",
        "port": 3000,
        "district": "Haute ville",
    },
    {
        "name": "bot-patrol-1",
        "role": "patrol",
        "port": 3001,
        "district": "place george orwell",
    },
    {
        "name": "bot-patrol-2",
        "role": "patrol",
        "port": 3002,
        "district": "quartier du theatre",
    },
]

# Intervalle de temporisation (en secondes) entre chaque connexion de bot
# (Staggering : prévient les kicks pour spam réseau et la saturation Microsoft)
STAGGER_DELAY = 7
