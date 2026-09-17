from simple_chalk import chalk
from config import DELIVERY_DESTINATION, CHEST_SEARCH_RADIUS
from points import POINTS_INTERET, GRAPH
import threading


# ============================================================
# LIVRAISON
#
# Mixin pour MCBot (voir bot.py).
#
# livraison <point> : va vider le coffre le plus proche du
# point donné, puis va tout déposer dans le coffre le plus
# proche de DELIVERY_DESTINATION. Repose sur MovementMixin
# (travel_to_and_wait) pour les trajets.
# ============================================================

class ChestMixin:

    def find_nearby_chest(self):
        try:
            def is_chest(block):
                return block and block.name in ("chest", "trapped_chest")

            return self.bot.findBlock({
                "matching": is_chest,
                "maxDistance": CHEST_SEARCH_RADIUS,
            })

        except Exception as e:
            self.log(
                chalk.red(f"Recherche de coffre erreur : {e}")
            )
            return None


    def empty_nearby_chest(self):
        block = self.find_nearby_chest()

        if not block:
            self.log(
                chalk.red("Aucun coffre trouvé à proximité.")
            )
            return None

        try:
            chest = self.bot.openChest(block)
        except Exception as e:
            self.log(
                chalk.red(f"Impossible d'ouvrir le coffre : {e}")
            )
            return None

        taken = []

        try:
            items = list(chest.containerItems())

            for item in items:
                try:
                    chest.withdraw(
                        item.type,
                        item.metadata,
                        item.count,
                        item.nbt,
                    )

                    taken.append({
                        "type": item.type,
                        "metadata": item.metadata,
                        "count": item.count,
                        "nbt": item.nbt,
                        "name": item.name,
                    })

                except Exception as e:
                    self.log(
                        chalk.red(
                            f"Erreur en prenant {item.name} : {e}"
                        )
                    )

        finally:
            try:
                chest.close()
            except Exception:
                pass

        return taken


    def deposit_into_nearby_chest(self, items):
        block = self.find_nearby_chest()

        if not block:
            self.log(
                chalk.red("Aucun coffre trouvé à proximité.")
            )
            return False

        try:
            chest = self.bot.openChest(block)
        except Exception as e:
            self.log(
                chalk.red(f"Impossible d'ouvrir le coffre : {e}")
            )
            return False

        try:
            for item in items:
                try:
                    chest.deposit(
                        item["type"],
                        item["metadata"],
                        item["count"],
                        item["nbt"],
                    )

                except Exception as e:
                    self.log(
                        chalk.red(
                            f"Erreur en déposant {item['name']} : {e}"
                        )
                    )

        finally:
            try:
                chest.close()
            except Exception:
                pass

        return True


    def start_delivery(self, source_point):
        source_point = source_point.strip().lower()

        if not source_point:
            self.log(
                chalk.yellow("Point de départ manquant.")
            )
            self.chat("Depuis quel point je dois livrer ? (livraison <point>)")
            return False

        if source_point not in POINTS_INTERET or source_point not in GRAPH:
            self.log(
                chalk.red(f"Point inconnu du graphe : {source_point}")
            )
            self.chat("Je ne connais pas ce point dans mon graphe.")
            return False

        if self.patrol_active:
            self.chat("Je suis déjà en mouvement, tape 'stop' d'abord.")
            return False

        def worker():
            self.log(
                chalk.cyan(
                    f"Livraison : {source_point} → {DELIVERY_DESTINATION}"
                )
            )
            self.chat(f"Je vais chercher les objets à {source_point}.")

            if not self.travel_to_and_wait(source_point):
                self.log(
                    chalk.red(f"Je n'ai pas réussi à atteindre {source_point}.")
                )
                self.chat("Je n'arrive pas à destination, livraison annulée.")
                return

            items = self.empty_nearby_chest()

            if items is None:
                self.chat("Je n'ai pas trouvé de coffre ici, livraison annulée.")
                return

            if not items:
                self.chat("Le coffre était vide, rien à livrer.")
                return

            self.log(
                chalk.cyan(
                    f"{len(items)} pile(s) récupérée(s), "
                    f"direction {DELIVERY_DESTINATION}."
                )
            )
            self.chat(
                f"J'ai récupéré {len(items)} pile(s), "
                f"je ramène ça à {DELIVERY_DESTINATION}."
            )

            if not self.travel_to_and_wait(DELIVERY_DESTINATION):
                self.log(
                    chalk.red(
                        f"Je n'ai pas réussi à atteindre {DELIVERY_DESTINATION}."
                    )
                )
                self.chat("Je n'arrive pas à la salle des coffres avec le chargement.")
                return

            if self.deposit_into_nearby_chest(items):
                self.log(chalk.green("✓ Livraison terminée."))
                self.chat("Livraison terminée !")
            else:
                self.chat("Je n'ai pas trouvé de coffre pour déposer les objets.")

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

        return True
