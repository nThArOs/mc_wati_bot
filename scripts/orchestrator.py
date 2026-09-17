# ============================================================
# LIBRARIES
# ============================================================

import os
import sys
import time
import threading
import subprocess
from simple_chalk import chalk

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

# Chargement de la configuration de la flotte
try:
    from config.fleet import FLEET_CONFIG, STAGGER_DELAY
except ImportError:
    FLEET_CONFIG = [
        {"name": "bot-leader", "role": "leader", "port": 3000, "district": "Haute ville"},
        {"name": "bot-patrol-1", "role": "patrol", "port": 3001, "district": "place george orwell"},
        {"name": "bot-patrol-2", "role": "patrol", "port": 3002, "district": "quartier du theatre"},
    ]
    STAGGER_DELAY = 7


# ============================================================
# BOT PROCESS WRAPPER
# ============================================================

BOT_COLORS = {
    "leader": chalk.green,
    "patrol": chalk.cyan,
    "follower": chalk.yellow,
    "guard": chalk.magenta,
}


class BotProcess:
    """Encapsule un sous-processus de bot unitaire (bot.py)."""

    def __init__(self, bot_info, script_path):
        self.info = bot_info
        self.name = bot_info["name"]
        self.role = bot_info.get("role", "patrol")
        self.port = bot_info.get("port", 3000)
        self.district = bot_info.get("district", "")
        self.script_path = script_path
        self.process = None
        self.color = BOT_COLORS.get(self.role, chalk.white)

    def is_alive(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        if self.is_alive():
            return False

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["BOT_NAME"] = self.name
        env["BOT_ROLE"] = self.role
        env["WEB_INVENTORY_PORT"] = str(self.port)
        env["ENABLE_STDIN_REPL"] = "false"
        if self.district:
            env["ASSIGNED_DISTRICT"] = self.district

        cmd = [sys.executable, self.script_path]

        try:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                universal_newlines=True,
            )

            threading.Thread(
                target=self._stream_output,
                daemon=True,
            ).start()

            return True
        except Exception as e:
            print(chalk.red(f"[{self.name}] Erreur de lancement: {e}"))
            return False

    def _stream_output(self):
        """Redirige les logs du sous-processus vers le terminal maître."""
        if not self.process or not self.process.stdout:
            return

        for line in iter(self.process.stdout.readline, ""):
            if not line:
                break
            stripped = line.rstrip()
            if stripped:
                # Ajoute une coloration sur le préfixe si non présent
                if stripped.startswith("["):
                    print(stripped)
                else:
                    print(self.color(f"[{self.name}]") + f" {stripped}")

    def send_command(self, command):
        """Transmet une commande textuelle via l'entrée standard du bot."""
        if not self.is_alive() or not self.process or not self.process.stdin:
            return False

        try:
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()
            return True
        except Exception as e:
            print(chalk.red(f"[{self.name}] Erreur d'envoi: {e}"))
            return False

    def stop(self):
        """Arrête proprement le bot via 'quit' puis SIGTERM si nécessaire."""
        if not self.is_alive():
            return

        print(chalk.yellow(f"[{self.name}] Arrêt en cours..."))
        self.send_command("quit")

        for _ in range(5):
            if not self.is_alive():
                break
            time.sleep(0.5)

        if self.is_alive():
            try:
                self.process.terminate()
            except Exception:
                pass


# ============================================================
# BOT MANAGER (ORCHESTRATEUR CENTRAL)
# ============================================================

