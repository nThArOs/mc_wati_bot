from javascript import require, On, off
from simple_chalk import chalk
from eliza import eliza
from utils.vec3_conversion import vec3_to_str
import os
import time
import random
import threading


# ============================================================
# IMPORT JAVASCRIPT LIBRARIES
# ============================================================

mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")
mineflayer_auto_eat = require("mineflayer-auto-eat").default
vec3 = require("vec3")


# ============================================================
# SERVER CONFIGURATION
# ============================================================

server_host = "game02.octoheberg.fr"
server_port = 25571

reconnect = True


# ============================================================
# HOME / PATROL CONFIGURATION
# ============================================================

HOME = {
    "x": 1802,
    "y": 130,
    "z": -1328,
}

PATROL_RADIUS = 16
PATROL_WAIT_SECONDS = 5


# ============================================================
# POINTS D'INTERET
# ============================================================

POINTS_INTERET = {

    # --------------------------------------------------------
    # Cathédrale
    # --------------------------------------------------------

    "cathedral": {
        "x": 1776,
        "y": 129,
        "z": -1328,
    },

    "cathedrale": {
        "x": 1776,
        "y": 129,
        "z": -1328,
    },

    "cathderal": {
        "x": 1776,
        "y": 129,
        "z": -1328,
    },

    "cathédrale": {
        "x": 1776,
        "y": 129,
        "z": -1328,
    },

    # --------------------------------------------------------
    # George Orwell
    # --------------------------------------------------------

    "george orwell": {
        "x": 1697,
        "y": 96,
        "z": -1323,
    },

    # --------------------------------------------------------
    # Arc de Triomphe
    # --------------------------------------------------------

    "arc de triomphe": {
        "x": 1683,
        "y": 96,
        "z": -1273,
    },

    # --------------------------------------------------------
    # Pierre Bourdieu
    # --------------------------------------------------------

    "pierre bourdieu": {
        "x": 1746,
        "y": 95,
        "z": -1418,
    },

    # --------------------------------------------------------
    # Usine à fer
    # --------------------------------------------------------

    "usine a fer": {
        "x": 1690,
        "y": 132,
        "z": -1145,
    },

    "usine à fer": {
        "x": 1690,
        "y": 132,
        "z": -1145,
    },

    # --------------------------------------------------------
    # Church
    # --------------------------------------------------------

    "churh": {
        "x": 1822,
        "y": 112,
        "z": -1413,
    },

    "church": {
        "x": 1822,
        "y": 112,
        "z": -1413,
    },

    # --------------------------------------------------------
    # Theatre
    # --------------------------------------------------------

    "theatre": {
        "x": 1714,
        "y": 95,
        "z": -1466,
    },

    "théâtre": {
        "x": 1714,
        "y": 95,
        "z": -1466,
    },

    # --------------------------------------------------------
    # Salle des coffres
    # --------------------------------------------------------

    "salle des coffres": {
        "x": 1792,
        "y": 102,
        "z": -1158,
    },
}


# ============================================================
# ELIZA CONFIGURATION
# ============================================================

eliza_bot = eliza.Eliza()

eliza_path = os.path.join(
    os.path.dirname(__file__),
    "eliza",
    "doctor.txt",
)

eliza_bot.load(eliza_path)


# ============================================================
# MINECRAFT BOT
# ============================================================

