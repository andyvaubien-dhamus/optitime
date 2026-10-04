import os
import sys
from pathlib import Path

# --- DÉTECTION DU DOSSIER D'EXÉCUTION (Compatible PyInstaller / Portable) ---
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).resolve().parent.parent

APP_DATA_DIR = APP_ROOT / "OptiTimeData"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- CHEMINS DE PERSISTANCE ---
DB_FILE = APP_DATA_DIR / "optitime.db"
CSV_FILE_OLD = APP_DATA_DIR / "historique.csv"
CONFIG_FILE = APP_DATA_DIR / "config.json"
MEMO_FILE = APP_DATA_DIR / "memo.txt"
GAME_FILE = APP_DATA_DIR / "game_data.json"
ASSETS_DIR = APP_ROOT / "assets"

# --- CONFIGURATION PAR DÉFAUT ---
DEFAULT_CONFIG = {
    "objectif_h": 7.0,
    "franchise_min": 30,
    "activites": ["Administration", "Production", "Réunion", "Formation", "Pause Déj", "Autre"],
    "dashboard_widgets": ["kpi_total", "kpi_solde", "kpi_banque", "kpi_pause", "chart_evol", "chart_repart", "mail_rh"]
}

# --- BASES DE DONNÉES GAMIFICATION ---
SKINS_DB = {
    "Classique": {"wake": "😐", "happy": "🙂", "perfect": "😎", "sleep": "😴"},
    "Pixel":     {"wake": "👾", "happy": "🕹️", "perfect": "👑", "sleep": "💾"},
    "Animaux":   {"wake": "🐱", "happy": "🦊", "perfect": "🦁", "sleep": "🐨"},
    "Chronos":   {"wake": "⏳", "happy": "⚡", "perfect": "🔮", "sleep": "🌌"},
    "M█████":    {"wake": "🕶️", "happy": "💊", "perfect": "🔫", "sleep": "🔌"}
}

QUOTES_DB = {
    "Stoïcisme": [
        {"text": "Ce qui dépend de nous est libre.", "author": "Épictète"},
        {"text": "La vie n'est pas courte, c'est nous qui la perdons.", "author": "Sénèque"},
        {"text": "L'obstacle est le chemin.", "author": "Marc Aurèle"},
        {"text": "Le bonheur ne dépend que de nous.", "author": "Aristote"},
        {"text": "Hâte-toi de bien vivre.", "author": "Sénèque"},
        {"text": "L'homme le plus puissant est celui qui est maître de lui-même.", "author": "Sénèque"},
        {"text": "Le temps est la chose la plus précieuse qu'un homme puisse dépenser.", "author": "Théophraste"},
        {"text": "Le calme est la plus grande des forces.", "author": "Sénèque"}
    ],
    "Cinéma": [
        {"text": "Que la force soit avec toi.", "author": "Star Wars"},
        {"text": "Fais-le, ou ne le fais pas. Il n'y a pas d'essai.", "author": "Yoda"},
        {"text": "Vers l'infini et au-delà !", "author": "Toy Story"},
        {"text": "Pourquoi tombons-nous ? Pour mieux apprendre à nous relever.", "author": "Batman Begins"},
        {"text": "Carpe Diem. Saisissez le jour présent.", "author": "Le Cercle des Poètes Disparus"},
        {"text": "Tout ce que nous avons à décider, c'est quoi faire du temps qui nous est imparti.", "author": "Le Seigneur des Anneaux"}
    ],
    "Sport": [
        {"text": "Ils ne savaient pas que c'était impossible, alors ils l'ont fait.", "author": "Mark Twain"},
        {"text": "Tu rates 100% des tirs que tu ne tentes pas.", "author": "Wayne Gretzky"},
        {"text": "La douleur est temporaire. L'abandon est définitif.", "author": "Lance Armstrong"},
        {"text": "Je ne perds jamais. Soit je gagne, soit j'apprends.", "author": "Nelson Mandela"},
        {"text": "Le talent gagne des matchs, mais le travail d'équipe gagne des championnats.", "author": "Michael Jordan"}
    ],
    "Proverbes Zen": [
        {"text": "Le voyage de mille lieues commence par un pas.", "author": "Lao Tseu"},
        {"text": "L'eau qui coule ne stagne jamais.", "author": "Proverbe"},
        {"text": "Le silence est un ami qui ne trahit jamais.", "author": "Confucius"},
        {"text": "Hier est de l'histoire, demain est un mystère.", "author": "Zen"},
        {"text": "Sois comme le bambou : plie mais ne romps pas.", "author": "Proverbe"}
    ],
    "M█████": [
        {"text": "Libère ton esprit.", "author": "M."},
        {"text": "Je ne peux que te montrer la porte. C'est toi qui dois la franchir.", "author": "M."},
        {"text": "Il y a une différence entre connaître le chemin et parcourir le chemin.", "author": "M."},
        {"text": "Tout ce qui a un début a une fin.", "author": "L'Oracle"},
        {"text": "Prends la pilule rouge.", "author": "M."}
    ]
}