class BotManager:
    """Superviseur multi-instances pour la flotte de bots."""

    def __init__(self, fleet_config=None, stagger_delay=STAGGER_DELAY):
        self.fleet_config = fleet_config or FLEET_CONFIG
        self.stagger_delay = stagger_delay
        self.script_path = os.path.join(
            os.path.dirname(__file__),
            "bot.py",
        )
        self.bots = {}

        for bot_info in self.fleet_config:
            self.bots[bot_info["name"]] = BotProcess(
                bot_info,
                self.script_path,
            )

    def start_fleet(self):
        """Démarre tous les bots de manière échelonnée (staggering)."""
        print()
        print(chalk.cyan("=" * 60))
        print(chalk.cyanBright(" ORCHESTRATEUR : DÉMARRAGE DE LA FLOTTE"))
        print(chalk.cyan("=" * 60))
        print(
            chalk.gray(
                f"Nombre de bots : {len(self.bots)} | "
                f"Délai d'échelonnement : {self.stagger_delay}s"
            )
        )
        print()

        for idx, (name, bot) in enumerate(self.bots.items()):
            role_label = chalk.green(f"({bot.role})")
            port_label = chalk.gray(f"inventaire :{bot.port}")
            print(
                chalk.cyan(f"[{idx + 1}/{len(self.bots)}]")
                + f" Lancement de {chalk.bold(name)} {role_label} - {port_label}..."
            )

            bot.start()

            # Temporisation d'échelonnement sauf pour le dernier
            if idx < len(self.bots) - 1:
                time.sleep(self.stagger_delay)

        print()
        print(chalk.green("✓ Tous les bots ont été initialisés."))
        print(chalk.gray("Tapez 'status' pour voir la flotte ou 'help' pour les commandes."))
        print()

    def stop_fleet(self):
        """Arrête l'ensemble des bots de la flotte."""
        print()
        print(chalk.yellow("Arrêt de tous les bots de la flotte..."))
        for bot in self.bots.values():
            bot.stop()
        print(chalk.green("✓ Flotte arrêtée."))

    def broadcast(self, command):
        """Diffuse un ordre à tous les bots actifs."""
        count = 0
        for bot in self.bots.values():
            if bot.is_alive():
                bot.send_command(command)
                count += 1
        print(chalk.green(f"✓ Commande diffusée à {count} bot(s) : '{command}'"))

    def send_to(self, name, command):
        """Envoie un ordre à un bot spécifique."""
        bot = self.bots.get(name)
        if not bot:
            print(chalk.red(f"Bot introuvable : '{name}'"))
            return False

        if not bot.is_alive():
            print(chalk.yellow(f"Le bot '{name}' n'est pas actif."))
            return False

        bot.send_command(command)
        print(chalk.green(f"✓ Ordre envoyé à {name} : '{command}'"))
        return True

    def print_status(self):
        """Affiche un tableau synthétique de l'état de la flotte."""
        print()
        print(chalk.cyan("=" * 60))
        print(chalk.cyanBright(" ÉTAT DE LA FLOTTE DE BOTS"))
        print(chalk.cyan("=" * 60))

        for name, bot in self.bots.items():
            status = (
                chalk.green(f"ACTIF (PID {bot.process.pid})")
                if bot.is_alive()
                else chalk.red("INACTIF")
            )
            district_info = (
                f" -> {bot.district}" if bot.district else ""
            )
            print(
                f"  - {chalk.bold(name):<16} "
                f"[{bot.role:<7}{district_info}] "
                f"Port:{bot.port:<5} {status}"
            )

        print(chalk.cyan("=" * 60))
        print()

    def terminal_loop(self):
        """Console interactive REPL globale pour l'opérateur."""
        time.sleep(1)

        while True:
            try:
                raw = input()
            except (KeyboardInterrupt, EOFError):
                print()
                self.stop_fleet()
                break

            cmd = raw.strip()
            if not cmd:
                continue

            lower = cmd.lower()

            # Commandes globales de gestion
            if lower in ("quit", "exit", "stop all", "fleet stop"):
                self.stop_fleet()
                break

            if lower in ("status", "statut", "fleet", "flotte"):
                self.print_status()
                continue

            if lower in ("help", "aide"):
                print()
                print(chalk.cyan("=" * 60))
                print(chalk.cyanBright(" COMMANDES DU GESTIONNAIRE DE FLOTTE"))
                print(chalk.cyan("=" * 60))
                print("  - status / fleet          : Afficher l'état des bots de la flotte")
                print("  - all: <commande>         : Envoyer une commande à TOUS les bots")
                print("  - <nom_du_bot>: <cmd>     : Envoyer une commande à un bot précis")
                print("  - fleet patrol            : Lancer les patrouilles sur quartiers assignés")
                print("  - start <nom_du_bot>      : Redémarrer un bot individuellement")
                print("  - stop <nom_du_bot>       : Arrêter un bot spécifique")
                print("  - quit / exit             : Arrêter toute la flotte et quitter")
                print(chalk.cyan("=" * 60))
                print()
                continue

            # Déclenchement de la patrouille territoriale globale
            if lower in ("fleet patrol", "patrouille flotte"):
                for bot in self.bots.values():
                    if bot.is_alive() and bot.district:
                        bot.send_command(f"patrouille {bot.district}")
                print(chalk.green("✓ Patrouilles sectorielles lancées pour tous les patrouilleurs."))
                continue

            # Démarrage ou arrêt unitaire
            if lower.startswith("start "):
                target_name = cmd[len("start "):].strip()
                bot = self.bots.get(target_name)
                if bot:
                    bot.start()
                    print(chalk.green(f"✓ Démarrage de {target_name}..."))
                else:
                    print(chalk.red(f"Bot '{target_name}' inconnu."))
                continue

            if lower.startswith("stop "):
                target_name = cmd[len("stop "):].strip()
                bot = self.bots.get(target_name)
                if bot:
                    bot.stop()
                else:
                    print(chalk.red(f"Bot '{target_name}' inconnu."))
                continue

            # Routage par préfixe 'all: <commande>' ou '!all <commande>'
            if lower.startswith("all: ") or lower.startswith("!all "):
                sub_cmd = cmd.split(" ", 1)[1].strip()
                self.broadcast(sub_cmd)
                continue

            # Routage par préfixe '<nom>: <commande>' ou '!<nom> <commande>'
            targeted = False
            for name in self.bots:
                prefix1 = f"{name.lower()}: "
                prefix2 = f"!{name.lower()} "
                if lower.startswith(prefix1) or lower.startswith(prefix2):
                    sub_cmd = cmd.split(" ", 1)[1].strip()
                    self.send_to(name, sub_cmd)
                    targeted = True
                    break

            if targeted:
                continue

            # Par défaut, transmettre l'ordre au bot leader s'il existe
            leader = next(
                (b for b in self.bots.values() if b.role == "leader"),
                None,
            )
            if leader and leader.is_alive():
                leader.send_command(cmd)
            else:
                print(
                    chalk.yellow(
                        "Commande non reconnue. Utilisez 'all: <action>', '<nom>: <action>' ou 'help'."
                    )
                )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    try:
        from utils.bot_selector import select_bots
    except ImportError:
        from scripts.utils.bot_selector import select_bots

    selected = select_bots()
    manager = BotManager(fleet_config=selected)
    manager.start_fleet()
    manager.terminal_loop()

