from config import BOTS
from bot import MCBot


bots = [
    MCBot(
        cfg["name"],
        enable_console=cfg.get("console", False),
    )
    for cfg in BOTS
]
