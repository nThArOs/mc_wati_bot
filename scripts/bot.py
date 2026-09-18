from javascript import require, On, off
from simple_chalk import chalk
from llm_agent import ConversationAgent
from utils.vec3_conversion import vec3_to_str
try:
    from utils.auth_manager import (
        TokenManager,
        TOTPManager,
        MfaDeviceCodeHandler,
        get_bot_credentials,
    )
except ImportError:
    from scripts.utils.auth_manager import (
        TokenManager,
        TOTPManager,
        MfaDeviceCodeHandler,
        get_bot_credentials,
    )
from config import SERVER_HOST, SERVER_PORT, BOT_VERSION, RECONNECT, HOME
from points import POINTS_INTERET
from movement import MovementMixin
from chest import ChestMixin
from commands import CommandsMixin
import os
import sys
import time
import threading

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


# ============================================================
# LIBRARIES
# ============================================================

mineflayer = require("mineflayer")
pathfinder_lib = require("mineflayer-pathfinder")

try:
    auto_eat_module = require("mineflayer-auto-eat")
    auto_eat = (
        getattr(auto_eat_module, "loader", None)
        or getattr(auto_eat_module, "default", None)
        or auto_eat_module
    )
except Exception as e:
    print(f"[bot.py] mineflayer-auto-eat indisponible : {e}")
    auto_eat = None

try:
    web_inventory = require("mineflayer-web-inventory")
except Exception as e:
    print(f"[bot.py] mineflayer-web-inventory indisponible : {e}")
    web_inventory = None

try:
    armor_manager_module = require("mineflayer-armor-manager")
    armor_manager = (
        getattr(armor_manager_module, "default", None)
        or armor_manager_module
    )
except Exception as e:
    print(f"[bot.py] mineflayer-armor-manager indisponible : {e}")
    armor_manager = None

try:
    prismarine_viewer = require("prismarine-viewer").mineflayer
except Exception as e:
    print(f"[bot.py] prismarine-viewer indisponible : {e}")
    prismarine_viewer = None

vec3 = require("vec3")


# ============================================================
# BOT
# ============================================================

