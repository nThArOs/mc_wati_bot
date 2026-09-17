# ============================================================
# DONNÉES DU MONDE : points d'intérêt, quartiers, graphe de
# navigation entre les points.
# ============================================================

POINTS_INTERET = {
    "usine a fer": (1690, 132, -1145),

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

    "horloge": (1746, 95, -1418),
    "river": (1796, 101, -1448),
    "intersection 1": (1796, 104, -1419),
    "church": (1822, 112, -1413),
    "intersection 2": (1820, 119, -1388),
    "bourdieu-cathedral": (1820, 119, -1388),

    "cathedral": (1776, 129, -1328),
    
    "nether sand dupe": (183, 114, -621),
    "nether raid 2": (-226, 114, -478),
    "nether creeper 2": (248, 114, -297),
    
}

QUARTIERS = {
    "Haute ville": ["usine a fer", "route 1", "route 2", "route 3", "route 4", "salle des coffres", "arc de triomphe"],
    "place george orwell": ["george orwell", "place gauche", "place haute", "place droite", "parc"],
    "quartier du theatre": ["theatre","palace","palais"],
    "quartier pierre bourdieu": ["horloge", "intersection 1","river", "church", "intersection 2"],
    "quartier de la cathedrale": ["cathedral", "droite","parvis","gauche"],
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
