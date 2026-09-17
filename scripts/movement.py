from simple_chalk import chalk
from javascript import require
from utils.vec3_conversion import vec3_to_str
from config import (
    PATROL_WAIT,
    PATROL_STUCK_CHECK_INTERVAL,
    PATROL_STUCK_MIN_DISTANCE,
    PATROL_STUCK_CHECKS,
)
from points import POINTS_INTERET, QUARTIERS, GRAPH
import time
import threading

vec3 = require("vec3")


# ============================================================
# PATROUILLE ET TRAJETS SUR LE GRAPHE
#
# Mixin pour MCBot (voir bot.py). Deux façons d'utiliser le
# même moteur d'itinéraire (patrol_route / patrol_index) :
# - patrouille : boucle sans fin sur tout le graphe ou un
#   quartier (route_loop = True).
# - chemin/route : trajet ponctuel vers un point précis,
#   s'arrête une fois arrivé (route_loop = False).
# Dans les deux cas, mineflayer-pathfinder calcule le vrai
# chemin entre deux points consécutifs de l'itinéraire.
# ============================================================

class MovementMixin:

    # --------------------------------------------------------
    # Outils de graphe
    #
    # Utilitaires partagés par la patrouille, "chemin" et la
    # livraison : trouver un quartier, lister les points d'un
    # quartier/du graphe entier, trouver le point connu le plus
    # proche du bot, et calculer un chemin dans GRAPH.
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Patrouille (boucle)
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Trajet ponctuel (chemin/route)
    # --------------------------------------------------------

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


    def travel_to_and_wait(self, destination, timeout=180):
        # Utilisé par les tâches multi-étapes (livraison) qui ont
        # besoin de bloquer jusqu'à l'arrivée réelle, contrairement
        # à go_via_graph qui ne fait que lancer le trajet.

        self.route_arrived_event.clear()

        if not self.go_via_graph(destination):
            return False

        return self.route_arrived_event.wait(timeout)


    # --------------------------------------------------------
    # Exécution pas à pas de l'itinéraire
    # --------------------------------------------------------

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

        self.start_patrol_watchdog(
            generation,
            self.patrol_index,
            point,
        )


    def start_patrol_watchdog(self, generation, index, point_name):
        # Si goal_reached ne se déclenche jamais (point
        # inatteignable, coincé sur le terrain...), on ne veut
        # pas rester bloqué indéfiniment. Mais un simple délai
        # fixe coupait des trajets encore en cours (points
        # éloignés sur le chemin de montagne) : on vérifie donc
        # que le bot a réellement arrêté de bouger, pas juste
        # qu'il met du temps à arriver.

        def watchdog():
            last_pos = self.get_bot_position()
            stale_checks = 0

            while True:
                time.sleep(PATROL_STUCK_CHECK_INTERVAL)

                if not self.patrol_active:
                    return

                if (
                    generation is not None
                    and not self.task_valid(generation)
                ):
                    return

                if self.patrol_index != index:
                    return

                current_pos = self.get_bot_position()

                if last_pos is not None and current_pos is not None:
                    moved = (
                        (current_pos[0] - last_pos[0]) ** 2
                        + (current_pos[2] - last_pos[2]) ** 2
                    ) ** 0.5

                    if moved < PATROL_STUCK_MIN_DISTANCE:
                        stale_checks += 1
                    else:
                        stale_checks = 0

                last_pos = current_pos

                if stale_checks >= PATROL_STUCK_CHECKS:
                    self.log(
                        chalk.yellow(
                            f"⚠ Bloqué en essayant d'atteindre "
                            f"{point_name}, je passe au point suivant."
                        )
                    )

                    self.chat(
                        f"Je n'arrive pas à atteindre {point_name}, je continue."
                    )

                    self.run_patrol_route_step(generation)

                    return

        threading.Thread(
            target=watchdog,
            daemon=True,
        ).start()


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
                self.route_arrived_event.set()
                self.cancel_task()
                return
        else:
            self.patrol_index += 1

        self.goto_patrol_index(generation)
