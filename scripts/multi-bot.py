from javascript import require, On, Once, AsyncTask, once, off
from simple_chalk import chalk
import os
import sys

# Import utils
try:
    from utils.auth_manager import (
        TokenManager,
        TOTPManager,
        MfaDeviceCodeHandler,
    )
except ImportError:
    from scripts.utils.auth_manager import (
        TokenManager,
        TOTPManager,
        MfaDeviceCodeHandler,
    )

# Import the javascript libraries
mineflayer = require("mineflayer")

# Global bot parameters
server_host = "localhost"
server_port = 3000
reconnect = True
auth_mode = os.getenv("AUTH_MODE", "microsoft")
auth_tokens_dir = os.getenv("AUTH_TOKENS_DIR", "./tokens")
auto_open_browser = (
    os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("true", "1", "yes")
)
totp_secret = os.getenv("MICROSOFT_TOTP_SECRET", "")


class MCBot:

    def __init__(self, bot_name):
        self.reconnect = reconnect
        self.bot_name = bot_name

        # Gestion des jetons et double authentification (2FA) isolée par bot
        self.token_manager = TokenManager(
            bot_name=bot_name,
            base_dir=auth_tokens_dir,
        )
        self.totp_manager = TOTPManager(
            secret=totp_secret,
        )
        self.mfa_handler = MfaDeviceCodeHandler(
            bot_name=bot_name,
            totp_manager=self.totp_manager,
            auto_open_browser=auto_open_browser,
            logger=lambda msg: print(f"[{bot_name}] {msg}"),
        )

        self.bot_args = {
            "host": server_host,
            "port": server_port,
            "username": bot_name,
            "auth": auth_mode,
            "profilesFolder": self.token_manager.get_profile_path(),
            "onMsaCode": self.mfa_handler.on_msa_code,
            "hideErrors": False,
        }

        if self.token_manager.has_cached_tokens():
            summary = self.token_manager.get_token_summary()
            print(
                chalk.green(
                    f"[{bot_name}] ✓ Jetons en cache trouvés ({summary['file_count']} fichier(s)). "
                    f"Connexion persistante."
                )
            )
        else:
            print(
                chalk.yellow(
                    f"[{bot_name}] Aucun jeton en cache. Authentification 2FA requise."
                )
            )

        self.start_bot()

    # Start mineflayer bot
    def start_bot(self):
        self.bot = mineflayer.createBot(self.bot_args)

        self.start_events()

    # Attach mineflayer events to bot
    def start_events(self):

        # Login event: Triggers on bot login
        @On(self.bot, "login")
        def login(this):

            # Displays which server you are currently connected to
            self.bot_socket = self.bot._client.socket
            print(
                f"[{self.bot_name}] Logged in to {self.bot_socket.server if self.bot_socket.server else self.bot_socket._host }"
            )

        # Kicked event: Triggers on kick from server
        @On(self.bot, "kicked")
        def kicked(this, reason, loggedIn):
            if loggedIn:
                print(f"[{self.bot_name}] Kicked whilst trying to connect: {reason}")

        # Chat event: Triggers on chat message
        @On(self.bot, "messagestr")
        def messagestr(this, message, messagePosition, jsonMsg, sender, verified=None):
            if messagePosition == "chat" and "quit" in message:
                self.reconnect = False
                this.quit()

        # End event: Triggers on disconnect from server
        @On(self.bot, "end")
        def end(this, reason):
            print(f"[{self.bot_name}] Disconnected: {reason}")

            # Turn off old events
            off(self.bot, "login", login)
            off(self.bot, "kicked", kicked)
            off(self.bot, "messagestr", messagestr)

            # Reconnect
            if self.reconnect:
                print(f"[{self.bot_name}] Attempting to reconnect")
                self.start_bot()

            # Last event listener
            off(self.bot, "end", end)


# Run function that starts the bot(s)
bot = MCBot("bot-1")
bot_2 = MCBot("bot-2")
bot_3 = MCBot("bot-3")
bot_4 = MCBot("bot-4")
bot_5 = MCBot("bot-5")
