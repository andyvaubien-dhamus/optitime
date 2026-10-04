# ==========================================
# FICHIER : app.py (V13.6 - RESTAURATION COMPLÈTE & OPTIMISÉE)
# ==========================================
import streamlit as st
import pandas as pd
import io
from datetime import datetime, time, timedelta
import json
import os
import sys
import time as tm
import random
import base64
from PIL import Image
import textwrap

# --- 1. FONCTIONS SYSTÈME & LOGIQUE DE SAUVEGARDE ---
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def finaliser_session(duree, activite, commentaire):
    """Enregistre l'entrée et réinitialise le timer pour clore la journée."""
    save_entry_db({
        "Date": pd.to_datetime(datetime.now().date()),
        "Arrivée": st.session_state.timer_start_dt.strftime("%H:%M"),
        "Départ": datetime.now().strftime("%H:%M"),
        "Pause": 0, "Activité": activite, "Commentaire": commentaire,
        "Effectif_h": duree, "Solde_h": 0
    })
    st.session_state.timer_active = False
    st.session_state.show_cloture = False
    st.session_state.df = load_data_db()
    st.rerun()

# --- 2. MODALS DE NAVIGATION (PLUG-INS) ---
@st.dialog("🎯 Bilan de session", width="medium")
def modal_cloture_intelligente():
    d_sess = st.session_state.get("temp_eff", 0)
    t_jour = st.session_state.get("temp_total", 0)
    act_acc = st.session_state.timer_activity
    obj = st.session_state.config.get("objectif_h", 7.0)
    
    st.info(f"Cumul journée : **{t_jour:.2f}h** / {obj}h")
    
    st.markdown("### 🚀 Continuer le travail")
    st.caption("Terminer ce segment et changer de tâche :")
    liste_act = st.session_state.config["activites"]
    n_act = st.selectbox("Nouvelle activité", options=liste_act, key="pivot_modal")
    
    if st.button("VALIDER ET ENCHAÎNER", type="primary", use_container_width=True):
        save_entry_db({
            "Date": pd.to_datetime(datetime.now().date()), 
            "Arrivée": st.session_state.timer_start_dt.strftime("%H:%M"), 
            "Départ": datetime.now().strftime("%H:%M"), 
            "Pause": 0, "Activité": act_acc, "Commentaire": "Segment terminé", 
            "Effectif_h": d_sess, "Solde_h": 0
        })
        st.session_state.timer_start_dt = datetime.now()
        st.session_state.timer_activity = n_act
        st.session_state.timer_active = True
        st.session_state.show_cloture = False
        st.rerun()
        
    st.divider()
    st.markdown("### 🛑 Clôturer la journée")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📉 DÉFICIT", use_container_width=True): 
            finaliser_session(d_sess, act_acc, "Déficit accepté")
    with c2:
        comp = max(0.0, obj - t_jour)
        if st.button(f"🤖 ADMIN (+{comp:.2f}h)", use_container_width=True, type="secondary"): 
            finaliser_session(d_sess + comp, "Administration", "Complété automatiquement")

@st.dialog("🏪 Pause Active", width="large")
def pause_modal():
    it = st.session_state.get("current_pause")
    if it:
        st.subheader(f"{it['icon']} {it['title']}")
        st.info(it['desc'])
        p = get_resource_path(os.path.join("assets", "exercices", it["img"]))
        if os.path.exists(p): st.image(p)
    if st.button("✅ VALIDER (+15 ⚡)", type="primary", use_container_width=True):
        st.session_state.game["vitality_ener"] += 15
        st.session_state.game["counters"]["pauses_clicked"] += 1
        save_game_data(check_achievements(st.session_state.game))
        st.session_state.pause_mode = False
        st.rerun()

@st.dialog("🌀 Vortex Temporel", width="medium")
def vortex_modal():
    st.write("### 🌀 Réparation de Série")
    st.info("Utilisez cette relique pour rattraper une absence passée et restaurer votre série.")
    if st.button("ACQUÉRIR RELIQUE (-300 ⚡)", type="primary", use_container_width=True):
        if st.session_state.game["vitality_ener"] >= 300:
            st.session_state.game["vitality_ener"] -= 300
            st.session_state.game["inventory"]["streak_fixer"] += 1
            save_game_data(st.session_state.game)
            st.session_state.vortex_mode = False
            st.success("Relique ajoutée !")
            tm.sleep(1); st.rerun()
        else: st.error("Énergie insuffisante !")

# --- 3. CONFIGURATION & INITIALISATION ---
st.set_page_config(page_title="OptiTime V13.6", page_icon="⏱️", layout="wide")

from modules.constants import CONFIG_FILE, GAME_FILE, QUOTES_DB, SKINS_DB, LISTE_TROPHEES
from modules.database import init_db, load_data_db, save_entry_db, update_db_from_df
from modules.utils import (
    load_config, save_config, load_game_data, save_game_data, 
    check_achievements, load_memo, save_memo, clear_memo,
    get_optigotchi_status, check_and_import_csv, 
    sync_xp_from_achievements, calculate_duration
)

check_and_import_csv()
if 'db_init' not in st.session_state: 
    init_db()
    st.session_state.db_init = True

for key, val in {
    'config': load_config(), 'df': load_data_db(), 'app_ready': False,
    'timer_active': False, 'pause_mode': False, 'vortex_mode': False, 
    'show_cloture': False, 'animation_style': "ECG Code-Source"
}.items():
    if key not in st.session_state: st.session_state[key] = val

if 'game' not in st.session_state:
    data = load_game_data()
    defaults = {
        "counters": {"total_hours": 0, "streak_current": 0, "days_logged": 0, "pauses_clicked": 0},
        "current": {"skin": "Classique", "pack": "Stoïcisme"},
        "inventory": {"joker_coffe": 0, "machine_time": 0, "streak_fixer": 0},
        "vitality_ener": 0, "xp": 0, "achievements_unlocked": [],
        "theme_system_s_unlocked": False, "theme_prime_enabled": True
    }
    for k, v in defaults.items():
        if k not in data: data[k] = v
    for subk, subv in defaults["inventory"].items():
        if subk not in data["inventory"]: data["inventory"][subk] = subv
    st.session_state.game = sync_xp_from_achievements(data)