class MCBot(MovementMixin, ChestMixin, CommandsMixin):

    def __init__(self, name, enable_console=False, pipe_mode=False):
        self.bot_name = name
        self.enable_console = enable_console
        self.pipe_mode = pipe_mode
        self.reconnect = RECONNECT
        self.mode = "IDLE"
        self.patrol_active = False
        self.patrol_route = []
        self.patrol_index = 0
        self.patrol_label = None
        self.route_loop = False
        self.route_wait = 0
        self.route_arrived_event = threading.Event()
        self.task_generation = 0
        self.web_inventory_started = False
        self.viewer_started = False

        # Fleet : rôle et quartier assignés par l'orchestrateur (env vars),
        # vides en mode bot unique.
        self.bot_role = os.getenv("BOT_ROLE", "leader").lower()
        self.is_leader = self.bot_role == "leader"
        self.assigned_district = os.getenv("ASSIGNED_DISTRICT", "")
        self.web_inventory_port = int(os.getenv("WEB_INVENTORY_PORT", "3000"))
        self.viewer_port = int(
            os.getenv("VIEWER_PORT", str(self.web_inventory_port + 100))
        )

        # Un agent de conversation par bot : indispensable dès qu'on
        # fait tourner plusieurs bots en même temps (chacun garde
        # sa propre conversation, pas de state partagé).
        self.conversation = ConversationAgent(name)

        # Gestion des jetons et double authentification (2FA) isolée par bot
        auth_tokens_dir = os.getenv("AUTH_TOKENS_DIR", "./tokens")
        auto_open_browser = (
            os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("true", "1", "yes")
        )
        enable_headless = (
            os.getenv("ENABLE_HEADLESS_AUTH", "false").lower() in ("true", "1", "yes")
        )
        creds = get_bot_credentials(name)

        self.token_manager = TokenManager(
            bot_name=name,
            base_dir=auth_tokens_dir,
        )
        self.totp_manager = TOTPManager(
            secret=creds["totp_secret"],
        )
        self.mfa_handler = MfaDeviceCodeHandler(
            bot_name=name,
            totp_manager=self.totp_manager,
            auto_open_browser=auto_open_browser,
            logger=self.log,
            headless_email=creds["email"],
            headless_password=creds["password"],
            enable_headless=enable_headless,
        )

        self.bot_args = {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "username": name,
            "auth": "microsoft",
            "version": BOT_VERSION,
            "hideErrors": False,
            "profilesFolder": self.token_manager.get_profile_path(),
            "onMsaCode": self.mfa_handler.on_msa_code,
        }

        if self.token_manager.has_cached_tokens():
            summary = self.token_manager.get_token_summary()
            self.log(
                chalk.green(
                    f"✓ Jetons de session détectés dans {summary['profile_dir']} "
                    f"({summary['file_count']} fichier(s)). Connexion persistante sans 2FA."
                )
            )
        else:
            self.log(
                chalk.yellow(
                    "Aucun jeton en cache. Authentification 2FA requise."
                )
            )

        self.start_bot()

        if self.enable_console:
            threading.Thread(
                target=self.terminal_loop,
                daemon=True,
            ).start()
        elif self.pipe_mode:
            threading.Thread(
                target=self.pipe_listener_loop,
                daemon=True,
            ).start()


    # ========================================================
    # UTILITIES
    # ========================================================

    def log(self, message):
        try:
            name = getattr(self.bot, "username", None) or self.bot_name
        except Exception:
            name = self.bot_name

        text = f"[{name}] {message}"
        try:
            print(text)
        except UnicodeEncodeError:
            try:
                encoding = sys.stdout.encoding or "utf-8"
                print(text.encode(encoding, errors="replace").decode(encoding))
            except Exception:
                safe_text = text.replace("✓", "[OK]").encode("ascii", errors="replace").decode("ascii")
                print(safe_text)


    def new_task(self, mode):
        self.task_generation += 1
        self.mode = mode
        return self.task_generation


    def task_valid(self, generation):
        return generation == self.task_generation


    def stop_movement(self):
        try:
            self.bot.pathfinder.setGoal(None)
        except Exception:
            pass


    def reset_patrol_state(self):
        self.patrol_active = False
        self.patrol_route = []
        self.patrol_index = 0
        self.patrol_label = None
        self.route_loop = False
        self.route_wait = 0


    def cancel_task(self):
        self.task_generation += 1
        self.reset_patrol_state()
        self.mode = "IDLE"
        self.stop_movement()


    def chat(self, message):
        try:
            self.bot.chat(message)
        except Exception:
            pass


    # ========================================================
    # PATHFINDING
    # ========================================================

    def pathfind(self, position):
        try:
            goal = pathfinder_lib.pathfinder.goals.GoalNear(
                position["x"],
                position["y"],
                position["z"],
                1,
            )
            self.bot.pathfinder.setGoal(goal)

        except Exception as e:
            self.log(
                chalk.red(f"Pathfinding error: {e}")
            )


    def go_to_coords(self, x, y, z, mode, message):
        generation = self.new_task(mode)

        self.reset_patrol_state()
        self.stop_movement()

        target = vec3(x, y, z)

        self.log(
            chalk.magenta(
                f"Déplacement vers "
                f"{vec3_to_str(target)}"
            )
        )

        self.chat(message)
        self.pathfind(target)

        return generation


    # ========================================================
    # DESTINATIONS
    # ========================================================

    def go_home(self):
        return self.go_to_coords(
            HOME["x"],
            HOME["y"],
            HOME["z"],
            "HOME",
            "Je rentre à la maison.",
        )


    def go_to_point(self, name):
        name = name.strip().lower()

        if name not in POINTS_INTERET:
            self.log(
                chalk.red(
                    f"Point d'intérêt inconnu : {name}"
                )
            )
            return False

        x, y, z = POINTS_INTERET[name]

        self.go_to_coords(
            x,
            y,
            z,
            "POINT",
            f"J'arrive à {name} !",
        )

        return True


    # ========================================================
    # GO INTELLIGENT
    #
    # go home
    # go cathedral
    # go nThArOs
    #
    # HOME → lieu → joueur
    # ========================================================

    def go_to_destination(self, destination):
        destination = destination.strip()

        if not destination:
            self.log(
                chalk.yellow(
                    "Destination manquante."
                )
            )
            return

        lower = destination.lower()

        # HOME reste indépendant
        if lower in ("home", "maison"):
            self.go_home()
            return

        # LIEU
        if lower in POINTS_INTERET:
            self.go_to_point(lower)
            return

        # JOUEUR
        if self.go_to_player(destination):
            return

        self.log(
            chalk.red(
                f"Destination introuvable : {destination}"
            )
        )


    # ========================================================
    # PLAYERS
    # ========================================================

    def find_player(self, name):
        name = str(name).strip().lower()

        try:
            players = self.bot.players

            # Les objets JS n'ont pas de .keys()/.items() Python :
            # "for x in proxy" déclenche le vrai protocole d'énumération
            # du bridge (javascript/JSPyBridge), à la différence d'un
            # appel de méthode qui chercherait une propriété JS inexistante.
            for player_name in players:
                if str(player_name).lower() != name:
                    continue

                data = players[player_name]

                if data and data.entity:
                    return player_name, data.entity

        except Exception:
            import traceback
            self.log(
                chalk.red(
                    f"Player search error:\n{traceback.format_exc()}"
                )
            )

        return None


    def find_player_uuid(self, uuid):
        try:
            players = self.bot.players

            for player_name in players:
                data = players[player_name]

                if data and str(data.uuid) == str(uuid) and data.entity:
                    return data.entity

        except Exception:
            import traceback
            self.log(
                chalk.red(
                    f"Player search error (uuid):\n{traceback.format_exc()}"
                )
            )

        return None


    def go_to_player(self, name):
        result = self.find_player(name)

        if not result:
            self.log(
                chalk.red(
                    f"Joueur introuvable ou sans entité chargée : {name}"
                )
            )
            return False

        real_name, entity = result
        pos = entity.position

        self.go_to_coords(
            pos.x,
            pos.y,
            pos.z,
            "PLAYER",
            f"J'arrive vers {real_name} !",
        )

        return True


    def list_players(self):
        print()

        try:
            players = self.bot.players

            for name in players:
                data = players[name]

                if data and data.entity:
                    print(
                        f"  - {name} "
                        f"{vec3_to_str(data.entity.position)}"
                    )
                else:
                    print(
                        f"  - {name} (position inconnue)"
                    )

        except Exception:
            import traceback
            self.log(
                chalk.red(
                    f"List players error:\n{traceback.format_exc()}"
                )
            )

        print()


    # ========================================================
    # MINEFLAYER
    # ========================================================

    def start_bot(self):
        self.bot = mineflayer.createBot(
            self.bot_args
        )

        # La patrouille/pathfinding change de goal en continu,
        # ce qui ajoute des listeners internes à chaque appel.
        # Ce n'est pas une vraie fuite, on lève juste la limite.
        self.bot.setMaxListeners(0)

        self.bot.loadPlugin(
            pathfinder_lib.pathfinder
        )

        # On a des routes construites en dur (le chemin de
        # montagne route 1-4 par ex.) : on ne veut pas que le
        # bot creuse un raccourci ou pose des blocs, il doit
        # suivre le terrain/la route existante.
        movements = pathfinder_lib.Movements(self.bot)
        movements.canDig = False
        movements.allow1by1towers = False
        movements.canPlace = False
        self.bot.pathfinder.setMovements(movements)

        if auto_eat and callable(auto_eat):
            try:
                self.bot.loadPlugin(auto_eat)
                eat_opts = {
                    "priority": "foodPoints",
                    "startAt": 14,
                    "bannedFood": [],
                }
                if hasattr(self.bot, "autoEat"):
                    if hasattr(self.bot.autoEat, "options"):
                        self.bot.autoEat.options = eat_opts
                    elif hasattr(self.bot.autoEat, "setOpts"):
                        self.bot.autoEat.setOpts(eat_opts)
            except Exception as e:
                self.log(chalk.yellow(f"Auto-eat plugin warning: {e}"))

        if armor_manager and callable(armor_manager):
            try:
                self.bot.loadPlugin(armor_manager)
            except Exception as e:
                self.log(chalk.yellow(f"Armor manager plugin warning: {e}"))

        # Un seul serveur web pour toute la vie du process,
        # inutile de le relancer à chaque reconnexion.
        if web_inventory and not self.web_inventory_started:
            try:
                web_inventory(
                    self.bot,
                    {"port": self.web_inventory_port},
                )

                self.web_inventory_started = True

                self.log(
                    chalk.green(
                        f"Inventaire web : "
                        f"http://localhost:{self.web_inventory_port}"
                    )
                )

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Web inventory error: {e}"
                    )
                )

        if prismarine_viewer and not self.viewer_started:
            try:
                prismarine_viewer(
                    self.bot,
                    {"port": self.viewer_port, "firstPerson": True},
                )

                self.viewer_started = True

                self.log(
                    chalk.green(
                        f"Viewer 3D : "
                        f"http://localhost:{self.viewer_port}"
                    )
                )

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Viewer error: {e}"
                    )
                )

        self.start_events()


    # ========================================================
    # EVENTS
    # ========================================================

    def start_events(self):

        @On(self.bot, "login")
        def login():
            try:
                socket = self.bot._client.socket
                server = (
                    socket.server
                    if socket.server
                    else socket._host
                )

                self.log(
                    chalk.green(
                        f"Logged in to {server}"
                    )
                )

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Login error: {e}"
                    )
                )


        @On(self.bot, "spawn")
        def spawn():
            try:
                # Charger le plugin ne fait qu'équiper automatiquement
                # les nouveaux objets ramassés : il faut déclencher
                # explicitement une passe sur l'inventaire existant.
                if hasattr(self.bot, "armorManager"):
                    try:
                        self.bot.armorManager.equipAll()
                    except Exception as e:
                        self.log(
                            chalk.yellow(
                                f"Armor manager equipAll warning: {e}"
                            )
                        )

                # Seul le leader dit bonjour, pour éviter le spam
                # quand plusieurs bots de la flotte spawnent ensemble.
                if self.is_leader:
                    message = self.conversation.greeting()
                    self.chat(message)

                    self.log(
                        chalk.green(
                            f"LLM: {message}"
                        )
                    )

                if self.assigned_district:
                    def auto_patrol():
                        time.sleep(3)
                        self.log(
                            chalk.cyan(
                                f"Démarrage automatique de patrouille sur : "
                                f"{self.assigned_district}"
                            )
                        )
                        self.handle_patrol_command(self.assigned_district)

                    threading.Thread(
                        target=auto_patrol,
                        daemon=True,
                    ).start()

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Spawn error: {e}"
                    )
                )


        @On(self.bot, "kicked")
        def kicked(reason, loggedIn):
            if loggedIn:
                self.log(
                    chalk.redBright(
                        f"Kicked: {reason}"
                    )
                )


        @On(self.bot, "goal_reached")
        def goal_reached(_this, _goal):

            # ------------------------------------------------
            # PATROUILLE
            # ------------------------------------------------

            if self.patrol_active:

                generation = self.task_generation

                self.log(
                    chalk.green(
                        "✓ Point de patrouille atteint."
                    )
                )

                def continue_patrol():
                    if self.route_wait > 0:
                        time.sleep(self.route_wait)

                    if (
                        self.patrol_active
                        and self.task_valid(generation)
                    ):
                        self.run_patrol_route_step(generation)

                threading.Thread(
                    target=continue_patrol,
                    daemon=True,
                ).start()

                return

            # ------------------------------------------------
            # TÂCHE NORMALE
            # ------------------------------------------------

            messages = {
                "HOME": (
                    "✓ Tâche terminée : "
                    "je suis arrivé à la maison.",
                    "Je suis arrivé à la maison.",
                ),

                "POINT": (
                    "✓ Tâche terminée : "
                    "je suis arrivé à destination.",
                    "Je suis arrivé à destination.",
                ),

                "PLAYER": (
                    "✓ Tâche terminée : "
                    "je suis arrivé auprès du joueur.",
                    "Je suis arrivé !",
                ),
            }

            result = messages.get(self.mode)

            if result:
                log_message, chat_message = result

                self.log(
                    chalk.green(log_message)
                )

                self.chat(chat_message)

                self.mode = "IDLE"


        @On(self.bot, "messagestr")
        def messagestr(
            message,
            messagePosition,
            jsonMsg,
            sender,
            verified=None,
        ):

            if messagePosition != "chat":
                return

            text = message.strip()

            # Ce serveur formate le chat en "<joueur> message" au lieu
            # d'envoyer un UUID d'expéditeur fiable (sender est souvent
            # vide/incohérent) : on extrait le nom depuis le préfixe et
            # on s'en sert comme identité, avec sender en secours.
            player_name = None

            if text.startswith("<"):
                end = text.find(">")

                if end != -1:
                    player_name = text[1:end].strip()
                    text = text[end + 1:].strip()

            if player_name:
                if player_name.lower() == str(self.bot.username or "").lower():
                    return
            elif (
                self.bot.player
                and sender == self.bot.player.uuid
            ):
                return

            identity = player_name or sender

            self.log(
                chalk.yellow(
                    f"Chat: {text}"
                )
            )

            # ------------------------------------------------
            # ROUTAGE MULTI-BOTS (!all, !<nom_du_bot>)
            # ------------------------------------------------

            current_name = self.bot_name.lower()

            try:
                bot_user = (
                    str(self.bot.username).lower()
                    if self.bot.username
                    else current_name
                )
            except Exception:
                bot_user = current_name

            if text.startswith("!"):
                lower_text = text.lower()

                if lower_text.startswith("!all "):
                    text = text[5:].strip()
                elif lower_text.startswith(f"!{current_name} "):
                    text = text[len(current_name) + 2:].strip()
                elif lower_text.startswith(f"!{bot_user} "):
                    text = text[len(bot_user) + 2:].strip()
                else:
                    # Message ciblé pour un autre bot de la flotte -> ignorer
                    return

            # ------------------------------------------------
            # COME TO ME
            # ------------------------------------------------

            if text.lower() in (
                "viens",
                "viens ici",
                "viens me voir",
                "rejoins moi",
                "rejoins-moi",
                "come to me",
            ):

                found = (
                    self.find_player(player_name)
                    if player_name
                    else None
                )
                entity = found[1] if found else self.find_player_uuid(sender)

                if not entity:
                    self.chat(
                        "Je ne trouve pas ce joueur."
                    )
                    return

                pos = entity.position

                self.go_to_coords(
                    pos.x,
                    pos.y,
                    pos.z,
                    "PLAYER",
                    "J'arrive !",
                )

                return

            # ------------------------------------------------
            # COMMANDES
            # ------------------------------------------------

            self.handle_command(
                text,
                identity,
            )


        @On(self.bot, "end")
        def end(reason):

            self.log(
                chalk.red(
                    f"Disconnected: {reason}"
                )
            )

            if self.reconnect:
                self.log(
                    chalk.cyanBright(
                        "Reconnexion..."
                    )
                )

                time.sleep(2)
                self.start_bot()


# ============================================================
# START (point d'entrée pour un lancement direct ou en
# sous-processus supervisé par l'orchestrateur multi-bot)
# ============================================================

if __name__ == "__main__":
    _bot_name = os.getenv("BOT_NAME", "Moisurunautrecom")
    _enable_stdin_repl = (
        os.getenv("ENABLE_STDIN_REPL", "true").lower() in ("true", "1", "yes")
    )

    MCBot(
        _bot_name,
        enable_console=_enable_stdin_repl,
        pipe_mode=not _enable_stdin_repl,
    )
