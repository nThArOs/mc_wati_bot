from javascript import require, On, off
from simple_chalk import chalk
from eliza import eliza
from utils.vec3_conversion import vec3_to_str
import os
import time
import random
import threading


# ============================================================
# LIBRARIES
# ============================================================

mineflayer = require("mineflayer")
pathfinder_lib = require("mineflayer-pathfinder")
auto_eat = require("mineflayer-auto-eat").default
vec3 = require("vec3")


# ============================================================
# CONFIG
# ============================================================

SERVER_HOST = "game02.octoheberg.fr"
SERVER_PORT = 25571
BOT_NAME = "pathfinder-bot"
RECONNECT = True

# Maison : indépendante des autres destinations
HOME = {
    "x": 1802,
    "y": 130,
    "z": -1328,
}

PATROL_RADIUS = 16
PATROL_WAIT = 5

POINTS_INTERET = {
    "usine a fer": (1690, 132, -1145),
    "usine à fer": (1690, 132, -1145),
    
    "salle des coffres": (1792, 102, -1158),
    
    "arc de triomphe": (1683, 96, -1273),
    
    "george orwell": (1697, 96, -1323),
    "place gauche": (1608, 95, -1236),
    "place haute": (1551, 95, -1271),
    "place droite": (1629, 95, -1311),
    "parc": (1629, 95, -1311),
    
    "palace": (1707, 97, -1374),
    "palais": (1634, 95, -1481),
    "theatre": (1714, 95, -1466),
    "théâtre": (1714, 95, -1466),

   
    
    "horloge": (1746, 95, -1418),
    "river": (1787, 119, -1381),
    "intersection 1": (1796, 104, -1419),
    "church": (1822, 112, -1413),
    "intersection 2": (1820, 119, -1388),
    "bourdieu-cathedral": (1820, 119, -1388),
    
    "cathedral": (1776, 129, -1328),
    "cathedrale": (1776, 129, -1328),
}

QUARTIERS = {
    "Haute ville": ["usine a fer", "salle des coffres", "arc de triomphe"],
    "place george orwell": ["george orwell", "place gauche", "place haute", "place droite", "parc"],
    "quartier du theatre": ["theatre","palace","palais"],
    "quartier pierre bourdieu": ["horloge", "intersection 1","river", "church", "intersection 2"],
    "quartier de la cathedrale": ["cathedral", "droite","parvis","gauche"],
}

# =========================
# Graphe des routes entre points
# =========================