# --- 4. CATALOGUE & STYLES ---
CATALOGUE_RECUPS = [
    {"id": "r1", "cat": "Régénération", "title": "Réveil Visage", "icon": "✨", "img": "reveil_visage.png", "desc": "Massage doux du contour des yeux."},
    {"id": "r2", "cat": "Régénération", "title": "Point Antistress", "icon": "🤏", "img": "point_antistress.png", "desc": "Massez le point entre le pouce et l'index."},
    {"id": "r3", "cat": "Régénération", "title": "Massage Crânien", "icon": "💆", "img": "massage_crane.png", "desc": "Mouvements circulaires sur le cuir chevelu."},
    {"id": "r4", "cat": "Régénération", "title": "Lissage Front", "icon": "😌", "img": "lissage_front.png", "desc": "Lissage du centre vers les tempes."},
    {"id": "m1", "cat": "Mouvements", "title": "Le Chat Assis", "icon": "🐈", "img": "chat_assis.png", "desc": "Dos rond / Dos creux sur chaise."},
    {"id": "m2", "cat": "Mouvements", "title": "Libération Poignets", "icon": "👋", "img": "liberation_poignets.png", "desc": "Étirements des poignets."},
    {"id": "m3", "cat": "Mouvements", "title": "Torsion Assise", "icon": "🌪️", "img": "torsion_assise.png", "desc": "Rotation douce du buste."},
    {"id": "m4", "cat": "Mouvements", "title": "Étirement Nuque", "icon": "📐", "img": "etirement_nuque.png", "desc": "Inclinaison latérale douce."},
    {"id": "e1", "cat": "Ergonomie", "title": "Check Yeux", "icon": "👀", "img": "ergo_yeux.png", "desc": "Regard aligné au haut de l'écran."},
    {"id": "e2", "cat": "Ergonomie", "title": "Check Dos", "icon": "🪑", "img": "ergo_dos.png", "desc": "Dos bien calé au dossier."},
    {"id": "e3", "cat": "Ergonomie", "title": "Check Bras", "icon": "📐", "img": "ergo_coudes.png", "desc": "Coudes à 90 degrés."},
    {"id": "e4", "cat": "Ergonomie", "title": "Check Écran", "icon": "🖥️", "img": "ergo_ecran.png", "desc": "Distance d'un bras minimum."},
    {"id": "s1", "cat": "Essentiels", "title": "Cohérence Cardiaque", "icon": "❤️", "img": "coherence.png", "desc": "Respiration rythmée 5s/5s."},
    {"id": "s2", "cat": "Essentiels", "title": "Hydratation", "icon": "💧", "img": "hydratation.png", "desc": "Boire un verre d'eau."},
    {"id": "s3", "cat": "Essentiels", "title": "Regard au Loin", "icon": "🔭", "img": "regard_loin.png", "desc": "Fixer un point à 6m (20s)."},
    {"id": "s4", "cat": "Essentiels", "title": "Respiration Ventrale", "icon": "🎈", "img": "respiration_ventre.png", "desc": "Respirer par le ventre."},
]

prime_active = st.session_state.game.get("theme_system_s_unlocked", False)
prime_enabled = st.session_state.game.get("theme_prime_enabled", True)

is_prime_activated = st.session_state.game.get("theme_system_s_unlocked", False)
prime_enabled = st.session_state.game.get("theme_prime_enabled", True)

