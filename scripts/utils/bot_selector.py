# ============================================================
# LIBRARIES
# ============================================================

import os
import re
import sys
from simple_chalk import chalk


# ============================================================
# CONFIGURATION PAR DÉFAUT DES BOTS
# ============================================================

DEFAULT_BOT_CONFIG = [
    {
        "id": "1",
        "name": "Moisurunautrecom",
        "role": "leader",
        "port": 3000,
        "district": "Haute ville",
        "console": True,
    },
    {
        "id": "2",
        "name": "nThArOs",
        "role": "patrol",
        "port": 3001,
        "district": "place george orwell",
        "console": False,
    },
]


# ============================================================
# RÉCUPÉRATION DE LA LISTE DES BOTS
# ============================================================

def get_available_bots():
    """Récupère la liste ordonnée des bots configurés pour la flotte.

    Tente d'importer FLEET_CONFIG depuis config.fleet, ou utilise la
    configuration par défaut avec Moisurunautrecom et nThArOs.
    """
    try:
        from config.fleet import FLEET_CONFIG

        bots = []
        for idx, item in enumerate(FLEET_CONFIG, 1):
            entry = dict(item)
            entry["id"] = str(idx)
            if "console" not in entry:
                entry["console"] = (idx == 1)
            bots.append(entry)
        return bots
    except Exception:
        return [dict(b) for b in DEFAULT_BOT_CONFIG]


# ============================================================
# PARSING DE LA SÉLECTION UTILISATEUR
# ============================================================

def parse_bot_selection(raw_input, available_bots=None, default_id="1"):
    """Interprète le choix saisi par l'utilisateur et renvoie les bots choisis.

    Prend en charge :
      - Un numéro unique : '1' ou '2'
      - Plusieurs numéros : '1,2', '1 2', '1;2', '1 et 2'
      - Mots-clés universels : '3', 'all', 'tous', '*', 'both'
      - Noms directs de bots (insensible à la casse) : 'Moisurunautrecom', 'nThArOs'
      - Saisie vide : sélection du bot par défaut
    """
    bots = available_bots if available_bots is not None else get_available_bots()
    if not bots:
        return []

    text = (raw_input or "").strip().lower()

    # Saisie vide -> choix par défaut
    if not text:
        default_bot = next(
            (b for b in bots if b.get("id") == str(default_id)),
            bots[0],
        )
        return [dict(default_bot)]

    # Mots-clés pour sélectionner tous les bots
    all_keywords = ("all", "tous", "both", "*", "tous les bots")
    all_numeric_id = str(len(bots) + 1)
    if text in all_keywords or text == all_numeric_id:
        return [dict(b) for b in bots]

    # Normalisation des séparateurs (virgules, points-virgules, 'et', espaces)
    normalized = re.sub(r"[,;+&]|(\bet\b)", " ", text)
    tokens = [tok.strip() for tok in normalized.split() if tok.strip()]

    selected = []
    selected_names = set()

    for token in tokens:
        matched = False

        # Vérification par ID numérique ('1', '2', etc.)
        for bot in bots:
            if bot.get("id") == token:
                if bot["name"] not in selected_names:
                    selected.append(dict(bot))
                    selected_names.add(bot["name"])
                matched = True
                break

        if matched:
            continue

        # Vérification par mot-clé global dans un token ('all')
        if token in all_keywords or token == all_numeric_id:
            for bot in bots:
                if bot["name"] not in selected_names:
                    selected.append(dict(bot))
                    selected_names.add(bot["name"])
            matched = True
            continue

        # Vérification par nom de bot (insensible à la casse)
        for bot in bots:
            if bot["name"].lower() == token:
                if bot["name"] not in selected_names:
                    selected.append(dict(bot))
                    selected_names.add(bot["name"])
                matched = True
                break

    # Si rien n'a pu être interprété, repli sur le bot par défaut
    if not selected:
        default_bot = next(
            (b for b in bots if b.get("id") == str(default_id)),
            bots[0],
        )
        return [dict(default_bot)]

    return selected


# ============================================================
# INTERFACE UTILISATEUR & PROMPT TERMINAL
# ============================================================

def prompt_bot_selection(available_bots=None, default_id="1"):
    """Affiche le menu interactif dans le terminal et lit la sélection."""
    bots = available_bots if available_bots is not None else get_available_bots()

    print()
    print(chalk.cyan("=" * 60))
    print(chalk.cyanBright(" SÉLECTION DES BOTS MINECRAFT (mc_wati_bot)"))
    print(chalk.cyan("=" * 60))
    print(chalk.white("Choisissez le(s) bot(s) à démarrer :"))

    for bot in bots:
        b_id = bot.get("id", "?")
        b_name = bot.get("name", "Inconnu")
        b_role = bot.get("role", "patrol")
        b_port = bot.get("port", 3000)
        role_label = (
            chalk.green(f"({b_role})")
            if b_role == "leader"
            else chalk.cyan(f"({b_role})")
        )
        print(
            f"  [{chalk.bold(b_id)}] {chalk.bold(b_name):<20} "
            f"{role_label:<18} {chalk.gray(f'Port web :{b_port}')}"
        )

    all_idx = str(len(bots) + 1)
    all_names = " + ".join(b["name"] for b in bots)
    print(
        f"  [{chalk.bold(all_idx)}] {chalk.bold('Tous les bots'):<20} "
        f"{chalk.magenta('(multi-instances)'):<18} {chalk.gray(all_names)}"
    )

    print(chalk.cyan("=" * 60))
    print(
        chalk.gray(
            f"Exemples : '1' (Moisurunautrecom), '2' (nThArOs), "
            f"'1,2' ou '{all_idx}' (Tous)"
        )
    )

    try:
        prompt_str = chalk.yellow(f"Votre choix [défaut: {default_id}] > ")
        user_input = input(prompt_str).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        user_input = default_id

    selected = parse_bot_selection(user_input, bots, default_id=default_id)
    return selected


# ============================================================
# SÉLECTION AUTOMATIQUE OU INTERACTIVE
# ============================================================

def select_bots(available_bots=None, default_id="1"):
    """Point d'entrée principal pour sélectionner les bots.

    Détecte automatiquement si des variables d'environnement (SELECTED_BOTS, BOT_NAME)
    sont fournies, ou si le terminal est non interactif pour éviter de bloquer.
    """
    bots = available_bots if available_bots is not None else get_available_bots()

    # 1. Variable d'environnement prioritaire SELECTED_BOTS (ex: '1,2' ou 'all')
    env_selected = os.getenv("SELECTED_BOTS")
    if env_selected:
        return parse_bot_selection(env_selected, bots, default_id=default_id)

    # 2. Variable BOT_NAME unitaire
    env_bot_name = os.getenv("BOT_NAME")
    if env_bot_name:
        for b in bots:
            if b["name"].lower() == env_bot_name.lower():
                return [dict(b)]
        return [{
            "id": "1",
            "name": env_bot_name,
            "role": os.getenv("BOT_ROLE", "leader"),
            "port": int(os.getenv("WEB_INVENTORY_PORT", "3000")),
            "console": True,
            "district": os.getenv("ASSIGNED_DISTRICT", ""),
        }]

    # 3. Mode non-interactif (tests unitaires ou pipe sans tty)
    if not sys.stdin or not sys.stdin.isatty():
        return parse_bot_selection("", bots, default_id=default_id)

    # 4. Mode interactif standard
    return prompt_bot_selection(bots, default_id=default_id)