# --- CATALOGUE COMPLET DE RÉCUPÉRATION ---
CATALOGUE_RECUPS = [
    {"id": "r1", "cat": "Régénération", "title": "Réveil Visage", "icon": "✨", "img": "reveil_visage.png", "desc": "Massage doux du contour des yeux et des tempes.", "keywords": ["visage", "yeux", "front", "fatigue"]},
    {"id": "r2", "cat": "Régénération", "title": "Point Antistress", "icon": "🤏", "img": "point_antistress.png", "desc": "Massez le point entre le pouce et l'index.", "keywords": ["stress", "tension", "angoisse", "calme"]},
    {"id": "r3", "cat": "Régénération", "title": "Massage Crânien", "icon": "💆", "img": "massage_crane.png", "desc": "Mouvements circulaires sur le cuir chevelu.", "keywords": ["crane", "tete", "cerveau", "migraine"]},
    {"id": "r4", "cat": "Régénération", "title": "Lissage Front", "icon": "😌", "img": "lissage_front.png", "desc": "Lissage du centre vers les tempes.", "keywords": ["front", "yeux", "concentration"]},
    {"id": "m1", "cat": "Mouvements", "title": "Le Chat Assis", "icon": "🐈", "img": "chat_assis.png", "desc": "Dos rond / Dos creux sur chaise.", "keywords": ["dos", "colonne", "chaise", "lombaire"]},
    {"id": "m2", "cat": "Mouvements", "title": "Libération Poignets", "icon": "👋", "img": "liberation_poignets.png", "desc": "Étirements des poignets et fléchisseurs.", "keywords": ["poignets", "mains", "clavier", "souris"]},
    {"id": "m3", "cat": "Mouvements", "title": "Torsion Assise", "icon": "🌪️", "img": "torsion_assise.png", "desc": "Rotation douce du buste.", "keywords": ["dos", "torsion", "buste", "raideur"]},
    {"id": "m4", "cat": "Mouvements", "title": "Étirement Nuque", "icon": "📐", "img": "etirement_nuque.png", "desc": "Inclinaison latérale douce.", "keywords": ["nuque", "cou", "cervicales", "epaule"]},
    {"id": "e1", "cat": "Ergonomie", "title": "Check Yeux", "icon": "👀", "img": "ergo_yeux.png", "desc": "Regard aligné au haut de l'écran.", "keywords": ["yeux", "ecran", "hauteur", "vision"]},
    {"id": "e2", "cat": "Ergonomie", "title": "Check Dos", "icon": "🪑", "img": "ergo_dos.png", "desc": "Dos bien calé au dossier.", "keywords": ["dos", "posture", "chaise", "fauteuil"]},
    {"id": "e3", "cat": "Ergonomie", "title": "Check Bras", "icon": "📐", "img": "ergo_coudes.png", "desc": "Coudes à 90 degrés.", "keywords": ["bras", "coudes", "hauteur"]},
    {"id": "e4", "cat": "Ergonomie", "title": "Check Écran", "icon": "🖥️", "img": "ergo_ecran.png", "desc": "Distance d'un bras minimum.", "keywords": ["ecran", "distance", "yeux"]},
    {"id": "s1", "cat": "Essentiels", "title": "Cohérence Cardiaque", "icon": "❤️", "img": "coherence.png", "desc": "Respiration rythmée 5s inspiration / 5s expiration.", "keywords": ["stress", "coeur", "respiration", "calme"]},
    {"id": "s2", "cat": "Essentiels", "title": "Hydratation", "icon": "💧", "img": "hydratation.png", "desc": "Boire un grand verre d'eau fraîche.", "keywords": ["eau", "soif", "fatigue", "energie"]},
    {"id": "s3", "cat": "Essentiels", "title": "Regard au Loin", "icon": "🔭", "img": "regard_loin.png", "desc": "Fixer un point à 6m (20s).", "keywords": ["yeux", "vue", "fatigue", "vision"]},
    {"id": "s4", "cat": "Essentiels", "title": "Respiration Ventrale", "icon": "🎈", "img": "respiration_ventre.png", "desc": "Respirer profondément par le ventre.", "keywords": ["ventre", "respiration", "detente"]}
]

# --- LISTE DES TROPHÉES ---
LISTE_TROPHEES = [
    {"id": "welcome", "name": "👋 Bienvenue à Bord", "desc_mission": "Initialiser votre première journée de travail.", "condition": "days", "target": 1, "xp": 100, "skin_unlock": None, "pack_unlock": None},
    {"id": "streak_3", "name": "🔥 On s'échauffe", "desc_mission": "Maintenir une série de 3 jours consécutifs.", "condition": "streak", "target": 3, "xp": 200, "skin_unlock": None, "pack_unlock": "Proverbes Zen"},
    {"id": "pauses_10", "name": "🧘 Maître Zen", "desc_mission": "Prendre 10 pauses actives.", "condition": "pauses", "target": 10, "xp": 300, "skin_unlock": "Animaux", "pack_unlock": None},
    {"id": "hours_50", "name": "💻 Bosseur Pixelisé", "desc_mission": "Cumuler 50 heures de focus.", "condition": "hours", "target": 50, "xp": 400, "skin_unlock": "Pixel", "pack_unlock": None},
    {"id": "days_10", "name": "🎬 Cinéphile", "desc_mission": "Utiliser l'application pendant 10 jours.", "condition": "days", "target": 10, "xp": 400, "skin_unlock": None, "pack_unlock": "Cinéma"},
    {"id": "days_20", "name": "🏅 Champion Olympique", "desc_mission": "Atteindre 20 jours d'utilisation.", "condition": "days", "target": 20, "xp": 600, "skin_unlock": None, "pack_unlock": "Sport"},
    {"id": "legend_prime", "name": "🕶️ [PROTOCOLE INCONNU]", "desc_mission": "Synchronisation Ultime (Séquence S) : 2000 XP + Série de 30 jours.", "condition": "special_s", "target": 2000, "xp": 1000, "skin_unlock": "M█████", "pack_unlock": "M█████", "theme_unlock": "Système_S"}
]