class MCBot:

    def __init__(self, bot_name):

        self.bot_args = {
            "host": server_host,
            "port": server_port,
            "username": bot_name,
            "auth": "microsoft",
            "version": "1.21.11",
            "hideErrors": False,
        }

        self.reconnect = reconnect
        self.bot_name = bot_name

        # ====================================================
        # MODE ACTUEL
        #
        # IDLE
        # HOME
        # POINT
        # PLAYER
        # PATROL
        # ====================================================

        self.mode = "IDLE"

        # ====================================================
        # PATROUILLE
        # ====================================================

        self.patrol_active = False

        # ====================================================
        # TASK GENERATION
        #
        # Chaque nouvelle commande augmente ce nombre.
        #
        # Exemple :
        #
        # task 1 = go cathedral
        # task 2 = home
        #
        # La task 1 devient automatiquement invalide.
        # ====================================================

        self.task_generation = 0

        # ====================================================
        # START BOT
        # ====================================================

        self.start_bot()

        # ====================================================
        # TERMINAL
        # ====================================================

        threading.Thread(
            target=self.terminal_loop,
            daemon=True,
        ).start()


    # ========================================================
    # LOG
    # ========================================================

    def log(self, message):

        try:
            username = self.bot.username
        except Exception:
            username = self.bot_name

        print(
            f"[{username}] {message}"
        )


    # ========================================================
    # NEW TASK
    #
    # Annule automatiquement la tâche précédente.
    # ========================================================

    def new_task(self, mode):

        self.task_generation += 1

        self.mode = mode

        return self.task_generation


    # ========================================================
    # CHECK TASK
    #
    # Permet de vérifier qu'une tâche est toujours valide.
    # ========================================================

    def task_is_valid(self, generation):

        return (
            generation
            == self.task_generation
        )


    # ========================================================
    # STOP CURRENT MOVEMENT
    # ========================================================

    def stop_movement(self):

        try:

            self.bot.pathfinder.setGoal(
                None
            )

        except Exception:
            pass


    # ========================================================
    # CANCEL CURRENT TASK
    # ========================================================

    def cancel_current_task(self):

        # Invalide toutes les anciennes tâches
        self.task_generation += 1

        self.patrol_active = False

        self.mode = "IDLE"

        self.stop_movement()


    # ========================================================
    # PATHFINDING
    # ========================================================

    def pathfind_to_goal(
        self,
        goal_location
    ):

        try:

            goal = (
                mineflayer_pathfinder
                .pathfinder
                .goals
                .GoalNear(
                    goal_location["x"],
                    goal_location["y"],
                    goal_location["z"],
                    1,
                )
            )

            self.bot.pathfinder.setGoal(
                goal
            )

        except Exception as e:

            self.log(
                chalk.red(
                    f"Pathfinding error: "
                    f"{e}"
                )
            )


    # ========================================================
    # HOME
    # ========================================================

    def go_home(self):

        # ----------------------------------------------------
        # Nouvelle tâche
        # ----------------------------------------------------

        generation = self.new_task(
            "HOME"
        )

        # ----------------------------------------------------
        # Arrêt patrouille
        # ----------------------------------------------------

        self.patrol_active = False

        # ----------------------------------------------------
        # Arrêt ancien déplacement
        # ----------------------------------------------------

        self.stop_movement()

        home = vec3(
            HOME["x"],
            HOME["y"],
            HOME["z"],
        )

        self.log(
            chalk.magenta(
                f"Retour à la maison : "
                f"{vec3_to_str(home)}"
            )
        )

        try:

            self.bot.chat(
                "Je rentre à la maison."
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # Nouvelle destination
        # ----------------------------------------------------

        self.pathfind_to_goal(
            home
        )


    # ========================================================
    # GO TO POINT OF INTEREST
    # ========================================================

    def go_to_point(
        self,
        point_name
    ):

        point_name = (
            point_name
            .strip()
            .lower()
        )

        if point_name not in POINTS_INTERET:

            self.log(
                chalk.red(
                    f"Point d'intérêt inconnu : "
                    f"{point_name}"
                )
            )

            return False

        # ----------------------------------------------------
        # Nouvelle tâche
        # ----------------------------------------------------

        generation = self.new_task(
            "POINT"
        )

        # ----------------------------------------------------
        # Arrêt patrouille
        # ----------------------------------------------------

        self.patrol_active = False

        # ----------------------------------------------------
        # Arrêt déplacement précédent
        # ----------------------------------------------------

        self.stop_movement()

        point = POINTS_INTERET[
            point_name
        ]

        target = vec3(
            point["x"],
            point["y"],
            point["z"],
        )

        self.log(
            chalk.magenta(
                f"Déplacement vers "
                f"{point_name} : "
                f"{vec3_to_str(target)}"
            )
        )

        try:

            self.bot.chat(
                f"J'arrive à "
                f"{point_name} !"
            )

        except Exception:
            pass

        self.pathfind_to_goal(
            target
        )

        return True


    # ========================================================
    # FIND PLAYER BY UUID
    # ========================================================

    def find_player(
        self,
        player_uuid
    ):

        try:

            for player_name in self.bot.players:

                player_data = (
                    self.bot.players[
                        player_name
                    ]
                )

                if (
                    player_data["uuid"]
                    == player_uuid
                ):

                    if player_data.entity:

                        return (
                            player_data
                            .entity
                            .position
                        )

        except Exception as e:

            self.log(
                chalk.red(
                    f"Player search error: "
                    f"{e}"
                )
            )

        return None


    # ========================================================
    # FIND PLAYER BY NAME
    # ========================================================

    def find_player_by_name(
        self,
        player_name
    ):

        player_name = (
            player_name.strip()
        )

        if not player_name:
            return None

        try:

            # ------------------------------------------------
            # Recherche exacte
            # ------------------------------------------------

            if (
                player_name
                in self.bot.players
            ):

                player_data = (
                    self.bot.players[
                        player_name
                    ]
                )

                if player_data.entity:

                    return (
                        player_name,
                        player_data.entity,
                    )

            # ------------------------------------------------
            # Recherche sans casse
            # ------------------------------------------------

            for name in self.bot.players:

                if (
                    name.lower()
                    == player_name.lower()
                ):

                    player_data = (
                        self.bot.players[
                            name
                        ]
                    )

                    if player_data.entity:

                        return (
                            name,
                            player_data.entity,
                        )

        except Exception as e:

            self.log(
                chalk.red(
                    f"Player search error: "
                    f"{e}"
                )
            )

        return None


    # ========================================================
    # GO TO PLAYER
    # ========================================================

    def go_to_player(
        self,
        player_name
    ):

        player_name = (
            player_name.strip()
        )

        if not player_name:

            self.log(
                chalk.red(
                    "Nom du joueur manquant."
                )
            )

            return False

        result = (
            self.find_player_by_name(
                player_name
            )
        )

        if result is None:

            self.log(
                chalk.red(
                    f"Joueur introuvable "
                    f"ou sans entité chargée : "
                    f"{player_name}"
                )
            )

            return False

        real_name, player_entity = result

        # ----------------------------------------------------
        # Nouvelle tâche
        # ----------------------------------------------------

        generation = self.new_task(
            "PLAYER"
        )

        # ----------------------------------------------------
        # Arrêt patrouille
        # ----------------------------------------------------

        self.patrol_active = False

        # ----------------------------------------------------
        # Arrêt déplacement précédent
        # ----------------------------------------------------

        self.stop_movement()

        position = (
            player_entity.position
        )

        target = vec3(
            position.x,
            position.y,
            position.z,
        )

        self.log(
            chalk.magenta(
                f"Déplacement vers "
                f"{real_name} : "
                f"{vec3_to_str(target)}"
            )
        )

        try:

            self.bot.chat(
                f"J'arrive vers "
                f"{real_name} !"
            )

        except Exception:
            pass

        self.pathfind_to_goal(
            target
        )

        return True


    # ========================================================
    # GO INTELLIGENT
    #
    # go <destination>
    #
    # 1. Cherche un lieu
    # 2. Sinon cherche un joueur
    # 3. Sinon erreur
    # ========================================================

    def go_to_destination(
        self,
        destination
    ):

        destination = (
            destination.strip()
        )

        if not destination:

            self.log(
                chalk.yellow(
                    "Destination manquante."
                )
            )

            return

        destination_lower = (
            destination.lower()
        )

        # ----------------------------------------------------
        # LIEU
        # ----------------------------------------------------

        if (
            destination_lower
            in POINTS_INTERET
        ):

            self.go_to_point(
                destination_lower
            )

            return

        # ----------------------------------------------------
        # JOUEUR
        # ----------------------------------------------------

        player_result = (
            self.find_player_by_name(
                destination
            )
        )

        if player_result is not None:

            self.go_to_player(
                destination
            )

            return

        # ----------------------------------------------------
        # INCONNU
        # ----------------------------------------------------

        self.log(
            chalk.red(
                f"Destination introuvable : "
                f"{destination}"
            )
        )

        print(
            chalk.gray(
                "La destination doit être "
                "un lieu ou un joueur visible."
            )
        )


    # ========================================================
    # RANDOM PATROL POSITION
    # ========================================================

    def get_random_patrol_position(
        self
    ):

        x = (
            HOME["x"]
            + random.randint(
                -PATROL_RADIUS,
                PATROL_RADIUS,
            )
        )

        z = (
            HOME["z"]
            + random.randint(
                -PATROL_RADIUS,
                PATROL_RADIUS,
            )
        )

        return vec3(
            x,
            HOME["y"],
            z,
        )


    # ========================================================
    # START PATROL
    # ========================================================

    def start_patrol(self):

        if self.patrol_active:

            try:

                self.bot.chat(
                    "Je patrouille déjà."
                )

            except Exception:
                pass

            return

        # ----------------------------------------------------
        # Nouvelle tâche
        # ----------------------------------------------------

        self.task_generation += 1

        self.mode = "PATROL"

        self.patrol_active = True

        generation = (
            self.task_generation
        )

        # ----------------------------------------------------
        # Arrêt ancien déplacement
        # ----------------------------------------------------

        self.stop_movement()

        try:

            self.bot.chat(
                f"Je commence ma patrouille "
                f"dans un rayon de "
                f"{PATROL_RADIUS} blocs."
            )

        except Exception:
            pass

        self.log(
            chalk.cyan(
                f"Patrouille activée - "
                f"rayon {PATROL_RADIUS}"
            )
        )

        self.run_patrol_step(
            generation
        )


    # ========================================================
    # PATROL STEP
    # ========================================================

    def run_patrol_step(
        self,
        generation=None
    ):

        if not self.patrol_active:
            return

        # ----------------------------------------------------
        # Si génération fournie, vérifier qu'elle est encore
        # valide.
        # ----------------------------------------------------

        if generation is not None:

            if not self.task_is_valid(
                generation
            ):

                return

        target = (
            self.get_random_patrol_position()
        )

        self.log(
            chalk.magenta(
                f"Nouvelle destination "
                f"de patrouille : "
                f"{vec3_to_str(target)}"
            )
        )

        self.pathfind_to_goal(
            target
        )


    # ========================================================
    # LIST PLAYERS
    # ========================================================

    def list_players(self):

        try:

            players = list(
                self.bot.players.keys()
            )

            if not players:

                print(
                    chalk.yellow(
                        "Aucun joueur visible."
                    )
                )

                return

            print()

            print(
                chalk.cyan(
                    "Joueurs visibles :"
                )
            )

            for player_name in players:

                player_data = (
                    self.bot.players[
                        player_name
                    ]
                )

                if player_data.entity:

                    position = (
                        player_data
                        .entity
                        .position
                    )

                    print(
                        f"  - {player_name} "
                        f"{vec3_to_str(position)}"
                    )

                else:

                    print(
                        f"  - {player_name} "
                        f"(position inconnue)"
                    )

            print()

        except Exception as e:

            self.log(
                chalk.red(
                    f"Erreur joueurs : "
                    f"{e}"
                )
            )


    # ========================================================
    # TERMINAL
    # ========================================================

    def terminal_loop(self):

        time.sleep(1)

        print()

        print(
            chalk.green(
                "=========================================="
            )
        )

        print(
            chalk.green(
                "        CONSOLE DU BOT MINECRAFT"
            )
        )

        print(
            chalk.green(
                "=========================================="
            )
        )

        print(
            chalk.gray(
                "Tape 'help' pour voir les commandes."
            )
        )

        print()

        while True:

            try:

                command = input(
                    "> "
                ).strip()

                if not command:
                    continue

                command_lower = (
                    command.lower()
                )


                # ====================================================
                # HELP
                # ====================================================

                if command_lower in [
                    "help",
                    "?",
                ]:

                    print()

                    print(
                        chalk.cyan(
                            "Commandes disponibles :"
                        )
                    )

                    print(
                        "  help"
                        "               → afficher l'aide"
                    )

                    print(
                        "  players"
                        "            → afficher les joueurs"
                    )

                    print(
                        "  patrouille"
                        "         → commencer une patrouille"
                    )

                    print(
                        "  stop"
                        "               → arrêter le déplacement"
                    )

                    print(
                        "  home"
                        "               → rentrer à la maison"
                    )

                    print(
                        "  go <destination>"
                        "   → aller vers un lieu ou joueur"
                    )

                    print(
                        "  say <message>"
                        "      → parler dans le chat"
                    )

                    print(
                        "  quit"
                        "               → quitter le bot"
                    )

                    print()

                    print(
                        chalk.cyan(
                            "Exemples :"
                        )
                    )

                    print(
                        "  go cathedral"
                    )

                    print(
                        "  go cathedrale"
                    )

                    print(
                        "  go george orwell"
                    )

                    print(
                        "  go nThArOs"
                    )

                    print(
                        "  home"
                    )

                    print(
                        "  patrouille"
                    )

                    print()

                    continue


                # ====================================================
                # QUIT
                # ====================================================

                if command_lower == "quit":

                    self.log(
                        chalk.yellow(
                            "Arrêt du bot..."
                        )
                    )

                    self.reconnect = False

                    self.cancel_current_task()

                    try:

                        self.bot.chat(
                            eliza_bot.final()
                        )

                    except Exception:
                        pass

                    try:

                        self.bot.quit()

                    except Exception:
                        pass

                    break


                # ====================================================
                # STOP
                # ====================================================

                if command_lower == "stop":

                    self.cancel_current_task()

                    self.log(
                        chalk.yellow(
                            "✓ Tâche arrêtée."
                        )
                    )

                    continue


                # ====================================================
                # PATROUILLE
                # ====================================================

                if command_lower == "patrouille":

                    self.start_patrol()

                    continue


                # ====================================================
                # HOME
                # ====================================================

                if command_lower == "home":

                    self.go_home()

                    continue


                # ====================================================
                # PLAYERS
                # ====================================================

                if command_lower == "players":

                    self.list_players()

                    continue


                # ====================================================
                # SAY
                # ====================================================

                if command_lower.startswith(
                    "say "
                ):

                    message = (
                        command[
                            len("say "):
                        ].strip()
                    )

                    if not message:

                        self.log(
                            chalk.yellow(
                                "Message vide."
                            )
                        )

                        continue

                    try:

                        self.bot.chat(
                            message
                        )

                        self.log(
                            chalk.cyan(
                                f"Chat : "
                                f"{message}"
                            )
                        )

                    except Exception as e:

                        self.log(
                            chalk.red(
                                f"Erreur chat : "
                                f"{e}"
                            )
                        )

                    continue


                # ====================================================
                # GO
                #
                # Une seule syntaxe :
                #
                # go <destination>
                #
                # ====================================================

                if command_lower == "go":

                    self.log(
                        chalk.yellow(
                            "Destination manquante."
                        )
                    )

                    print(
                        "Exemples :"
                    )

                    print(
                        "  go cathedral"
                    )

                    print(
                        "  go nThArOs"
                    )

                    continue


                if command_lower.startswith(
                    "go "
                ):

                    destination = (
                        command[
                            len("go "):
                        ].strip()
                    )

                    self.go_to_destination(
                        destination
                    )

                    continue


                # ====================================================
                # UNKNOWN COMMAND
                # ====================================================

                self.log(
                    chalk.red(
                        f"Commande inconnue : "
                        f"{command}"
                    )
                )

                print(
                    chalk.gray(
                        "Tape 'help' pour voir "
                        "les commandes."
                    )
                )


            except EOFError:

                self.log(
                    chalk.yellow(
                        "EOF détecté. "
                        "Arrêt du bot."
                    )
                )

                self.reconnect = False

                self.cancel_current_task()

                try:

                    self.bot.quit()

                except Exception:
                    pass

                break


            except KeyboardInterrupt:

                print()

                self.log(
                    chalk.yellow(
                        "Ctrl+C détecté. "
                        "Arrêt du bot."
                    )
                )

                self.reconnect = False

                self.cancel_current_task()

                try:

                    self.bot.quit()

                except Exception:
                    pass

                break


            except Exception as e:

                self.log(
                    chalk.red(
                        f"Erreur terminal : "
                        f"{e}"
                    )
                )


    # ========================================================
    # START BOT
    # ========================================================

    def start_bot(self):

        self.bot = (
            mineflayer.createBot(
                self.bot_args
            )
        )

        # ----------------------------------------------------
        # Pathfinder
        # ----------------------------------------------------

        self.bot.loadPlugin(
            mineflayer_pathfinder.pathfinder
        )

        # ----------------------------------------------------
        # Auto Eat
        # ----------------------------------------------------

        self.bot.loadPlugin(
            mineflayer_auto_eat
        )

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


        # ====================================================
        # LOGIN
        # ====================================================

        @On(
            self.bot,
            "login"
        )
        def login():

            try:

                self.bot_socket = (
                    self.bot._client.socket
                )

                server = (
                    self.bot_socket.server
                    if self.bot_socket.server
                    else self.bot_socket._host
                )

                self.log(
                    chalk.green(
                        f"Logged in to "
                        f"{server}"
                    )
                )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"Login error: "
                        f"{e}"
                    )
                )


        # ====================================================
        # SPAWN
        # ====================================================

        @On(
            self.bot,
            "spawn"
        )
        def spawn():

            try:

                message = (
                    eliza_bot.initial()
                )

                self.bot.chat(
                    message
                )

                self.log(
                    chalk.green(
                        f"ELIZA: "
                        f"{message}"
                    )
                )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"ELIZA error: "
                        f"{e}"
                    )
                )


        # ====================================================
        # KICKED
        # ====================================================

        @On(
            self.bot,
            "kicked"
        )
        def kicked(
            reason,
            loggedIn
        ):

            if loggedIn:

                self.log(
                    chalk.redBright(
                        f"Kicked whilst "
                        f"trying to connect: "
                        f"{reason}"
                    )
                )


        # ====================================================
        # GOAL REACHED
        # ====================================================

        @On(
            self.bot,
            "goal_reached"
        )
        def goal_reached(
            _this,
            _goal
        ):

            # =================================================
            # PATROUILLE
            # =================================================

            if self.patrol_active:

                current_generation = (
                    self.task_generation
                )

                self.log(
                    chalk.green(
                        "Destination de patrouille "
                        "atteinte."
                    )
                )

                self.log(
                    chalk.gray(
                        f"Pause de "
                        f"{PATROL_WAIT_SECONDS} "
                        f"secondes..."
                    )
                )

                def continue_patrol():

                    time.sleep(
                        PATROL_WAIT_SECONDS
                    )

                    # ------------------------------------------------
                    # Vérifie que personne n'a donné une nouvelle
                    # commande pendant la pause.
                    # ------------------------------------------------

                    if not self.patrol_active:
                        return

                    if not self.task_is_valid(
                        current_generation
                    ):
                        return

                    self.run_patrol_step(
                        current_generation
                    )

                threading.Thread(
                    target=continue_patrol,
                    daemon=True,
                ).start()

                return


            # =================================================
            # HOME
            # =================================================

            if self.mode == "HOME":

                self.log(
                    chalk.green(
                        "✓ Tâche terminée : "
                        "je suis arrivé à la maison."
                    )
                )

                try:

                    self.bot.chat(
                        "Je suis arrivé à la maison."
                    )

                except Exception:
                    pass

                self.mode = "IDLE"

                return


            # =================================================
            # POINT
            # =================================================

            if self.mode == "POINT":

                self.log(
                    chalk.green(
                        "✓ Tâche terminée : "
                        "je suis arrivé à destination."
                    )
                )

                try:

                    self.bot.chat(
                        "Je suis arrivé à destination."
                    )

                except Exception:
                    pass

                self.mode = "IDLE"

                return


            # =================================================
            # PLAYER
            # =================================================

            if self.mode == "PLAYER":

                self.log(
                    chalk.green(
                        "✓ Tâche terminée : "
                        "je suis arrivé auprès du joueur."
                    )
                )

                try:

                    self.bot.chat(
                        "Je suis arrivé !"
                    )

                except Exception:
                    pass

                self.mode = "IDLE"

                return


        # ====================================================
        # CHAT
        # ====================================================

        @On(
            self.bot,
            "messagestr"
        )
        def messagestr(
            message,
            messagePosition,
            jsonMsg,
            sender,
            verified=None,
        ):

            # ------------------------------------------------
            # Seulement chat normal
            # ------------------------------------------------

            if messagePosition != "chat":
                return

            # ------------------------------------------------
            # Ignorer ses propres messages
            # ------------------------------------------------

            if self.bot.player:

                if (
                    sender
                    == self.bot.player.uuid
                ):

                    return

            # ------------------------------------------------
            # Message reçu
            # ------------------------------------------------

            original_message = (
                message.strip()
            )

            self.log(
                chalk.yellow(
                    f"Message received: "
                    f"{original_message}"
                )
            )

            # ------------------------------------------------
            # Retirer <joueur>
            # ------------------------------------------------

            message_no_tag = (
                original_message
            )

            if message_no_tag.startswith(
                "<"
            ):

                end_tag = (
                    message_no_tag.find(
                        ">"
                    )
                )

                if end_tag != -1:

                    message_no_tag = (
                        message_no_tag[
                            end_tag + 1:
                        ].strip()
                    )

            message_lower = (
                message_no_tag.lower()
            )

            self.log(
                chalk.gray(
                    f"Message analysé: "
                    f"{message_no_tag}"
                )
            )


            # =================================================
            # QUIT
            # =================================================

            if message_lower == "quit":

                try:

                    self.bot.chat(
                        eliza_bot.final()
                    )

                    self.reconnect = False

                    self.cancel_current_task()

                    self.bot.quit()

                except Exception as e:

                    self.log(
                        chalk.red(
                            f"Quit error: "
                            f"{e}"
                        )
                    )

                return


            # =================================================
            # COME TO ME
            # =================================================

            if message_lower in [
                "come to me",
                "viens",
                "viens me voir",
                "viens ici",
                "rejoins moi",
                "rejoins-moi",
            ]:

                # ------------------------------------------------
                # Nouvelle tâche
                # ------------------------------------------------

                self.new_task(
                    "PLAYER"
                )

                self.patrol_active = False

                self.stop_movement()

                player_location = (
                    self.find_player(
                        sender
                    )
                )

                if player_location:

                    target = vec3(
                        player_location["x"],
                        player_location["y"] + 1,
                        player_location["z"],
                    )

                    self.log(
                        chalk.magenta(
                            f"Pathfinding to "
                            f"{vec3_to_str(target)}"
                        )
                    )

                    try:

                        self.bot.chat(
                            "J'arrive !"
                        )

                    except Exception:
                        pass

                    self.pathfind_to_goal(
                        target
                    )

                else:

                    try:

                        self.bot.chat(
                            "Je ne trouve pas "
                            "ce joueur."
                        )

                    except Exception:
                        pass

                return


            # =================================================
            # STOP
            # =================================================

            if message_lower == "stop":

                self.cancel_current_task()

                try:

                    self.bot.chat(
                        "D'accord, j'arrête."
                    )

                except Exception:
                    pass

                return


            # =================================================
            # PATROUILLE
            # =================================================

            if message_lower in [
                "patrouille",
                "patrol",
                "patrouiller",
                "fais une patrouille",
                "commence la patrouille",
            ]:

                self.start_patrol()

                return


            # =================================================
            # HOME
            # =================================================

            if message_lower in [
                "home",
                "maison",
                "rentre",
                "rentre à la maison",
                "rentre a la maison",
                "retourne à la maison",
                "retourne a la maison",
            ]:

                self.go_home()

                return


            # =================================================
            # GO
            # =================================================

            if message_lower == "go":

                try:

                    self.bot.chat(
                        "Où veux-tu que j'aille ?"
                    )

                except Exception:
                    pass

                return


            if message_lower.startswith(
                "go "
            ):

                destination = (
                    message_no_tag[
                        len("go "):
                    ].strip()
                )

                self.go_to_destination(
                    destination
                )

                return


            # =================================================
            # POINT D'INTERET DIRECT
            # =================================================

            if (
                message_lower
                in POINTS_INTERET
            ):

                self.go_to_point(
                    message_lower
                )

                return


            # =================================================
            # PREFIXES FRANCAIS
            # =================================================

            prefixes = [
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
            ]

            for prefix in prefixes:

                if message_lower.startswith(
                    prefix
                ):

                    destination = (
                        message_no_tag[
                            len(prefix):
                        ].strip()
                    )

                    self.go_to_destination(
                        destination
                    )

                    return


            # =================================================
            # ELIZA
            # =================================================

            try:

                response = (
                    eliza_bot.respond(
                        message_no_tag
                    )
                )

                if response:

                    self.bot.chat(
                        response
                    )

                    self.log(
                        chalk.cyan(
                            f"ELIZA: "
                            f"{response}"
                        )
                    )

                else:

                    self.bot.chat(
                        "Je ne sais pas "
                        "quoi répondre."
                    )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"ELIZA response error: "
                        f"{e}"
                    )
                )


        # ====================================================
        # END
        # ====================================================

        @On(
            self.bot,
            "end"
        )
        def end(reason):

            self.log(
                chalk.red(
                    f"Disconnected: "
                    f"{reason}"
                )
            )

            # ------------------------------------------------
            # Remove old listeners
            # ------------------------------------------------

            off(
                self.bot,
                "login",
                login,
            )

            off(
                self.bot,
                "spawn",
                spawn,
            )

            off(
                self.bot,
                "kicked",
                kicked,
            )

            off(
                self.bot,
                "messagestr",
                messagestr,
            )

            # ------------------------------------------------
            # Reconnect
            # ------------------------------------------------

            if self.reconnect:

                self.log(
                    chalk.cyanBright(
                        "Attempting to reconnect..."
                    )
                )

                self.start_bot()

            off(
                self.bot,
                "end",
                end,
            )


# ============================================================
# START BOT
# ============================================================

bot = MCBot(
    "pathfinder-bot"
)
