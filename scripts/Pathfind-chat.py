from javascript import require, On, off
from simple_chalk import chalk
from eliza import eliza
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
import os
import sys
import time
import threading


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
except Exception:
    auto_eat = None

try:
    web_inventory = require("mineflayer-web-inventory")
except Exception:
    web_inventory = None

vec3 = require("vec3")


# ============================================================
# CONFIG
# ============================================================

SERVER_HOST = os.getenv("SERVER_HOST", "game02.octoheberg.fr")
SERVER_PORT = int(os.getenv("SERVER_PORT", "25571"))

# Sélection dynamique du bot si non imposé par l'environnement
if "BOT_NAME" not in os.environ and sys.stdin and sys.stdin.isatty():
    try:
        from utils.bot_selector import select_bots
    except ImportError:
        from scripts.utils.bot_selector import select_bots

    _chosen = select_bots()
    if len(_chosen) > 1:
        try:
            from scripts.orchestrator import BotManager
        except ImportError:
            from orchestrator import BotManager

        _mgr = BotManager(fleet_config=_chosen)
        _mgr.start_fleet()
        _mgr.terminal_loop()
        sys.exit(0)
    elif _chosen:
        BOT_NAME = _chosen[0]["name"]
        WEB_INVENTORY_PORT = _chosen[0].get("port", 3000)
        BOT_ROLE = _chosen[0].get("role", "leader")
    else:
        BOT_NAME = "Moisurunautrecom"
        WEB_INVENTORY_PORT = int(os.getenv("WEB_INVENTORY_PORT", "3000"))
        BOT_ROLE = os.getenv("BOT_ROLE", "leader").lower()
else:
    BOT_NAME = os.getenv("BOT_NAME", "Moisurunautrecom")
    WEB_INVENTORY_PORT = int(os.getenv("WEB_INVENTORY_PORT", "3000"))
    BOT_ROLE = os.getenv("BOT_ROLE", "leader").lower()

RECONNECT = os.getenv("RECONNECT", "true").lower() in ("true", "1", "yes")
IS_LEADER = (BOT_ROLE == "leader")
ENABLE_STDIN_REPL = (
    os.getenv("ENABLE_STDIN_REPL", "true").lower() in ("true", "1", "yes")
)
ASSIGNED_DISTRICT = os.getenv("ASSIGNED_DISTRICT", "")

# Authentification Microsoft & Jetons 2FA
AUTH_TOKENS_DIR = os.getenv("AUTH_TOKENS_DIR", "./tokens")
AUTO_OPEN_BROWSER = (
    os.getenv("AUTO_OPEN_BROWSER", "true").lower() in ("true", "1", "yes")
)
MICROSOFT_TOTP_SECRET = os.getenv("MICROSOFT_TOTP_SECRET", "")
MICROSOFT_EMAIL = os.getenv("MICROSOFT_EMAIL", "")
MICROSOFT_PASSWORD = os.getenv("MICROSOFT_PASSWORD", "")
ENABLE_HEADLESS_AUTH = (
    os.getenv("ENABLE_HEADLESS_AUTH", "false").lower() in ("true", "1", "yes")
)

# Maison : indépendante des autres destinations
HOME = {
    "x": 1802,
    "y": 130,
    "z": -1328,
}

PATROL_WAIT = 5

POINTS_INTERET = {
    "usine a fer": (1690, 132, -1145),
    "usine à fer": (1690, 132, -1145),

    "salle des coffres": (1776, 119, -1144),
    "route 1": (1693, 96, -1209),
    "route 2": (1717, 111, -1163),
    "route 3": (1722, 122, -1128),
    "route 4": (1721, 131, -1101),
    "arc de triomphe": (1683, 96, -1273),

    "george orwell": (1697, 96, -1323),
    "place gauche": (1608, 95, -1236),
    "place haute": (1551, 95, -1271),
    "place droite": (1629, 95, -1311),
    "parc": (1621, 95, -1272),

    "palace": (1707, 97, -1374),
    "palais": (1634, 95, -1481),
    "theatre": (1714, 95, -1466),
    "théâtre": (1714, 95, -1466),

    "horloge": (1746, 95, -1418),
    "river": (1796, 191, -1449),
    "intersection 1": (1796, 104, -1419),
    "church": (1822, 112, -1413),
    "intersection 2": (1820, 119, -1388),
    "bourdieu-cathedral": (1820, 119, -1388),

    "cathedral": (1776, 129, -1328),
    "cathedrale": (1776, 129, -1328),
}

