from simple_chalk import chalk
from points import POINTS_INTERET, QUARTIERS
import sys
import time


# ============================================================
# COMMAND HANDLER + TERMINAL
#
# Mixin pour MCBot (voir bot.py). Utilisé par le TERMINAL et
# le CHAT en jeu (handle_command est appelé des deux côtés).
# ============================================================

class CommandsMixin:

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
            self.chat("À plus tard !")

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

        if lower in ("chemin", "route"):
            self.log(
                chalk.yellow("Destination manquante.")
            )
            self.chat("Vers quel point ? (chemin <point>)")
            return True

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
        # LIVRAISON
        # ----------------------------------------------------

        if lower in ("livraison", "livraisons"):
            self.start_delivery("")
            return True

        if lower.startswith("livraison "):
            self.start_delivery(
                command[len("livraison "):]
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
        # AGENT DE CONVERSATION (LLM)
        # ----------------------------------------------------

        try:
            response = self.conversation.respond(sender, command)

            if response:
                self.chat(response)
                self.log(
                    chalk.cyan(
                        f"LLM: {response}"
                    )
                )

        except Exception as e:
            self.log(
                chalk.red(
                    f"LLM error: {e}"
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
                        "  livraison <point>     → vider un coffre et livrer à la salle des coffres\n"
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


    def pipe_listener_loop(self):
        """Écoute stdin en continu lorsque le bot est supervisé par un orchestrateur."""
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

            except Exception as e:
                self.log(
                    chalk.red(
                        f"Terminal error: {e}"
                    )
                )
