from javascript import require, On, off
from simple_chalk import chalk
from eliza import eliza
from utils.vec3_conversion import vec3_to_str
import os
import time
import random
import threading


# =========================
# Import JavaScript libraries
# =========================

mineflayer = require("mineflayer")
mineflayer_pathfinder = require("mineflayer-pathfinder")
mineflayer_auto_eat = require("mineflayer-auto-eat").default
vec3 = require("vec3")


# =========================
# Server configuration
# =========================

server_host = "game02.octoheberg.fr"
server_port = 25571
reconnect = True


# =========================
# HOME / PATROL CONFIG
# =========================

HOME = {
    "x": 1802,
    "y": 130,
    "z": -1328,
}

PATROL_RADIUS = 16
PATROL_WAIT_SECONDS = 5


# =========================
# POINTS D'INTERET
# =========================

POINTS_INTERET = {
    "cathderal": {
        "x": 1776,
        "y": 129,
        "z": -1328,
    },
    "george orwell": {
        "x": 1697,
        "y": 96,
        "z": -1323,
    },
    "arc de triomphe": {
        "x": 1683,
        "y": 96,
        "z": -1273,
    },
    "pierre bourdieu": {
        "x": 1746,
        "y": 95,
        "z": -1418,
    },
    "usine a fer": {
        "x": 1690,
        "y": 132,
        "z": -1145,
    },
    "churh": {
        "x": 1822,
        "y": 112,
        "z": -1413,
    },
    "theatre": {
        "x": 1714,
        "y": 95,
        "z": -1466,
    },
    "salle des coffres": {
        "x": 1792,
        "y": 102,
        "z": -1158,
    },
}


# =========================
# ELIZA configuration
# =========================

eliza_bot = eliza.Eliza()

eliza_path = os.path.join(
    os.path.dirname(__file__),
    "eliza",
    "doctor.txt",
)

eliza_bot.load(eliza_path)