QUARTIERS = {
    "Haute ville": ["usine a fer", "route 1", "route 2", "route 3", "route 4", "salle des coffres", "arc de triomphe"],
    "place george orwell": ["george orwell", "place gauche", "place haute", "place droite", "parc"],
    "quartier du theatre": ["theatre", "palace", "palais"],
    "quartier pierre bourdieu": ["horloge", "intersection 1", "river", "church", "intersection 2"],
    "quartier de la cathedrale": ["cathedral", "droite", "parvis", "gauche"],
}

# =========================
# Graphe des routes entre points
# =========================

GRAPH = {
    "usine a fer": ["route 4"],
    "route 4": ["usine a fer", "route 3"],
    "route 3": ["route 4", "route 2"],
    "route 2": ["route 3", "route 1", "salle des coffres"],
    "salle des coffres": ["route 2"],

    "route 1": ["route 2", "arc de triomphe"],

    "arc de triomphe": ["route 1", "george orwell"],

    "george orwell": ["arc de triomphe", "horloge", "place gauche", "place droite", "parc", "palace"],
    "place gauche": ["george orwell", "place haute", "parc"],
    "place haute": ["place gauche", "place droite", "parc"],
    "place droite": ["place haute", "george orwell", "parc"],
    "parc": ["george orwell", "place gauche", "place haute", "place droite"],

    "horloge": ["george orwell", "theatre", "intersection 1"],
    "theatre": ["horloge", "palace", "palais"],

    "intersection 1": ["horloge", "church", "river"],
    "river": ["intersection 1"],

    "church": ["intersection 1", "intersection 2"],
    "intersection 2": ["church", "cathedral"],
    "cathedral": ["intersection 2"],
}

# ============================================================
# ELIZA
# ============================================================

eliza_bot = eliza.Eliza()
eliza_bot.load(
    os.path.join(
        os.path.dirname(__file__),
        "eliza",
        "doctor.txt",
    )
)


# ============================================================
# BOT
# ============================================================

