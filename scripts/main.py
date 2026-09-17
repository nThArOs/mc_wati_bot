# ============================================================
# LIBRARIES & IMPORTS
# ============================================================

import os
import sys

# Configuration de l'encodage standard UTF-8 sur Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from utils.bot_selector import select_bots
except ImportError:
    from scripts.utils.bot_selector import select_bots

try:
    from orchestrator import BotManager
except ImportError:
    try:
        from scripts.orchestrator import BotManager
    except ImportError:
        BotManager = None

from bot import MCBot


# ============================================================
# SÉLECTION ET DÉMARRAGE DES BOTS
# ============================================================

def start_selected_bots(selected=None):
    """Lance les bots sélectionnés par l'utilisateur ou la configuration."""
    bots_to_run = selected if selected is not None else select_bots()

    if not bots_to_run:
        print("Aucun bot sélectionné.")
        return []

    # Si plusieurs bots sont sélectionnés, utiliser l'orchestrateur multi-instances
    if len(bots_to_run) > 1 and BotManager is not None:
        manager = BotManager(fleet_config=bots_to_run)
        manager.start_fleet()
        manager.terminal_loop()
        return list(manager.bots.values())

    # Mode unitaire (un seul bot avec console terminal active)
    instances = []
    for idx, cfg in enumerate(bots_to_run):
        instance = MCBot(
            cfg["name"],
            enable_console=(idx == 0),
        )
        instances.append(instance)

    return instances


bots = start_selected_bots()
bot = bots[0] if bots else None