if not is_prime_activated or not prime_enabled:
    st.markdown("""
    <style>
        :root { --anim-bg: #FFFFFF; --anim-primary: #1E293B; --anim-secondary: #F59E0B; }
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
        .stApp { background-color: #F8FAFC; }
        .sanctuary-card { background: white; border-radius: 15px; padding: 20px; border: 1px solid #E2E8F0; color: #1E293B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .roulette-container { height: 120px; display: flex; align-items: center; justify-content: center; font-size: 3rem; background: #1E293B; border-radius: 10px; color: white; border: 4px solid #F59E0B; }
        .shop-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 15px; transition: 0.3s; margin-bottom: 10px; text-align: center; }
        .shop-card:hover { border-color: #6366F1; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(99,102,241,0.1); }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        :root { --anim-bg: #000000; --anim-primary: #00FF41; --anim-secondary: #00FF41; }
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
        html, body, [class*="css"], .stText, p, span, label { font-family: 'Press Start 2P', cursive !important; color: #00FF41 !important; font-size: 0.8rem; }
        .stApp { background-color: #0D0D0D !important; background-image: linear-gradient(rgba(0, 255, 65, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 65, 0.05) 1px, transparent 1px); background-size: 20px 20px; }
        .sanctuary-card { background: #000000 !important; border: 2px solid #00FF41 !important; color: #00FF41 !important; box-shadow: 0 0 15px rgba(0, 255, 65, 0.4); }
        .shop-card { background: #000000; border: 1px solid #00FF41; border-radius: 0px; padding: 15px; margin-bottom: 10px; text-align: center; box-shadow: 0 0 5px #00FF41; }
        header, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR (PRIORITÉ NOTE > CITATION) ---
def get_daily_metrics(date_cible):
    if st.session_state.df.empty: return 0.0, 0.0
    df_day = st.session_state.df[st.session_state.df['Date'].dt.date == date_cible]
    return df_day['Effectif_h'].sum(), df_day['Pause'].sum()

with st.sidebar:
    st.title("⏱️ OptiTime V13.6")
    memo = load_memo()
    if memo:
        st.info(f"📩 **Note pour demain :**\n\n{memo}")
        if st.button("Marquer comme lu"): clear_memo(); st.rerun()
    else:
        pack = st.session_state.game["current"].get("pack", "Stoïcisme")
        if 'current_quote' not in st.session_state: st.session_state.current_quote = random.choice(QUOTES_DB[pack])
        q = st.session_state.current_quote
        st.markdown(f"""<div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border-left:4px solid #6366F1;">
            <i>"{q['text']}"</i><br><div style="text-align:right; font-size:0.8em;">— {q['author']}</div></div>""", unsafe_allow_html=True)

    h_t, _ = get_daily_metrics(datetime.now().date())
    avatar, msg, bg, _, _ = get_optigotchi_status(h_t, 0, st.session_state.config["objectif_h"], st.session_state.game["current"]["skin"], st.session_state.game)
    st.markdown(f'<div style="background:{bg}; font-size:3rem; text-align:center; border-radius:50%; width:100px; height:100px; margin:auto; line-height:100px; border:4px solid white;">{avatar}</div>', unsafe_allow_html=True)
    st.write(f"**{msg}**")

    with st.expander("🎒 Inventaire", expanded=False):
        st.write(f"📦 Capsules Joker : **{st.session_state.game['inventory'].get('joker_coffe',0)}**")
        st.write(f"⏳ Rattrapages Série : **{st.session_state.game['inventory'].get('streak_fixer',0)}**")

    if st.button("❌ QUITTER"): save_game_data(st.session_state.game); os._exit(0)

# --- 6. TABS ---
t1, t2, t3, t4, t5, t6, t7 = st.tabs(["⏱️ Pointage", "⚡ Vitalité", "🧘 Boutique", "🏆 Trophées", "📅 Journal", "📊 Rapports", "⚙️ Config"])

# --- TAB 1 : POINTAGE (CHRONO & MODES) ---
with t1:
    st.header("Gestion du Temps")
    
    design = st.selectbox(
        "Style du Moniteur", 
        ["Aura Zen", "Cercle Moderne", "Jauge Liquide", "Terminal Cyber", "Kumo Zen (Néomorphe)", "Battement ECG"], 
        key="timer_design_choice"
    )

    if st.session_state.timer_active:
        @st.fragment(run_every=1)
        def timer_display():
            now_dt = datetime.now()
            indigo, bg_w = "#663399", "#FFFFFF"
            
            delta_td = now_dt - st.session_state.timer_start_dt
            delta_str = str(delta_td).split('.')[0]
            
            # --- LOGIQUE KUMO (Plus rapide : cycle de 30s) ---
            # On utilise le modulo 30 pour que le dessin recommence toutes les 30 secondes
            seconds_passed = delta_td.total_seconds()
            kumo_progress = (seconds_passed % 30) / 30 
            dash_array = 600 
            dash_offset = dash_array * (1 - kumo_progress)

            # --- LOGIQUE DE RENDU VISUEL ---
            if design == "Terminal Cyber":
                st.markdown(f"""
                <div style="background:#121212; border-radius:2px; padding:40px; border: 1px solid #333; max-width:400px; margin:auto; position:relative;">
                    <div style="position:absolute; top:10px; left:10px; width:5px; height:5px; background:#6366F1; border-radius:50%; box-shadow: 0 0 10px #6366F1;"></div>
                    <p style="color:#666; font-family:monospace; font-size:0.7rem; letter-spacing:2px; margin-bottom:10px;">ID_SESSION_{st.session_state.timer_start_dt.strftime('%H%M')}</p>
                    <h1 style='font-family:monospace; font-weight:100; font-size:4rem; color:#E0E0E0; margin:0; text-shadow: 0 0 20px rgba(255,255,255,0.1);'>{delta_str}</h1>
                    <div style="margin-top:20px; height:1px; width:100%; background:linear-gradient(90deg, #6366F1, transparent);"></div>
                </div>""", unsafe_allow_html=True)

            elif design == "Aura Zen":
                ink_deep = "#5D0000"
                
                # Fonction pour nettoyer le code et éviter l'affichage brut
                def clean_html(raw):
                    return "".join([line.strip() for line in raw.split('\n')])

                raw_ui = f"""
                <div style="background:#E0E5EC; border-radius:50%; width:380px; height:380px; margin:auto; position:relative; display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow: 20px 20px 60px #bec3c9, -20px -20px 60px #ffffff; border:none; overflow:visible;">
                    
                    <style>
                        @keyframes pulse_aura {{
                            0% {{ transform: scale(1); opacity: 0.4; box-shadow: 0 0 20px {ink_deep}; }}
                            50% {{ transform: scale(1.2); opacity: 0.1; box-shadow: 0 0 50px {ink_deep}; }}
                            100% {{ transform: scale(1); opacity: 0.4; box-shadow: 0 0 20px {ink_deep}; }}
                        }}
                        .glow_layer {{
                            position: absolute;
                            border-radius: 50%;
                            border: 2px solid {ink_deep};
                            animation: pulse_aura 5s infinite ease-in-out;
                        }}
                    </style>

                    <div class="glow_layer" style="width: 220px; height: 220px; animation-delay: 0s;"></div>
                    <div class="glow_layer" style="width: 260px; height: 260px; animation-delay: -1s; opacity: 0.1;"></div>
                    
                    <div style="position:relative; z-index:10; text-align:center;">
                        <h1 style="font-family:'Georgia', serif; font-size:5.5rem; color:#2D3436; margin:0; font-weight:100; letter-spacing:-4px; line-height:1; background:transparent;">
                            {delta_str}
                        </h1>
                        <div style="width:40px; height:1px; background:{ink_deep}; margin:15px auto; opacity:0.2;"></div>
                        <p style="color:{ink_deep}; font-size:0.75rem; letter-spacing:8px; text-transform:uppercase; margin:0; font-weight:bold; opacity:0.5;">
                            Aura
                        </p>
                    </div>
                </div>
                """
                
                st.markdown(clean_html(raw_ui), unsafe_allow_html=True)

            elif design == "Kumo Zen (Néomorphe)":
                ink_deep = "#5D0000" 
                
                # --- GÉNÉRATEUR DE NUAGE (CORRIGÉ AVEC BASE) ---
                def get_calligraphy_cloud(size, top, left, opacity, flip=False, sketchy=False):
                    f = -1 if flip else 1
                    # Hésitations (traits de construction supérieurs)
                    hesitations = f"""
                        <g stroke="{ink_deep}" fill="none" stroke-width="0.5" opacity="0.15" stroke-dasharray="3,5">
                            <path d="M10,45 Q40,25 70,45" /> <path d="M70,20 A15,15 0 1,1 100,30" />
                        </g>
                    """ if sketchy else ""

                    return f"""
                    <g transform="translate({left},{top}) scale({size/100 * f}, {size/100})" opacity="{opacity}">
                        {hesitations}
                        
                        <g stroke="{ink_deep}" stroke-width="1.4" fill="none" stroke-linecap="round">
                            <path d="M5,52 C15,45 22,48 28,42" /> <path d="M35,38 C45,25 55,25 62,35" />
                            <path d="M72,30 C85,10 105,15 110,35" /> <path d="M115,42 C135,35 145,48 130,55" />
                        </g>

                        <g stroke="{ink_deep}" stroke-width="1.2" fill="none" stroke-linecap="round" opacity="0.9">
                             <path d="M 10,58 Q 45,65 80,60" /> 
                            <path d="M 95,60 Q 120,62 140,55" stroke-dasharray="20,5" /> <path d="M -10,65 Q 60,70 130,65" stroke-width="0.7" opacity="0.6" stroke-dasharray="50,10" />
                        </g>

                        <g stroke="{ink_deep}" stroke-width="0.9" fill="none" opacity="0.8">
                            <path d="M38,35 A5,5 0 1,1 45,30" /> 
                            <path d="M80,25 A8,8 0 1,1 90,32" stroke-dasharray="2,3" />
                            <path d="M118,35 A6,6 0 1,1 125,40" />
                        </g>
                    </g>
                    """

                # --- GÉNÉRATEUR DE SIGNATURE (Validé) ---
                def get_signature_svg():
                    return f"""
                    <svg viewBox="0 0 100 100" style="position:absolute; bottom:25px; right:35px; width:60px; height:60px; opacity:0.45;">
                        <rect x="5" y="5" width="90" height="90" fill="none" stroke="{ink_deep}" stroke-width="1" stroke-dasharray="5,3" opacity="0.3" />
                        <g stroke="{ink_deep}" fill="none" stroke-width="2.5" stroke-linecap="round">
                            <path d="M25,30 L65,30" opacity="0.9" /> <path d="M25,45 L60,45 Q65,45 62,65" stroke-dasharray="15,4" />
                            <path d="M50,15 L53,22 M60,12 L63,19" stroke-width="1.5" />
                        </g>
                        <g stroke="{ink_deep}" fill="none" stroke-width="2.5" stroke-linecap="round">
                            <path d="M30,75 Q40,70 45,78" stroke-width="2" /> <path d="M25,95 Q65,95 75,55" stroke-dasharray="25,8" />
                        </g>
                    </svg>
                    """

                def clean_html(raw):
                    return "".join([line.strip() for line in raw.split('\n')])

                # COMPOSITION (5 Nuages complets)
                cloud_scene = (
                    get_calligraphy_cloud(140, 10, 15, 0.75, sketchy=True) + 
                    get_calligraphy_cloud(110, 50, 440, 0.5, flip=True) +
                    get_calligraphy_cloud(90, 190, -25, 0.35, sketchy=True) +
                    get_calligraphy_cloud(130, 270, 90, 0.6, flip=True) +
                    get_calligraphy_cloud(100, 210, 470, 0.65)
                )

                raw_ui = f"""
                <div style="background:#E0E5EC; border-radius:50px; padding:60px; text-align:center; box-shadow: 20px 20px 60px #bec3c9, -20px -20px 60px #ffffff; max-width:650px; margin:auto; position:relative; overflow:hidden; min-height:450px; display:flex; flex-direction:column; align-items:center; justify-content:center; border:none;">
                    <svg viewBox="0 0 650 450" style="position:absolute; top:0; left:0; width:100%; height:100%;">
                        {cloud_scene}
                    </svg>
                    
                    {get_signature_svg()}

                    <div style="position:relative; z-index:10;">
                        <h1 style="font-family:'Georgia', serif; font-size:5.5rem; color:#2D3436; margin:0; font-weight:100; letter-spacing:-4px; line-height:1;">{delta_str}</h1>
                        <div style="width:40px; height:1px; background:{ink_deep}; margin:25px auto; opacity:0.25;"></div>
                        <p style="color:{ink_deep}; font-size:0.75rem; letter-spacing:8px; text-transform:uppercase; margin:0; font-weight:bold; opacity:0.7;">Kumo Calligraphie Zen</p>
                    </div>
                </div>
                """
                st.markdown(clean_html(raw_ui), unsafe_allow_html=True)

            elif design == "Cercle Moderne":
                st.markdown(f"""
                <div style="display:flex; justify-content:center; align-items:center; margin: 20px auto; width:250px; height:250px; border-radius:50%; border: 6px solid #F0F0F0; border-top: 6px solid {indigo}; animation: spin-circle 4s linear infinite;">
                    <div style="animation: reverse-spin 4s linear infinite;">
                        <h1 style='color:{indigo}; margin:0;'>{delta_str}</h1>
                    </div>
                </div>
                <style>
                    @keyframes spin-circle {{ 100% {{ transform: rotate(360deg); }} }}
                    @keyframes reverse-spin {{ 100% {{ transform: rotate(-360deg); }} }}
                </style>""", unsafe_allow_html=True)

            elif design == "Jauge Liquide":
                # 1. CALCUL DE LA PROGRESSION (Sécurisé)
                objectif_h = st.session_state.config.get("objectif_h", 7.0)
                fait_h, _ = get_daily_metrics(now_dt.date())
                # On s'assure d'avoir au moins 1% pour voir le liquide au début
                total_actuel_h = fait_h + (delta_td.total_seconds() / 3600)
                pct = max(1, min(100, int((total_actuel_h / objectif_h) * 100)))
                
                # 2. PRÉPARATION DU HTML (Nettoyage des indentations avec dedent)
                # Note : on utilise textwrap.dedent pour que le HTML soit collé à gauche
                html_jauge = textwrap.dedent(f"""
                    <div style="background:#f0f2f6; border-radius:20px; width:100%; max-width:400px; height:220px; margin:auto; position:relative; overflow:hidden; border:4px solid {indigo};">
                        <div style="position:absolute; bottom:0; left:0; width:100%; height:{pct}%; background:{indigo}; opacity:0.6; transition: height 1s ease;">
                            <div class="wave_container">
                                <svg viewBox="0 0 100 20" preserveAspectRatio="none" class="wave_svg">
                                    <path d="M0 10 Q 25 20 50 10 T 100 10 V 20 H 0 Z" fill="{indigo}" />
                                </svg>
                                <svg viewBox="0 0 100 20" preserveAspectRatio="none" class="wave_svg">
                                    <path d="M0 10 Q 25 20 50 10 T 100 10 V 20 H 0 Z" fill="{indigo}" />
                                </svg>
                            </div>
                        </div>
                        <div style="position:relative; z-index:10; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%;">
                            <h1 style="font-size:4rem; color:#1E293B; margin:0; border:none; background:none; box-shadow:none;">{delta_str}</h1>
                            <div style="color:white; background:{indigo}; padding:2px 12px; border-radius:20px; font-weight:bold; font-size:0.9rem;">
                                {pct}% de l'objectif
                            </div>
                        </div>
                        <style>
                            .wave_container {{
                                position: absolute;
                                top: -20px;
                                left: 0;
                                width: 200%;
                                height: 30px;
                                display: flex;
                                animation: move_wave 3s linear infinite;
                            }}
                            .wave_svg {{ width: 100%; height: 100%; }}
                            @keyframes move_wave {{
                                0% {{ transform: translateX(0); }}
                                100% {{ transform: translateX(-50%); }}
                            }}
                        </style>
                    </div>
                """)
                
                # 3. AFFICHAGE
                st.markdown(html_jauge, unsafe_allow_html=True)

            elif design == "Battement ECG":
                st.markdown(f"""
                <div style="background:#121212; border-radius:15px; padding:40px; text-align:center; max-width:400px; margin:auto; border: 1px solid #333; position:relative; overflow:hidden;">
                    <h1 style='font-family:monospace; font-size:4rem; color:{indigo}; margin:0; text-shadow: 0 0 15px {indigo}66;'>{delta_str}</h1>
                    <svg viewBox="0 0 200 40" style="width:100%; height:60px; margin-top:10px;">
                        <path d="M0,20 L40,20 L45,10 L50,30 L55,20 L80,20 L85,0 L90,40 L95,20 L130,20 L135,15 L140,25 L145,20 L200,20" 
                              fill="none" stroke="{indigo}" stroke-width="2" stroke-dasharray="1000" stroke-dashoffset="1000">
                            <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="2s" repeatCount="indefinite" />
                        </path>
                        <circle cx="0" cy="20" r="3" fill="{indigo}">
                            <animateMotion dur="2s" repeatCount="indefinite" path="M0,20 L40,20 L45,10 L50,30 L55,20 L80,20 L85,0 L90,40 L95,20 L130,20 L135,15 L140,25 L145,20 L200,20" />
                        </circle>
                    </svg>
                </div>""", unsafe_allow_html=True)
            
            # --- BOUTONS ---
            st.write("")
            col_btns = st.columns(2)
            with col_btns[0]:
                if st.button("⏹ STOP & ENREGISTRER", type="primary", use_container_width=True, key="btn_stop_final"):
                    fran = st.session_state.config.get("franchise_min", 30)
                    eff = calculate_duration(st.session_state.timer_start_dt.time(), now_dt.time(), 0, fran)
                    fait, _ = get_daily_metrics(now_dt.date())
                    total = fait + eff
                    if total >= st.session_state.config.get("objectif_h", 7.0):
                        finaliser_session(eff, st.session_state.timer_activity, "Objectif atteint")
                    else:
                        st.session_state.temp_eff, st.session_state.temp_total = eff, total
                        st.session_state.timer_active, st.session_state.show_cloture = False, True
                        st.rerun()
            with col_btns[1]:
                if st.button("⏸ PAUSE ACTIVE", use_container_width=True):
                    st.session_state.current_pause, st.session_state.pause_mode = random.choice(CATALOGUE_RECUPS), True
                    st.rerun()
        
        timer_display()
        
    else:
        # Interface de démarrage (quand le timer est inactif)
        c1, c2 = st.columns([3, 1])
        with c1:
            act = st.selectbox("Choisir une activité", st.session_state.config["activites"])
        with c2:
            st.write("") 
            if st.button("▶ DÉMARRER", type="primary", use_container_width=True):
                st.session_state.timer_active, st.session_state.timer_start_dt, st.session_state.timer_activity = True, datetime.now(), act
                st.rerun()
    # =========================================================
    # --- 3. BLOCS ADDITIONNELS (INCLUS DANS L'ONGLET T1) ---
    # =========================================================
    st.divider()

    # 1. SAISIE MANUELLE
    with st.expander("📝 Saisie Manuelle"):
        st.info("Ajouter une entrée manuellement.")        
        with st.form("form_manual_entry_unique"):
            dm = st.date_input("Date", key="manual_date")
            t1m = st.time_input("Arrivée", time(8,30), key="manual_t1")
            t2m = st.time_input("Départ", time(17,0), key="manual_t2")
            pm = st.number_input("Pause (min)", 0, 120, 45, key="manual_p")
            am = st.selectbox("Activité", st.session_state.config["activites"], key="manual_act")
            
            if st.form_submit_button("ENREGISTRER L'ENTRÉE"):
                eff = calculate_duration(t1m, t2m, pm, st.session_state.config["franchise_min"])
                save_entry_db({
                    "Date": pd.to_datetime(dm), 
                    "Arrivée": t1m.strftime("%H:%M"), 
                    "Départ": t2m.strftime("%H:%M"), 
                    "Pause": pm, 
                    "Activité": am, 
                    "Commentaire": "Manuel", 
                    "Effectif_h": eff, 
                    "Solde_h": 0
                })
                st.session_state.df = load_data_db()
                st.success("Entrée enregistrée !")
                st.rerun()

    # 2. DÉPART RAPIDE
    with st.expander("🚪 Départ Rapide"):
        t_reprise = st.time_input("Heure de début d'activité", value=time(14,0), key="quick_t")
        act_fin = st.selectbox("Dernière activité", st.session_state.config["activites"], key="quick_act")
        msg_demain = st.text_area("Note / Message pour demain", key="quick_memo")
        if st.button("💾 CLÔTURER LA JOURNÉE", type="primary", use_container_width=True, key="btn_quick_exit"):
            if msg_demain: 
                save_memo(msg_demain)
            eff = calculate_duration(t_reprise, datetime.now().time(), 0, st.session_state.config["franchise_min"])
            save_entry_db({
                "Date": pd.to_datetime(datetime.now().date()), 
                "Arrivée": t_reprise.strftime("%H:%M"), 
                "Départ": datetime.now().strftime("%H:%M"), 
                "Pause": 0, 
                "Activité": act_fin, 
                "Commentaire": "Fin Rapide", 
                "Effectif_h": eff, 
                "Solde_h": 0
            })
            save_game_data(st.session_state.game)
            os._exit(0)

    # 3. DÉCLARATION D'ABSENCE
    with st.expander("🏖️ Déclaration d'Absence"):
        with st.form("form_absence_entry_unique"):
            d1 = st.date_input("Date de début", key="abs_d1")
            d2 = st.date_input("Date de fin", key="abs_d2")
            motif = st.selectbox("Motif", ["RTT", "FÉRIÉ", "CONGÉS ANNUELS", "MALADIE"], key="abs_motif")
            if st.form_submit_button("VALIDER L'ABSENCE"):
                delta = (d2 - d1).days + 1
                energy_reward = 20 * delta if motif in ["RTT", "FÉRIÉ", "CONGÉS ANNUELS"] else 0
                
                curr = d1
                while curr <= d2:
                    save_entry_db({"Date": pd.to_datetime(curr), "Arrivée": "00:00", "Départ": "00:00", "Pause": 0, "Activité": motif, "Commentaire": "Absence", "Effectif_h": 7.0, "Solde_h": 0})
                    curr += timedelta(days=1)
                
                st.session_state.game["vitality_ener"] += energy_reward
                save_game_data(st.session_state.game)
                st.session_state.df = load_data_db()
                st.success(f"Absence enregistrée. {energy_reward} ⚡ gagnés !")
                tm.sleep(1)
                st.rerun()


# --- TAB 2 : LE SANCTUAIRE DE VITALITÉ ---
with t2:
    st.header("☕ Sanctuaire de Vitalité")
    
    # 1. ÉTAT DES RÉSERVES
    ener = st.session_state.game.get("vitality_ener", 0)
    capsules = st.session_state.game["inventory"].get("joker_coffe", 0)
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown(f"""<div class="sanctuary-card" style="text-align:center; background:#FEFCE8; border-color:#FACC15;">
            <p style="margin:0; font-size:0.8em; color:#854D0E;">ÉNERGIE TOTALE</p>
            <h2 style="color:#D97706; margin:0;">{ener} ⚡</h2>
        </div>""", unsafe_allow_html=True)
    with col_res2:
        st.markdown(f"""<div class="sanctuary-card" style="text-align:center; background:#FDF2F2; border-color:#92400E;">
            <p style="margin:0; font-size:0.8em; color:#92400E;">DOSETTES EN STOCK</p>
            <h2 style="color:#78350F; margin:0;">{capsules} ☕</h2>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # 2. COMPTOIR DES CAPSULES (Design Boutique Café)
    st.subheader("🛍️ Le Comptoir du Barista")
    c_buy1, c_buy2, c_buy3 = st.columns(3)
    
    with c_buy1:
        st.markdown("""<div style="border-left:3px solid #78350F; padding-left:10px; margin-bottom:10px;">
            <b style="color:#78350F;">Capsule Grand Cru</b><br>
            <small style="color:gray;">Nécessaire pour lancer une extraction à la machine.</small>
        </div>""", unsafe_allow_html=True)
        if st.button("ACHETER (-50⚡)", key="btn_buy_pod_v13", use_container_width=True):
            if ener >= 50:
                st.session_state.game["vitality_ener"] -= 50
                st.session_state.game["inventory"]["joker_coffe"] += 1
                save_game_data(st.session_state.game); st.rerun()
            else: st.error("Énergie insuffisante !")

    with c_buy2:
        st.markdown("""<div style="border-left:3px solid #F59E0B; padding-left:10px; margin-bottom:10px;">
            <b style="color:#B45309;">Contrat Barista</b><br>
            <small style="color:gray;">Misez 100⚡. Si vous tenez 3j (2 pauses/j), gagnez 300⚡.</small>
        </div>""", unsafe_allow_html=True)
        if st.button("SIGNER (-100⚡)", key="btn_contract_pod_v13", use_container_width=True, disabled=st.session_state.game.get("active_contract") is not None):
            if ener >= 100:
                st.session_state.game["vitality_ener"] -= 100
                st.session_state.game["active_contract"] = {"days_done": 0, "target_days": 3}
                save_game_data(st.session_state.game); st.rerun()

    with c_buy3:
        st.markdown("""<div style="border-left:3px solid #6366F1; padding-left:10px; margin-bottom:10px;">
            <b style="color:#4F46E5;">Vortex Arabica</b><br>
            <small style="color:gray;">Bonus spécial pour restaurer une série brisée par oubli.</small>
        </div>""", unsafe_allow_html=True)
        if st.button("ACTIVER (-300⚡)", key="btn_vortex_pod_v13", use_container_width=True):
            st.session_state.vortex_mode = True; st.rerun()

    st.divider()

    # 3. LA MACHINE À CAFÉ (Loterie & Révélation)
    st.subheader("☕ Percolateur Haute Pression")
    
    reveal_area = st.empty()
    
    if capsules > 0:
        if st.button("PRÉPARER MON CAFÉ (Consomme 1 Dosette)", type="primary", use_container_width=True, key="btn_brew_coffee"):
            st.session_state.game["inventory"]["joker_coffe"] -= 1
            
            # --- ÉTAPES DE PRÉPARATION ---
            steps = [
                ("🫳", "Insertion de la dosette dans le tiroir..."),
                ("🌡️", "Chauffage de l'eau à température optimale..."),
                ("⚙️", "Montée en pression (19 bars)..."),
                ("☕", "Extraction lente des arômes...")
            ]
            
            for icon, text in steps:
                reveal_area.markdown(f"""<div class="sanctuary-card" style="text-align:center;">
                    <h3 style="color:#78350F;">{icon} {text}</h3>
                </div>""", unsafe_allow_html=True)
                tm.sleep(1.0)
            
            # --- TIRAGE DE LA LOTERIE (6 PRIX) ---
            # [Nom, Gain_Ener, Gain_Fixer, Couleur, Message, Consolation]
            lottery_pool = [
                ("L'OR NOIR (ULTRA-REBOOST)", 125, 0, "#F59E0B", "ARÔME EXCEPTIONNEL !", "Le meilleur cru de la saison !"),
                ("ESPRESSO DE PROTECTION", 0, 1, "#6366F1", "BOUCLIER TEMPOREL !", "Un goût puissant qui fige le temps."),
                ("ALLONGÉ ÉNERGÉTIQUE", 40, 0, "#10B981", "RECHARGE RÉUSSIE.", "Un café équilibré pour bien repartir."),
                ("DÉCAFÉINÉ NEUTRE", 0, 0, "#94A3B8", "RIEN À SIGNALER.", "Le goût est là, mais l'effet est nul."),
                ("JUS DE CHAUSSETTE", -15, 0, "#EF4444", "CAFÉ IMBUVABLE...", "Attention, il est vraiment trop amer."),
                ("BRÛLURE DU PERCOLATEUR", -30, 0, "#7F1D1D", "INCIDENT MACHINE !", "Le café a débordé sur vos réserves !")
            ]
            
            res = random.choices(lottery_pool, weights=[10, 15, 35, 20, 10, 10])[0]
            nom, g_e, g_f, color, m_msg, c_msg = res
            
            # Update state
            st.session_state.game["vitality_ener"] += g_e
            if g_f > 0:
                st.session_state.game["inventory"]["streak_fixer"] = st.session_state.game["inventory"].get("streak_fixer", 0) + 1
            
            save_game_data(st.session_state.game)

           # --- RÉVÉLATION FINALE (CORRECTION DÉFINITIVE DU RENDU) ---
            import textwrap # S'assurer que l'import est présent en haut du fichier
            
            is_jackpot = g_e >= 100 or g_f > 0
            is_bad = g_e < 0
            shadow = f"0 10px 30px {color}44" if is_jackpot else "none"
            
            # 1. On prépare les données proprement
            gain_display = ""
            if g_e > 0: gain_display = f"+{g_e} ⚡"
            elif g_e < 0: gain_display = f'<span style="color:#EF4444;">{g_e} ⚡</span>'
            
            if g_f > 0:
                gain_display += " 🛡️ GEL DE SÉRIE"
            if not gain_display:
                gain_display = '<span style="color:#94A3B8;">☕ TASSE VIDE</span>'

            conclusion = "😟 Pas de chance... une petite pause s'impose." if is_bad else "💼 Dégustation terminée. Retour au travail !"

            # 2. On crée le HTML sans aucune indentation Markdown
            html_content = textwrap.dedent(f"""
                <div style="background-color:white; border:5px solid {color}; border-radius:15px; text-align:center; padding:40px; margin:10px 0; box-shadow:{shadow};">
                    <h1 style="color:{color}; font-size:2.8em; margin:0; line-height:1.1; border:none; background:none;">{nom}</h1>
                    <p style="font-size:1.2em; font-weight:bold; margin-top:5px; color:{color}; text-transform:uppercase; letter-spacing:1px;">
                        {m_msg}
                    </p>
                    <hr style="border:0; border-top:1px solid {color}; opacity:0.2; margin:25px 0;">
                    <div style="font-size:3em; margin:20px 0; font-weight:bold; color:#1E293B;">
                        {gain_display}
                    </div>
                    <div style="background:rgba(0,0,0,0.03); border-radius:8px; padding:15px; margin:20px 0; border:1px dashed {color}66;">
                        <p style="font-style:italic; color:#4B5563; margin:0; font-size:1.1em;">
                            "{c_msg}"
                        </p>
                    </div>
                    <p style="color:#64748B; font-size:0.9em; font-weight:500; margin-top:25px;">
                        {conclusion}
                    </p>
                </div>
            """)

            # 3. Affichage
            reveal_area.markdown(html_content, unsafe_allow_html=True)

            if is_jackpot: st.balloons()
            save_game_data(st.session_state.game)
            tm.sleep(5.0)
            st.rerun()

# --- TAB 3 : BOUTIQUE (ESTHÉTIQUE) ---
with t3:
    st.header("🧘 Boutique de la Récup'")
    rayons = ["Régénération", "Mouvements", "Ergonomie", "Essentiels"]
    cols = st.columns(4)
    for i, r in enumerate(rayons):
        with cols[i]:
            st.markdown(f"### {r}")
            for it in [x for x in CATALOGUE_RECUPS if x['cat'] == r]:
                st.markdown(f"""<div class="shop-card">
                    <div style="font-size:2rem;">{it['icon']}</div>
                    <div style="font-weight:bold; margin:5px 0;">{it['title']}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"Lancer", key=f"btn_shop_{it['id']}", use_container_width=True):
                    st.session_state.current_pause = it; st.session_state.pause_mode = True; st.rerun()

# --- TAB 4 : TROPHÉES (XP & LISTE) ---
with t4:
    st.header("🏆 Galerie des Succès")
    xp = st.session_state.game.get("xp", 0)
    st.progress(min(xp/3000, 1.0))
    st.write(f"XP Totale : **{xp} / 3000**")
    st.divider()
    cols_tr = st.columns(2)
    for i, tr in enumerate(LISTE_TROPHEES):
        unlocked = tr["id"] in st.session_state.game.get("achievements_unlocked", [])
        with cols_tr[i % 2]:
            st.markdown(f"""<div class="sanctuary-card" style="opacity: {1 if unlocked else 0.4}; margin-bottom:10px;">
                <b>{'✅' if unlocked else '🔒'} {tr['name']}</b><br><small>{tr['desc_mission']}</small></div>""", unsafe_allow_html=True)

# --- TAB 5 : JOURNAL (RESTAURÉ AVEC SUPPRESSION) ---
with t5:
    st.header("📅 Historique des Saisies")
    if not st.session_state.df.empty:
        edit_df = st.data_editor(st.session_state.df, use_container_width=True, key="journal_editor")
        if st.button("💾 SAUVEGARDER LES MODIFICATIONS"):
            update_db_from_df(edit_df); st.session_state.df = load_data_db(); st.rerun()
            
        st.divider()
        st.subheader("🗑️ Zone de Suppression")
        to_del = st.multiselect("Sélectionnez les entrées à supprimer :", options=st.session_state.df.index,
                                format_func=lambda x: f"{st.session_state.df.loc[x, 'Date'].strftime('%d/%m')} - {st.session_state.df.loc[x, 'Activité']} ({st.session_state.df.loc[x, 'Effectif_h']}h)")
        if to_del and st.button("🚨 SUPPRIMER LA SÉLECTION", type="secondary"):
            update_db_from_df(st.session_state.df.drop(to_del))
            st.session_state.df = load_data_db(); st.success("Supprimé !"); st.rerun()

# --- TAB 6 : RAPPORTS (GRAPHIQUE BARRES) ---
with t6:
    st.header("📊 Rapports d'Activité")
    if not st.session_state.df.empty:
        st.bar_chart(st.session_state.df.set_index('Date')['Effectif_h'], color="#6366F1")
        st.write(f"Total des heures enregistrées : **{st.session_state.df['Effectif_h'].sum():.2f} h**")

# --- DANS TAB 7 : CONFIG ---
with t7:
    st.subheader("⚙️ Paramètres Généraux")
    with st.form("form_config_main"):
        obj = st.number_input("Objectif quotidien (heures)", 1.0, 12.0, float(st.session_state.config.get("objectif_h", 7.0)))
        
        # AJOUT DE L'ITEM FRANCHISE ICI
        fran = st.number_input("Franchise de pause (min)", 0, 60, int(st.session_state.config.get("franchise_min", 30)), 
                                help="Temps de pause déduit seulement au-delà de cette durée.")
        
        if st.form_submit_button("SAUVEGARDER LES PARAMÈTRES"):
            st.session_state.config["objectif_h"] = obj
            st.session_state.config["franchise_min"] = fran # Sauvegarde de la franchise
            save_config(st.session_state.config)
            st.success("Configuration mise à jour !")
            st.rerun()

    st.divider()
    st.subheader("🎭 Personnalisation & Déblocages")
    
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        # --- SÉLECTEUR DE SKIN ---
        unlocked_skins = st.session_state.game.get("unlocked", ["Classique"])
        current_skin = st.session_state.game["current"].get("skin", "Classique")
        
        new_skin = st.selectbox(
            "Apparence de l'Optigotchi",
            options=unlocked_skins,
            index=unlocked_skins.index(current_skin) if current_skin in unlocked_skins else 0,
            help="Choisissez parmi vos skins débloqués."
        )
        if new_skin != current_skin:
            st.session_state.game["current"]["skin"] = new_skin
            save_game_data(st.session_state.game)
            st.rerun()

    with col_p2:
        # --- SÉLECTEUR DE PACK DE CITATIONS ---
        # On déduit les packs débloqués via les trophées obtenus
        unlocked_packs = ["Stoïcisme"] # Pack par défaut
        for tr in LISTE_TROPHEES:
            if tr["id"] in st.session_state.game.get("achievements_unlocked", []) and tr.get("pack_unlock"):
                unlocked_packs.append(tr["pack_unlock"])
        
        current_pack = st.session_state.game["current"].get("pack", "Stoïcisme")
        
        new_pack = st.selectbox(
            "Pack de Citations",
            options=unlocked_packs,
            index=unlocked_packs.index(current_pack) if current_pack in unlocked_packs else 0,
            help="Les citations qui apparaîtront dans l'interface."
        )
        if new_pack != current_pack:
            st.session_state.game["current"]["pack"] = new_pack
            save_game_data(st.session_state.game)
            st.rerun()

    # --- ÉTAT DU PROTOCOLE PRIME ---
    if is_prime_activated:
        st.divider()
        reality = st.toggle("💃 Mode Réalité (Désactive le thème visuel S)", value=not prime_enabled)
        if reality == prime_enabled:
            st.session_state.game["theme_prime_enabled"] = not reality
            save_game_data(st.session_state.game)
            st.rerun()

# --- GESTION EXCLUSIVE DES DIALOGUES ---
if st.session_state.get("pause_mode"): pause_modal()
if st.session_state.get("show_cloture"): modal_cloture_intelligente()
if st.session_state.get("vortex_mode"): vortex_modal()