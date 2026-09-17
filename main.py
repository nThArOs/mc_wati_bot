# ============================================================
# POINT D'ENTRÉE PRINCIPAL (mc_wati_bot)
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

# Configuration des chemins d'importation
root_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(root_dir, "scripts")

if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from utils.bot_selector import select_bots
from orchestrator import BotManager
from bot import MCBot


def main():
    selected = select_bots()
    if not selected:
        print("Aucun bot sélectionné.")
        return

    if len(selected) > 1:
        manager = BotManager(fleet_config=selected)
        manager.start_fleet()
        manager.terminal_loop()
    else:
        cfg = selected[0]
        MCBot(cfg["name"], enable_console=True)


if __name__ == "__main__":
    main()
