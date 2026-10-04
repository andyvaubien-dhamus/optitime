import os
import sys
import json
import pandas as pd
from datetime import datetime, time, timedelta
from .constants import (
    CONFIG_FILE, GAME_FILE, MEMO_FILE, DEFAULT_CONFIG,
    LISTE_TROPHEES, SKINS_DB
)

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def calculate_duration(t_start, t_end, pause_min, franchise_min=0):
    if pd.isna(t_start) or pd.isna(t_end): return 0.0
    dummy_date = datetime.min.date()
    if isinstance(t_start, str):
        try: t_start = datetime.strptime(str(t_start)[0:5], "%H:%M").time()
        except: t_start = time(0,0)
    elif hasattr(t_start, 'time'):
        try: t_start = t_start.time()
        except: return 0.0
        
    if isinstance(t_end, str):
        try: t_end = datetime.strptime(str(t_end)[0:5], "%H:%M").time()
        except: t_end = time(0,0)
    elif hasattr(t_end, 'time'):
        try: t_end = t_end.time()
        except: return 0.0

    if not t_start or not t_end: return 0.0
    dt_start = datetime.combine(dummy_date, t_start)
    dt_end = datetime.combine(dummy_date, t_end)
    if dt_end < dt_start: dt_end += timedelta(days=1)
    duration_minutes = (dt_end - dt_start).total_seconds() / 60.0
    effective_minutes = duration_minutes - max(0, pause_min - franchise_min)
    return max(0.0, round(effective_minutes / 60.0, 2))

def load_config():
    if not os.path.exists(CONFIG_FILE): return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, indent=4)

def load_game_data():
    default_game = {
        "xp": 0, "vitality_ener": 0, "level": 1, "unlocked": ["Classique"],
        "achievements_unlocked": [],
        "theme_system_s_unlocked": False,
        "theme_prime_enabled": True,
        "current": {"skin": "Classique", "pack": "Stoïcisme"},
        "inventory": {"joker_coffe": 0, "machine_time": 0, "streak_fixer": 0},
        "last_active_day": None,
        "counters": {"days_logged": 0, "pauses_clicked": 0, "total_hours": 0.0, "streak_current": 0}
    }
    if not os.path.exists(GAME_FILE): return default_game
    try:
        with open(GAME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_game.items():
                if k not in data: data[k] = v
            for subk, subv in default_game["inventory"].items():
                if subk not in data["inventory"]: data["inventory"][subk] = subv
            return sync_xp_from_achievements(data)
    except: return default_game

def save_game_data(data):
    with open(GAME_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

def update_streak_logic(game_data):
    today = datetime.now().date()
    last_date_str = game_data.get("last_active_day")
    updated = False

    if last_date_str:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        diff = (today - last_date).days
        if diff >= 1:
            if diff == 1:
                game_data["counters"]["streak_current"] += 1
            else:
                gels = game_data.get("inventory", {}).get("streak_fixer", 0)
                if gels > 0:
                    game_data["inventory"]["streak_fixer"] -= 1
                else:
                    game_data["counters"]["streak_current"] = 1
            updated = True
    else:
        game_data["counters"]["streak_current"] = 1
        updated = True

    game_data["last_active_day"] = str(today)
    return game_data, updated

def sync_xp_from_achievements(game_data):
    unlocked_ids = game_data.get("achievements_unlocked", [])
    total_xp = 0
    for trophy in LISTE_TROPHEES:
        if trophy["id"] in unlocked_ids: total_xp += trophy.get("xp", 0)
    game_data["xp"] = total_xp
    return game_data

def check_achievements(game_data):
    updated = False
    cnt = game_data["counters"]
    my_achievements = game_data.get("achievements_unlocked", [])
    my_unlocks = game_data.get("unlocked", [])
    game_data = sync_xp_from_achievements(game_data)
    current_xp = game_data["xp"]
    current_streak = cnt.get("streak_current", 0)

    for trophy in LISTE_TROPHEES:
        if trophy["id"] in my_achievements: continue
        condition_met = False
        if trophy["condition"] == "days" and cnt["days_logged"] >= trophy["target"]:
            condition_met = True
        elif trophy["condition"] == "streak" and current_streak >= trophy["target"]:
            condition_met = True
        elif trophy["condition"] == "pauses" and cnt["pauses_clicked"] >= trophy["target"]:
            condition_met = True
        elif trophy["condition"] == "hours" and cnt["total_hours"] >= trophy["target"]:
            condition_met = True
        elif trophy["condition"] == "special_s":
            if current_xp >= 2000 and current_streak >= 30:
                condition_met = True

        if condition_met:
            my_achievements.append(trophy["id"])
            if trophy.get("skin_unlock") and trophy["skin_unlock"] not in my_unlocks:
                my_unlocks.append(trophy["skin_unlock"])
            updated = True

    if game_data["xp"] >= 3000:
        if not game_data.get("theme_system_s_unlocked", False):
            game_data["theme_system_s_unlocked"] = True
            updated = True

    if updated:
        game_data["achievements_unlocked"] = my_achievements
        game_data["unlocked"] = my_unlocks
        save_game_data(game_data)
    return game_data

def get_optigotchi_status(total_h, pause_m, objectif, skin_name, game_data=None):
    skin_assets = SKINS_DB.get(skin_name, SKINS_DB["Classique"])
    ratio = total_h / objectif if objectif > 0 else 0
    if ratio >= 1.0: return skin_assets["perfect"], "Objectif atteint !", "#D1FAE5", "#10B981", "happy"
    elif ratio >= 0.5: return skin_assets["happy"], "En bonne voie !", "#DBEAFE", "#3B82F6", "focus"
    else: return skin_assets["sleep"], "En attente...", "#F3F4F6", "#9CA3AF", "sleep"

def load_memo():
    if os.path.exists(MEMO_FILE):
        with open(MEMO_FILE, "r", encoding="utf-8") as f: return f.read()
    return ""

def save_memo(text):
    with open(MEMO_FILE, "w", encoding="utf-8") as f: f.write(text)

def clear_memo():
    if os.path.exists(MEMO_FILE): os.remove(MEMO_FILE)