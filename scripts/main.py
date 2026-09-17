from config import BOTS
from bot import MCBot


bots = [
    MCBot(
        cfg["name"],
        enable_console=cfg.get("console", False),
    )
    for cfg in BOTS
]

bot = bots[0] if bots else None