GRAPH = {
    "usine a fer": ["salle des coffres","arc de triomphe"],
    "salle des coffres": ["usine a fer", "arc de triomphe"],
    "arc de triomphe": ["usine a fer","salle des coffres", "george orwell"],

    "george orwell": ["arc de triomphe", "horloge", "place gauche", "place droite", "parc","palace"],
    "place gauche": ["george orwell", "place haute", "parc"],
    "place haute": ["place gauche", "place droite", "parc"],
    "place droite": ["place haute", "george orwell", "parc"],
    "parc": ["george orwell", "place gauche", "place haute", "place droite"],

    "horloge": ["george orwell", "theatre", "intersection 1"],
    "theatre": ["horloge","palace","palais"],

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
        self.patrol_quartier = None
        self.patrol_current_point = None
        self.task_generation = 0

        self.bot_args = {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "username": name,
            "auth": "microsoft",
            "version": "1.21.11",
            "hideErrors": False,
        }

        self.start_bot()

        threading.Thread(
            target=self.terminal_loop,
            daemon=True,
        ).start()


    # ========================================================
    # UTILITIES
    # ========================================================

    def log(self, message):
        try:
            name = self.bot.username
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
        self.patrol_quartier = None
        self.patrol_current_point = None
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
    # ========================================================

    def random_patrol_position(self):
        return vec3(
            HOME["x"] + random.randint(
                -PATROL_RADIUS,
                PATROL_RADIUS,
            ),
            HOME["y"],
            HOME["z"] + random.randint(
                -PATROL_RADIUS,
                PATROL_RADIUS,
            ),
        )


    def start_patrol(self):
        if self.patrol_active:
            self.chat("Je patrouille déjà.")
            return

        self.task_generation += 1
        generation = self.task_generation

        self.mode = "PATROL"
        self.patrol_active = True
        self.stop_movement()

        self.chat(
            f"Je commence ma patrouille "
            f"dans un rayon de {PATROL_RADIUS} blocs."
        )

        self.run_patrol_step(generation)


    def run_patrol_step(self, generation=None):
        if not self.patrol_active:
            return

        if (
            generation is not None
            and not self.task_valid(generation)
        ):
            return

        target = self.random_patrol_position()

        self.log(
            chalk.magenta(
                f"Patrouille → {vec3_to_str(target)}"
            )
        )

        self.pathfind(target)


    # ========================================================
    # PATROL PAR QUARTIER
    #
    # Se déplace de point en point à l'intérieur d'un quartier
    # en suivant GRAPH. mineflayer-pathfinder calcule le vrai
    # chemin, GRAPH sert seulement à choisir le prochain point.
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


    def next_quartier_point(self, quartier_name, current_point):
        valid_points = self.quartier_points_valides(quartier_name)

        neighbors = GRAPH.get(current_point, [])

        candidates = [
            point
            for point in neighbors
            if point in valid_points
        ]

        if not candidates:
            candidates = [
                point
                for point in valid_points
                if point != current_point
            ]

        if not candidates:
            return None

        return random.choice(candidates)


    def start_quartier_patrol(self, quartier_name):
        if self.patrol_active:
            self.chat("Je patrouille déjà.")
            return False

        matched = self.find_quartier(quartier_name)

        if not matched:
            self.log(
                chalk.red(
                    f"Quartier inconnu : {quartier_name}"
                )
            )
            self.chat("Je ne connais pas ce quartier.")
            return False

        valid_points = self.quartier_points_valides(matched)

        if not valid_points:
            self.log(
                chalk.red(
                    f"Aucun point connu dans le quartier : {matched}"
                )
            )
            self.chat("Ce quartier n'a aucun point que je connais.")
            return False

        self.task_generation += 1
        generation = self.task_generation

        self.mode = "PATROL_QUARTIER"
        self.patrol_active = True
        self.patrol_quartier = matched
        self.patrol_current_point = valid_points[0]
        self.stop_movement()

        self.chat(
            f"Je patrouille dans {matched}."
        )

        self.log(
            chalk.cyan(
                f"Patrouille de quartier activée : {matched}"
            )
        )

        self.run_quartier_patrol_step(generation)

        return True


    def run_quartier_patrol_step(self, generation=None):
        if not self.patrol_active:
            return

        if not self.patrol_quartier:
            return

        if (
            generation is not None
            and not self.task_valid(generation)
        ):
            return

        next_point = self.next_quartier_point(
            self.patrol_quartier,
            self.patrol_current_point,
        )

        if not next_point:
            self.log(
                chalk.red(
                    f"Plus aucun point à visiter dans "
                    f"{self.patrol_quartier}."
                )
            )
            self.cancel_task()
            return

        self.patrol_current_point = next_point

        x, y, z = POINTS_INTERET[next_point]
        target = vec3(x, y, z)

        self.log(
            chalk.magenta(
                f"Patrouille [{self.patrol_quartier}] → "
                f"{next_point} : {vec3_to_str(target)}"
            )
        )

        self.pathfind(target)


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
        # PATROL
        # ----------------------------------------------------

        if lower in (
            "patrouille",
            "patrol",
            "patrouiller",
        ):
            self.start_patrol()
            return True

        # ----------------------------------------------------
        # PATROL PAR QUARTIER
        # ----------------------------------------------------

        if lower.startswith("patrouille "):
            self.start_quartier_patrol(
                command[len("patrouille "):].strip()
            )
            return True

        if lower.startswith("patrol "):
            self.start_quartier_patrol(
                command[len("patrol "):].strip()
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
                        "  patrouille            → lancer patrouille\n"
                        "  patrouille <quartier> → patrouiller un quartier\n"
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

        self.bot.loadPlugin(auto_eat)

        self.bot.autoEat.options = {
            "priority": "foodPoints",
            "startAt": 14,
            "bannedFood": [],
        }

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
                message = eliza_bot.initial()
                self.chat(message)

                self.log(
                    chalk.green(
                        f"ELIZA: {message}"
                    )
                )

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
                    time.sleep(PATROL_WAIT)

                    if (
                        self.patrol_active
                        and self.task_valid(generation)
                    ):
                        if self.mode == "PATROL_QUARTIER":
                            self.run_quartier_patrol_step(
                                generation
                            )
                        else:
                            self.run_patrol_step(
                                generation
                            )

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
# START
# ============================================================

bot = MCBot(BOT_NAME)