class MCBot:

    def __init__(self, name):
        self.bot_name = name
        self.reconnect = RECONNECT
        self.mode = "IDLE"
        self.patrol_active = False
        self.patrol_route = []
        self.patrol_index = 0
        self.patrol_label = None
        self.route_loop = False
        self.route_wait = 0
        self.web_inventory_started = False
        self.task_generation = 0

        # Gestion des jetons et double authentification (2FA) isolée par bot
        creds = get_bot_credentials(name)
        self.token_manager = TokenManager(
            bot_name=name,
            base_dir=AUTH_TOKENS_DIR,
        )
        self.totp_manager = TOTPManager(
            secret=creds["totp_secret"],
        )
        self.mfa_handler = MfaDeviceCodeHandler(
            bot_name=name,
            totp_manager=self.totp_manager,
            auto_open_browser=AUTO_OPEN_BROWSER,
            logger=self.log,
            headless_email=creds["email"],
            headless_password=creds["password"],
            enable_headless=ENABLE_HEADLESS_AUTH,
        )

        self.bot_args = {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "username": name,
            "auth": "microsoft",
            "version": "1.21.11",
            "hideErrors": False,
            "profilesFolder": self.token_manager.get_profile_path(),
            "onMsaCode": self.mfa_handler.on_msa_code,
        }

        # Rapport initial sur les jetons
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
                    f"Aucun jeton en cache dans {self.token_manager.get_profile_path()}. "
                    f"Authentification 2FA requise au démarrage."
                )
            )

        self.start_bot()

        if ENABLE_STDIN_REPL:
            threading.Thread(
                target=self.terminal_loop,
                daemon=True,
            ).start()
        else:
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

        print(f"[{name}] {message}")


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


    def cancel_task(self):
        self.task_generation += 1
        self.patrol_active = False
        self.patrol_route = []
        self.patrol_index = 0
        self.patrol_label = None
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

        self.patrol_active = False
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
    # PLAYERS
    # ========================================================

    def find_player(self, name):
        name = name.strip().lower()

        try:
            for player_name, data in self.bot.players.items():

                if player_name.lower() == name:
                    if data.entity:
                        return player_name, data.entity

        except Exception as e:
            self.log(
                chalk.red(
                    f"Player search error: {e}"
                )
            )

        return None


    def find_player_uuid(self, uuid):
        try:
            for name, data in self.bot.players.items():
                if data.uuid == uuid and data.entity:
                    return data.entity

        except Exception:
            pass

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
    # PATROL
    #
    # La patrouille suit un itinéraire précalculé qui ne se
    # déplace que le long des arêtes de GRAPH (aucun saut
    # arbitraire) : soit sur tout le graphe (toute la ville),
    # soit restreint aux points d'un quartier. mineflayer-
    # pathfinder calcule ensuite le vrai chemin entre deux
    # points consécutifs de cet itinéraire.
    # ========================================================

    def find_quartier(self, name):
        name = name.strip().lower()

        for quartier_name in QUARTIERS:
            if quartier_name.lower() == name:
                return quartier_name

        return None


    def quartier_points_valides(self, quartier_name):
        return [
            point
            for point in QUARTIERS.get(quartier_name, [])
            if point in POINTS_INTERET
        ]


    def all_graph_points(self):
        return [
            point
            for point in GRAPH
            if point in POINTS_INTERET
        ]


    def get_bot_position(self):
        try:
            pos = self.bot.entity.position
            return (pos.x, pos.y, pos.z)
        except Exception:
            return None


    def nearest_point(self, allowed_points, position):
        if position is None:
            return None

        px, _, pz = position

        nearest = None
        nearest_dist = None

        for point in allowed_points:
            if point not in POINTS_INTERET:
                continue

            x, _, z = POINTS_INTERET[point]
            dist = (x - px) ** 2 + (z - pz) ** 2

            if nearest_dist is None or dist < nearest_dist:
                nearest = point
                nearest_dist = dist

        return nearest


    def build_patrol_route(self, allowed_points, start_point=None):
        allowed = [
            point
            for point in allowed_points
            if point in POINTS_INTERET
        ]

        if not allowed:
            return []

        allowed_set = set(allowed)

        if start_point not in allowed_set:
            start_point = allowed[0]

        visited = set()
        route = []

        def visit(node):
            visited.add(node)
            route.append(node)

            for neighbor in GRAPH.get(node, []):
                if (
                    neighbor in allowed_set
                    and neighbor not in visited
                ):
                    visit(neighbor)
                    # revient sur node : toujours une arête valide
                    route.append(node)

        visit(start_point)

        return route


    def start_patrol_route(self, allowed_points, label):
        if self.patrol_active:
            self.chat("Je patrouille déjà.")
            return False

        start_point = self.nearest_point(
            allowed_points,
            self.get_bot_position(),
        )

        route = self.build_patrol_route(allowed_points, start_point)

        if len(route) < 2:
            self.log(
                chalk.red(
                    f"Pas assez de points pour patrouiller : {label}"
                )
            )
            self.chat("Je n'ai pas assez de points pour patrouiller ici.")
            return False

        self.task_generation += 1
        generation = self.task_generation

        self.mode = "PATROL_ROUTE"
        self.patrol_active = True
        self.patrol_route = route
        self.patrol_index = 0
        self.patrol_label = label
        self.route_loop = True
        self.route_wait = PATROL_WAIT
        self.stop_movement()

        self.chat(f"Je patrouille : {label}.")

        self.log(
            chalk.cyan(
                f"Patrouille activée ({len(route)} étapes) : {label}"
            )
        )

        self.goto_patrol_index(generation)

        return True


    # ========================================================
    # ALLER QUELQUE PART EN SUIVANT LE GRAPHE
    #
    # chemin <point> : trajet ponctuel (pas de boucle), calcule
    # le plus court chemin dans GRAPH entre le point du graphe
    # le plus proche du bot et la destination, puis enchaîne
    # les points un par un.
    # ========================================================

    def shortest_graph_path(self, start, target):
        if start is None or target is None:
            return None

        if start == target:
            return [start]

        came_from = {start: None}
        queue = [start]

        while queue:
            node = queue.pop(0)

            if node == target:
                break

            for neighbor in GRAPH.get(node, []):
                if neighbor not in came_from:
                    came_from[neighbor] = node
                    queue.append(neighbor)

        if target not in came_from:
            return None

        path = []
        node = target

        while node is not None:
            path.append(node)
            node = came_from[node]

        path.reverse()

        return path


    def go_via_graph(self, destination):
        destination = destination.strip().lower()

        if not destination:
            self.log(
                chalk.yellow("Destination manquante.")
            )
            self.chat("Où veux-tu que j'aille via le graphe ?")
            return False

        if destination not in POINTS_INTERET or destination not in GRAPH:
            self.log(
                chalk.red(
                    f"Point inconnu du graphe : {destination}"
                )
            )
            self.chat("Je ne connais pas ce point dans mon graphe.")
            return False

        if self.patrol_active:
            self.chat("Je suis déjà en mouvement, tape 'stop' d'abord.")
            return False

        start_point = self.nearest_point(
            self.all_graph_points(),
            self.get_bot_position(),
        )

        path = self.shortest_graph_path(start_point, destination)

        if not path:
            self.log(
                chalk.red(
                    f"Aucun chemin trouvé vers {destination}."
                )
            )
            self.chat("Je ne trouve pas de chemin vers ce point.")
            return False

        self.task_generation += 1
        generation = self.task_generation

        self.mode = "PATROL_ROUTE"
        self.patrol_active = True
        self.patrol_route = path
        self.patrol_index = 0
        self.patrol_label = destination
        self.route_loop = False
        self.route_wait = 0
        self.stop_movement()

        self.chat(f"Je rejoins {destination} en suivant le graphe.")

        self.log(
            chalk.cyan(
                f"Trajet via le graphe ({len(path)} étapes) → {destination}"
            )
        )

        self.goto_patrol_index(generation)

        return True


    def handle_patrol_command(self, arg):
        arg = arg.strip().lower()

        if arg in ("", "ville", "toute la ville", "ville entiere", "ville entière"):
            return self.start_patrol_route(
                self.all_graph_points(),
                "toute la ville",
            )

        matched = self.find_quartier(arg)

        if not matched:
            self.log(
                chalk.red(f"Quartier inconnu : {arg}")
            )
            print(
                chalk.gray(
                    "Quartiers disponibles : "
                    + ", ".join(QUARTIERS.keys())
                )
            )
            self.chat("Je ne connais pas ce quartier.")
            return False

        return self.start_patrol_route(
            self.quartier_points_valides(matched),
            matched,
        )


    def goto_patrol_index(self, generation=None):
        if not self.patrol_active or not self.patrol_route:
            return

        if (
            generation is not None
            and not self.task_valid(generation)
        ):
            return

        point = self.patrol_route[self.patrol_index]
        x, y, z = POINTS_INTERET[point]
        target = vec3(x, y, z)

        self.log(
            chalk.magenta(
                f"Patrouille [{self.patrol_label}] → "
                f"{point} : {vec3_to_str(target)}"
            )
        )

        self.pathfind(target)


    def run_patrol_route_step(self, generation=None):
        if not self.patrol_active or not self.patrol_route:
            return

        if (
            generation is not None
            and not self.task_valid(generation)
        ):
            return

        if self.patrol_index >= len(self.patrol_route) - 1:
            if self.route_loop:
                self.patrol_index = 0
            else:
                self.log(
                    chalk.green(
                        f"✓ Arrivé à destination via le graphe : "
                        f"{self.patrol_label}"
                    )
                )
                self.chat(f"Je suis arrivé à {self.patrol_label} !")
                self.cancel_task()
                return
        else:
            self.patrol_index += 1

        self.goto_patrol_index(generation)


    # ========================================================
    # PLAYERS LIST
    # ========================================================

    def list_players(self):
        print()

        for name, data in self.bot.players.items():
            if data.entity:
                print(
                    f"  - {name} "
                    f"{vec3_to_str(data.entity.position)}"
                )
            else:
                print(
                    f"  - {name} (position inconnue)"
                )

        print()


    # ========================================================
    # COMMAND HANDLER
    #
    # Utilisé par le TERMINAL et le CHAT.
    # ========================================================

    def handle_command(self, command, sender=None):
        command = command.strip()

        if not command:
            return True

        lower = command.lower()

        # ----------------------------------------------------
        # QUIT
        # ----------------------------------------------------

        if lower == "quit":
            self.reconnect = False
            self.cancel_task()
            self.chat(eliza_bot.final())

            try:
                self.bot.quit()
            except Exception:
                pass

            return False

        # ----------------------------------------------------
        # STOP
        # ----------------------------------------------------

        if lower == "stop":
            self.cancel_task()
            self.chat("D'accord, j'arrête.")
            self.log(
                chalk.yellow("✓ Tâche arrêtée.")
            )
            return True

        # ----------------------------------------------------
        # AUTHENTIFICATION & JETONS 2FA
        # ----------------------------------------------------

        if lower in ("auth", "auth status", "statut auth"):
            summary = self.token_manager.get_token_summary()
            print()
            print(chalk.cyan("=" * 60))
            print(chalk.cyanBright(" ÉTAT DE L'AUTHENTIFICATION & DES JETONS (2FA)"))
            print(chalk.cyan("=" * 60))
            print(f"  Bot : {summary['bot_name']}")
            print(f"  Dossier profil : {summary['profile_dir']}")
            token_status = (
                chalk.green(f"Oui ({summary['file_count']} fichier(s))")
                if summary["has_tokens"]
                else chalk.yellow("Non (première authentification requise)")
            )
            print(f"  Jetons en cache : {token_status}")
            if summary["files"]:
                print(f"  Fichiers : {', '.join(summary['files'])}")
            print(f"  Dernière mise à jour : {summary['last_modified']}")
            if summary["account_hint"]:
                print(f"  Compte associé : {chalk.magenta(summary['account_hint'])}")
            print(f"  Jeton 2FA TOTP : {self.totp_manager.format_status()}")
            print(chalk.cyan("=" * 60))
            print()
            return True

        if lower in ("auth totp", "totp"):
            if not self.totp_manager.is_configured():
                print()
                print(
                    chalk.yellow(
                        "Aucune clé secrète TOTP configurée (définir MICROSOFT_TOTP_SECRET)."
                    )
                )
                print()
            else:
                code, remaining = self.totp_manager.generate_code()
                color = chalk.green if remaining > 10 else chalk.yellow
                print()
                print(
                    chalk.green("✓ Jeton TOTP 2FA actuel : ")
                    + chalk.cyanBright(code)
                    + " "
                    + color(f"({remaining}s restantes)")
                )
                print()
            return True

        if lower in ("auth clear", "clear tokens", "reset auth"):
            deleted = self.token_manager.clear_tokens()
            self.log(
                chalk.yellow(
                    f"✓ {deleted} fichier(s) de jetons supprimé(s). "
                    f"Une nouvelle validation 2FA sera effectuée à la prochaine connexion."
                )
            )
            return True

        # ----------------------------------------------------
        # HELP / AIDE
        # ----------------------------------------------------

        if lower in ("help", "aide"):
            print()
            print(chalk.cyan("=" * 60))
            print(chalk.cyanBright(" COMMANDES DISPONIBLES"))
            print(chalk.cyan("=" * 60))
            print("  - go <destination> / va à <lieu> : Se déplacer vers un point d'intérêt")
            print("  - home / maison : Rentrer au point d'apparition HOME")
            print("  - patrouille [quartier] : Démarrer une patrouille en boucle sur le graphe")
            print("  - chemin <lieu> / route <lieu> : Trajet ponctuel via le graphe")
            print("  - quartiers : Lister les quartiers urbains disponibles")
            print("  - players / joueurs : Lister les joueurs connectés et leurs positions")
            print("  - auth status : Consulter l'état des jetons de session et du 2FA")
            print("  - auth totp : Afficher le jeton TOTP 2FA actuel et le temps restant")
            print("  - auth clear : Réinitialiser les jetons en cache (forcer un nouveau 2FA)")
            print("  - stop : Stopper immédiatement la tâche en cours")
            print("  - quit : Déconnecter le bot et quitter le programme")
            print(chalk.cyan("=" * 60))
            print()
            return True

        # ----------------------------------------------------
        # PATROL
        # ----------------------------------------------------

        if lower in (
            "patrouille",
            "patrol",
            "patrouiller",
        ):
            self.handle_patrol_command("")
            return True

        if lower.startswith("patrouille "):
            self.handle_patrol_command(
                command[len("patrouille "):]
            )
            return True

        if lower.startswith("patrol "):
            self.handle_patrol_command(
                command[len("patrol "):]
            )
            return True

        # ----------------------------------------------------
        # ALLER QUELQUE PART VIA LE GRAPHE (trajet ponctuel)
        # ----------------------------------------------------

        if lower.startswith("chemin "):
            self.go_via_graph(
                command[len("chemin "):]
            )
            return True

        if lower.startswith("route "):
            self.go_via_graph(
                command[len("route "):]
            )
            return True

        # ----------------------------------------------------
        # QUARTIERS
        # ----------------------------------------------------

        if lower in ("quartiers", "quartier"):
            print()
            print(chalk.cyan("Quartiers disponibles :"))

            for quartier_name in QUARTIERS:
                print(f"  - {quartier_name}")

            print()
            return True

        # ----------------------------------------------------
        # HOME
        #
        # home = alias de go home
        # ----------------------------------------------------

        if lower in ("home", "maison"):
            self.go_to_destination("home")
            return True

        # ----------------------------------------------------
        # PLAYERS
        # ----------------------------------------------------

        if lower in ("players", "joueurs"):
            self.list_players()
            return True

        # ----------------------------------------------------
        # SAY
        # ----------------------------------------------------

        if lower.startswith("say "):
            message = command[4:].strip()
            self.chat(message)
            self.log(
                chalk.cyan(f"Chat: {message}")
            )
            return True

        # ----------------------------------------------------
        # GO
        # ----------------------------------------------------

        if lower == "go":
            self.chat("Où veux-tu que j'aille ?")

            print()
            print(chalk.cyan("Destinations disponibles :"))
            print("  - home")

            for point_name in sorted(POINTS_INTERET):
                print(f"  - {point_name}")

            print(
                chalk.gray(
                    "Tape 'players' pour voir les joueurs visibles."
                )
            )
            print()

            return True

        if lower.startswith("go "):
            self.go_to_destination(
                command[3:].strip()
            )
            return True

        # ----------------------------------------------------
        # COMMANDES FRANÇAISES
        # ----------------------------------------------------

        prefixes = (
            "va à ",
            "va a ",
            "va au ",
            "va aux ",
            "va à la ",
            "va a la ",
            "va à l'",
            "va a l'",
            "aller à ",
            "aller a ",
        )

        for prefix in prefixes:
            if lower.startswith(prefix):
                self.go_to_destination(
                    command[len(prefix):].strip()
                )
                return True

        # ----------------------------------------------------
        # ELIZA
        # ----------------------------------------------------

        # Seul le bot leader répond avec ELIZA dans le chat in-game
        if not IS_LEADER and sender is not None:
            return True

        try:
            response = eliza_bot.respond(command)

            if response:
                self.chat(response)
                self.log(
                    chalk.cyan(
                        f"ELIZA: {response}"
                    )
                )

        except Exception as e:
            self.log(
                chalk.red(
                    f"ELIZA error: {e}"
                )
            )

        return True


    # ========================================================
    # TERMINAL
    # ========================================================

    def terminal_loop(self):
        time.sleep(1)

        print(
            chalk.green(
                "\n========== CONSOLE BOT =========="
            )
        )

        print(
            chalk.gray(
                "help | go <destination> | home | "
                "players | patrouille | stop | say | quit"
            )
        )

        while True:
            try:
                command = input("> ").strip()

                if command.lower() == "help":
                    print(
                        "\n"
                        "  go <destination>      → lieu ou joueur\n"
                        "  go home               → maison\n"
                        "  home                  → maison\n"
                        "  players               → joueurs visibles\n"
                        "  patrouille            → patrouiller toute la ville\n"
                        "  patrouille <quartier> → patrouiller un quartier\n"
                        "  chemin <point>        → rejoindre un point via le graphe\n"
                        "  quartiers             → lister les quartiers\n"
                        "  stop                  → arrêter la tâche\n"
                        "  say <message>         → parler\n"
                        "  quit                  → quitter\n"
                    )
                    continue

                if not self.handle_command(command):
                    break

            except (EOFError, KeyboardInterrupt):
                print()
                self.reconnect = False
                self.cancel_task()

                try:
                    self.bot.quit()
                except Exception:
                    pass

                break

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Terminal error: {e}"
                    )
                )


    def pipe_listener_loop(self):
        """Écoute stdin en continu lorsque le bot est supervisé par un orchestrateur."""
        import sys
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                command = line.strip()
                if command:
                    self.handle_command(command)
            except Exception:
                break


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

        # Un seul serveur web pour toute la vie du process,
        # inutile de le relancer à chaque reconnexion.
        if web_inventory and not self.web_inventory_started:
            try:
                web_inventory(
                    self.bot,
                    {"port": WEB_INVENTORY_PORT},
                )

                self.web_inventory_started = True

                self.log(
                    chalk.green(
                        f"Inventaire web : "
                        f"http://localhost:{WEB_INVENTORY_PORT}"
                    )
                )

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Web inventory error: {e}"
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
                # Seul le bot leader engage la conversation ELIZA pour éviter le spam
                if IS_LEADER:
                    message = eliza_bot.initial()
                    self.chat(message)

                    self.log(
                        chalk.green(
                            f"ELIZA (Leader): {message}"
                        )
                    )

                # Démarrage automatique de la patrouille si un quartier est assigné
                if ASSIGNED_DISTRICT:
                    def auto_patrol():
                        time.sleep(3)
                        self.log(
                            chalk.cyan(
                                f"Démarrage automatique de patrouille sur : {ASSIGNED_DISTRICT}"
                            )
                        )
                        self.handle_patrol_command(ASSIGNED_DISTRICT)

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
        def kicked(reason=None, loggedIn=None, *args):
            try:
                if loggedIn:
                    self.log(
                        chalk.redBright(
                            f"Kicked: {reason}"
                        )
                    )
            except Exception as e:
                self.log(
                    chalk.red(
                        f"Kicked error: {e}"
                    )
                )


        @On(self.bot, "goal_reached")
        def goal_reached(*args, **kwargs):
            try:
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

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Goal reached error: {e}"
                    )
                )


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

            if (
                self.bot.player
                and sender == self.bot.player.uuid
            ):
                return

            text = message.strip()

            # Retire <joueur>
            if text.startswith("<"):
                end = text.find(">")

                if end != -1:
                    text = text[end + 1:].strip()

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
                    self.bot.username.lower()
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

                entity = self.find_player_uuid(sender)

                if not entity:
                    self.chat(
                        "Je ne trouve pas ce joueur."
                    )
                    return

                pos = entity.position

                self.go_to_coords(
                    pos.x,
                    pos.y + 1,
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
                sender,
            )


        @On(self.bot, "end")
        def end(reason=None, *args):
            try:
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
            except Exception as e:
                self.log(
                    chalk.red(
                        f"End event error: {e}"
                    )
                )


# ============================================================
# START
# ============================================================

bot = MCBot(BOT_NAME)