# =========================
# Minecraft Bot
# =========================

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

        self.patrol_active = False
        self.patrol_task = None

        self.mode = "IDLE"
        self.patrol_generation = 0

        self.start_bot()

    # =========================
    # Console log
    # =========================

    def log(self, message):
        print(f"[{self.bot.username}] {message}")

    # =========================
    # Pathfinder
    # =========================

    def pathfind_to_goal(self, goal_location):

        try:

            goal = mineflayer_pathfinder.pathfinder.goals.GoalNear(
                goal_location["x"],
                goal_location["y"],
                goal_location["z"],
                1,
            )

            self.bot.pathfinder.setGoal(goal)

        except Exception as e:

            self.log(
                chalk.red(
                    f"Pathfinding error: {e}"
                )
            )

    # =========================
    # HOME
    # =========================

    def go_home(self):

        self.log(
            chalk.magenta(
                f"Retour à la maison : "
                f"{HOME['x']} "
                f"{HOME['y']} "
                f"{HOME['z']}"
            )
        )

        home = vec3(
            HOME["x"],
            HOME["y"],
            HOME["z"],
        )

        self.pathfind_to_goal(home)

    # =========================
    # POINTS D'INTERET
    # =========================

    def go_to_point(self, point_name):

        if point_name not in POINTS_INTERET:

            self.bot.chat(
                f"Je ne connais pas le point d'intérêt : "
                f"{point_name}"
            )

            return

        self.stop_patrol()

        point = POINTS_INTERET[point_name]

        target = vec3(
            point["x"],
            point["y"],
            point["z"],
        )

        self.log(
            chalk.magenta(
                f"Déplacement vers {point_name} : "
                f"{vec3_to_str(target)}"
            )
        )

        self.bot.chat(
            f"J'arrive à {point_name} !"
        )

        self.pathfind_to_goal(target)

    # =========================
    # STOP PATROL
    # =========================

    def stop_patrol(self):

        self.patrol_active = False

        try:

            self.bot.pathfinder.setGoal(None)

        except Exception:

            pass

        self.log(
            chalk.yellow(
                "Patrouille arrêtée."
            )
        )

    # =========================
    # RANDOM PATROL POSITION
    # =========================

    def get_random_patrol_position(self):

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

    # =========================
    # START PATROL
    # =========================

    def start_patrol(self):

        if self.patrol_active:

            self.bot.chat(
                "Je patrouille déjà."
            )

            return

        self.patrol_active = True

        self.bot.chat(
            f"Je commence ma patrouille "
            f"dans un rayon de {PATROL_RADIUS} blocs."
        )

        self.log(
            chalk.cyan(
                f"Patrouille activée - "
                f"rayon {PATROL_RADIUS}"
            )
        )

        self.run_patrol_step()

    # =========================
    # PATROL STEP
    # =========================

    def run_patrol_step(self):

        if not self.patrol_active:
            return

        target = self.get_random_patrol_position()

        self.log(
            chalk.magenta(
                f"Nouvelle destination de patrouille : "
                f"{vec3_to_str(target)}"
            )
        )

        self.pathfind_to_goal(target)

    # =========================
    # Find player
    # =========================

    def find_player(self, player_uuid):

        try:

            for player_name in self.bot.players:

                player_data = (
                    self.bot.players[player_name]
                )

                if player_data["uuid"] == player_uuid:

                    if player_data.entity:

                        return (
                            player_data.entity.position
                        )

        except Exception as e:

            self.log(
                chalk.red(
                    f"Player search error: {e}"
                )
            )

        return None

    # =========================
    # Start bot
    # =========================

    def start_bot(self):

        self.bot = mineflayer.createBot(
            self.bot_args
        )

        # Pathfinder
        self.bot.loadPlugin(
            mineflayer_pathfinder.pathfinder
        )

        # Auto Eat
        self.bot.loadPlugin(
            mineflayer_auto_eat
        )

        # Auto Eat configuration
        self.bot.autoEat.options = {
            "priority": "foodPoints",
            "startAt": 14,
            "bannedFood": [],
        }

        self.start_events()

    # =========================
    # Events
    # =========================

    def start_events(self):

        # =========================
        # LOGIN
        # =========================

        @On(self.bot, "login")
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
                        f"Logged in to {server}"
                    )
                )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"Login error: {e}"
                    )
                )

        # =========================
        # SPAWN
        # =========================

        @On(self.bot, "spawn")
        def spawn():

            try:

                message = eliza_bot.initial()

                self.bot.chat(message)

                self.log(
                    chalk.green(
                        f"ELIZA: {message}"
                    )
                )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"ELIZA error: {e}"
                    )
                )

        # =========================
        # KICKED
        # =========================

        @On(self.bot, "kicked")
        def kicked(reason, loggedIn):

            if loggedIn:

                self.log(
                    chalk.redBright(
                        f"Kicked whilst trying to connect: "
                        f"{reason}"
                    )
                )

        # =========================
        # GOAL REACHED
        # =========================

        @On(self.bot, "goal_reached")
        def goal_reached(_this, _goal):

            if not self.patrol_active:
                return

            self.log(
                chalk.green(
                    "Destination de patrouille atteinte."
                )
            )

            self.log(
                chalk.gray(
                    f"Pause de "
                    f"{PATROL_WAIT_SECONDS} secondes..."
                )
            )

            def continue_patrol():

                time.sleep(
                    PATROL_WAIT_SECONDS
                )

                if self.patrol_active:

                    self.run_patrol_step()

            threading.Thread(
                target=continue_patrol,
                daemon=True,
            ).start()

        # =========================
        # CHAT
        # =========================

        @On(self.bot, "messagestr")
        def messagestr(
            message,
            messagePosition,
            jsonMsg,
            sender,
            verified=None,
        ):

            # Only normal chat
            if messagePosition != "chat":
                return

            # Ignore own messages
            if self.bot.player:

                if sender == self.bot.player.uuid:
                    return

            # =========================
            # Message reçu
            # =========================

            original_message = message.strip()

            self.log(
                chalk.yellow(
                    f"Message received: "
                    f"{original_message}"
                )
            )

            # =========================
            # Nettoyage du message
            # =========================

            message_no_tag = original_message

            if message_no_tag.startswith("<"):

                end_tag = message_no_tag.find(">")

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

            # =========================
            # QUIT
            # =========================

            if message_lower == "quit":

                try:

                    self.bot.chat(
                        eliza_bot.final()
                    )

                    self.reconnect = False

                    self.bot.quit()

                except Exception as e:

                    self.log(
                        chalk.red(
                            f"Quit error: {e}"
                        )
                    )

                return

            # =========================
            # COME TO ME
            # =========================

            if message_lower in [
                "come to me",
                "viens",
                "viens me voir",
                "viens ici",
                "rejoins moi",
                "rejoins-moi",
            ]:

                self.stop_patrol()

                player_location = (
                    self.find_player(sender)
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

                    self.bot.chat(
                        "J'arrive !"
                    )

                    self.pathfind_to_goal(
                        target
                    )

                else:

                    self.bot.chat(
                        "Je ne trouve pas ce joueur."
                    )

                return

            # =========================
            # STOP
            # =========================

            if message_lower in [
                "stop",
                "arrête",
                "arrete",
                "stoppe",
            ]:

                self.patrol_active = False

                try:

                    self.bot.pathfinder.setGoal(
                        None
                    )

                    self.bot.chat(
                        "D'accord, j'arrête."
                    )

                except Exception as e:

                    self.log(
                        chalk.red(
                            f"Stop error: {e}"
                        )
                    )

                return

            # =========================
            # PATROL
            # =========================

            if message_lower in [
                "patrouille",
                "patrol",
                "patrouiller",
                "fais une patrouille",
                "commence la patrouille",
            ]:

                self.start_patrol()

                return

            # =========================
            # STOP PATROL
            # =========================

            if message_lower in [
                "stop patrouille",
                "arrête la patrouille",
                "arrete la patrouille",
            ]:

                self.stop_patrol()

                self.bot.chat(
                    "J'arrête ma patrouille."
                )

                return

            # =========================
            # HOME
            # =========================

            if message_lower in [
                "rentre",
                "rentre à la maison",
                "rentre a la maison",
                "retourne à la maison",
                "retourne a la maison",
                "go home",
                "home",
                "maison",
            ]:

                self.stop_patrol()

                self.bot.chat(
                    "Je rentre à la maison."
                )

                self.go_home()

                return

            # =========================
            # POINTS D'INTERET
            # =========================

            point_name = None

            # Commande directe
            # Exemple : "theatre"
            if message_lower in POINTS_INTERET:

                point_name = message_lower

            else:

                prefixes = [
                    "va à ",
                    "va a ",
                    "va au ",
                    "va aux ",
                    "va à la ",
                    "va a la ",
                    "va à l'",
                    "va a l'",
                    "go ",
                    "go to",
                    "go t",
                    "aller à ",
                    "aller a ",
                ]

                for prefix in prefixes:

                    if message_lower.startswith(
                        prefix
                    ):

                        requested_place = (
                            message_lower[
                                len(prefix):
                            ].strip()
                        )

                        if (
                            requested_place
                            in POINTS_INTERET
                        ):

                            point_name = (
                                requested_place
                            )

                        break

            if point_name is not None:

                self.go_to_point(
                    point_name
                )

                return

            # =========================
            # ELIZA
            # =========================

            try:

                response = eliza_bot.respond(
                    message_no_tag
                )

                if response:

                    self.bot.chat(
                        response
                    )

                    self.log(
                        chalk.cyan(
                            f"ELIZA: {response}"
                        )
                    )

                else:

                    self.bot.chat(
                        "Je ne sais pas quoi répondre."
                    )

            except Exception as e:

                self.log(
                    chalk.red(
                        f"ELIZA response error: {e}"
                    )
                )

        # =========================
        # END
        # =========================

        @On(self.bot, "end")
        def end(reason):

            self.log(
                chalk.red(
                    f"Disconnected: {reason}"
                )
            )

            # Remove old listeners

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

            # Reconnect

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


# =========================
# Start bot
# =========================

bot = MCBot("pathfinder-bot")
