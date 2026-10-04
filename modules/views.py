import flet as ft
from datetime import datetime, time, timedelta
import pandas as pd
import random
import time as tm
import os
import base64

from .constants import (
    CATALOGUE_RECUPS, LISTE_TROPHEES, QUOTES_DB, SKINS_DB, ASSETS_DIR
)
from .database import (
    load_data_db, save_entry_db, delete_entry_db, update_db_from_df
)
from .utils import (
    calculate_duration, save_config, save_game_data,
    update_streak_logic, check_achievements, get_optigotchi_status,
    load_memo, save_memo, clear_memo, get_resource_path
)

class AppViews:
    def __init__(self, page: ft.Page, app_state: dict):
        self.page = page
        self.state = app_state
        self.current_quote = None
        self.init_components()

    def init_components(self):
        # Sélecteur de style
        self.design_choice = ft.Dropdown(
            label="Style du Moniteur",
            options=[
                ft.dropdown.Option("Terminal Cyber"),
                ft.dropdown.Option("Aura Zen"),
                ft.dropdown.Option("Cercle Moderne"),
                ft.dropdown.Option("Jauge Liquide"),
                ft.dropdown.Option("Battement ECG"),
                ft.dropdown.Option("Kumo Zen (Néomorphe)")
            ],
            value="Terminal Cyber",
            width=260,
            on_change=lambda e: self.update_timer_render()
        )

        # Affichage temps du moniteur
        self.txt_time_display = ft.Text("00:00:00", size=48, weight=ft.FontWeight.W_200, font_family="monospace")
        self.txt_pct_display = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        self.monitor_container = ft.Container(
            content=ft.Column(
                [self.txt_time_display, self.txt_pct_display],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=420, height=220, border_radius=16, alignment=ft.alignment.center,
            bgcolor="#121212", border=ft.border.all(1, "#333333")
        )

        self.act_select = ft.Dropdown(
            label="Choisir une activité",
            options=[ft.dropdown.Option(a) for a in self.state["config"]["activites"]],
            value=self.state["config"]["activites"][0],
            width=300
        )
        self.btn_start = ft.ElevatedButton("▶ DÉMARRER", on_click=self.start_timer, bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE)
        self.btn_stop = ft.ElevatedButton("⏹ STOP & ENREGISTRER", on_click=self.stop_timer, bgcolor=ft.colors.RED_600, color=ft.colors.WHITE, visible=False)
        self.btn_pause = ft.ElevatedButton("⏸ PAUSE ACTIVE", on_click=lambda e: self.trigger_random_pause(), visible=False)

        # Boutique
        self.search_recup = ft.TextField(
            hint_text="Saisir un mot-clé (yeux, dos, stress, fatigue, eau...)",
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.render_shop_cards(e.control.value)
        )
        self.grid_shop = ft.GridView(expand=True, max_extent=260, child_aspect_ratio=1.1, spacing=10, run_spacing=10)

        # Barista
        self.txt_ener = ft.Text("0 ⚡", size=26, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_700)
        self.txt_pods = ft.Text("0 ☕", size=26, weight=ft.FontWeight.BOLD, color=ft.colors.BROWN_700)
        self.coffee_reveal_area = ft.Container(visible=False)

        # Dashboard / Journal
        self.table_journal = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Plage")),
                ft.DataColumn(ft.Text("Pause")),
                ft.DataColumn(ft.Text("Activité")),
                ft.DataColumn(ft.Text("Commentaire")),
                ft.DataColumn(ft.Text("Effectif")),
                ft.DataColumn(ft.Text("Suppr")),
            ],
            rows=[]
        )
        self.chart_bars = ft.BarChart(
            expand=True,
            interactive=True,
            bar_groups=[],
            bottom_axis=ft.ChartAxis(labels=[]),
        )
        self.txt_total_hours_report = ft.Text("Total des heures : 0.00 h", weight=ft.FontWeight.BOLD, size=16)

        # Sidebar & Optigotchi
        self.avatar_display = ft.Container(
            content=ft.Text("😐", size=40),
            width=80, height=80, border_radius=40,
            alignment=ft.alignment.center,
            border=ft.border.all(3, ft.colors.WHITE)
        )
        self.optigotchi_msg = ft.Text("En attente...", weight=ft.FontWeight.BOLD)
        self.memo_sidebar = ft.Container()
        self.sidebar_quote_box = ft.Container(padding=10, border_radius=8, bgcolor=ft.colors.BLACK12)

    # --- SIDEBAR REFRESH ---
    def refresh_sidebar(self):
        memo = load_memo()
        if memo:
            def on_read(e):
                clear_memo()
                self.refresh_sidebar()
                self.page.update()

            self.memo_sidebar.content = ft.Column([
                ft.Text("📩 Note pour demain :", weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700),
                ft.Text(memo, italic=True),
                ft.ElevatedButton("Marquer comme lu", on_click=on_read)
            ])
            self.memo_sidebar.visible = True
            self.sidebar_quote_box.visible = False
        else:
            self.memo_sidebar.visible = False
            pack = self.state["game"]["current"].get("pack", "Stoïcisme")
            quotes = QUOTES_DB.get(pack, QUOTES_DB["Stoïcisme"])
            if not self.current_quote:
                self.current_quote = random.choice(quotes)
            q = self.current_quote
            self.sidebar_quote_box.content = ft.Column([
                ft.Text(f'"{q["text"]}"', italic=True),
                ft.Text(f'— {q["author"]}', size=11, text_align=ft.TextAlign.RIGHT, color=ft.colors.GREY_600)
            ])
            self.sidebar_quote_box.visible = True

        df = load_data_db()
        today_h = 0.0
        if not df.empty:
            df_day = df[df['Date'].dt.date == datetime.now().date()]
            today_h = df_day['Effectif_h'].sum()

        skin = self.state["game"]["current"].get("skin", "Classique")
        av, msg, bg, _, _ = get_optigotchi_status(today_h, 0, self.state["config"]["objectif_h"], skin, self.state["game"])
        self.avatar_display.content.value = av
        self.avatar_display.bgcolor = bg
        self.optigotchi_msg.value = msg

    # --- CHRONO / RENDUS ---
    def start_timer(self, e):
        self.state["timer_active"] = True
        self.state["timer_start_dt"] = datetime.now()
        self.state["timer_activity"] = self.act_select.value
        self.btn_start.visible = False
        self.btn_stop.visible = True
        self.btn_pause.visible = True
        self.act_select.disabled = True
        self.update_timer_render()
        self.page.update()

    def update_clock_tick(self):
        if self.state["timer_active"]:
            self.state["elapsed_seconds"] = int((datetime.now() - self.state["timer_start_dt"]).total_seconds())
            td = timedelta(seconds=self.state["elapsed_seconds"])
            self.txt_time_display.value = str(td).split('.')[0]
            self.update_timer_render()
            self.page.update()

    def update_timer_render(self):
        design = self.design_choice.value
        now_dt = datetime.now()
        obj_h = float(self.state["config"].get("objectif_h", 7.0))
        df = load_data_db()
        fait_h = 0.0
        if not df.empty:
            fait_h = df[df['Date'].dt.date == now_dt.date()]['Effectif_h'].sum()
        current_total = fait_h + (self.state["elapsed_seconds"] / 3600)
        pct = max(1, min(100, int((current_total / obj_h) * 100)))

        td = timedelta(seconds=self.state["elapsed_seconds"])
        delta_str = str(td).split('.')[0]
        act_name = self.state.get("timer_activity", "Production")

        # Chaque design ci-dessous définit sa propre taille, son propre fond
        # et sa propre bordure sur son Container interne. Le conteneur externe
        # (self.monitor_container) doit donc rester neutre : sans cela, sa
        # taille et son fond d'origine (420x220, fond sombre) persistent
        # derrière/autour des designs plus grands ou plus clairs (Aura Zen
        # 380x380, Kumo Zen 550x320...), provoquant rognage ou fond incongru.
        self.monitor_container.width = None
        self.monitor_container.height = None
        self.monitor_container.bgcolor = None
        self.monitor_container.border = None
        self.monitor_container.border_radius = None

        # =========================================================
        # 1. TERMINAL CYBER
        # =========================================================
        if design == "Terminal Cyber":
            is_prime = self.state["game"].get("theme_system_s_unlocked", False)
            accent_col = "#00FF41" if is_prime else "#6366F1"
            txt_col = "#00FF41" if is_prime else "#E0E0E0"

            self.monitor_container.content = ft.Container(
                width=480, height=240, bgcolor="#121212", border_radius=8,
                border=ft.border.all(1, "#333333"),
                padding=25,
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Container(width=10, height=10, border_radius=5, bgcolor=accent_col),
                            ft.Text(f"ID_SESSION_{now_dt.strftime('%H%M')}", font_family="monospace", size=11, color="#666666"),
                        ], spacing=8),
                        ft.Text("ONLINE", font_family="monospace", size=10, color=accent_col)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        alignment=ft.alignment.center,
                        expand=True,
                        content=ft.Text(
                            delta_str,
                            size=54,
                            font_family="monospace",
                            weight=ft.FontWeight.W_200,
                            color=txt_col
                        )
                    ),
                    ft.Container(height=2, width=float("inf"), bgcolor=accent_col),
                    ft.Row([
                        ft.Text(f"> ACTIVITÉ: {act_name.upper()}", size=11, font_family="monospace", color="#888888"),
                        ft.Text(f"OBJECTIF: {pct}%", size=11, font_family="monospace", color=accent_col)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        # =========================================================
        # 2. AURA ZEN
        # =========================================================
        elif design == "Aura Zen":
            ink_deep = "#5D0000"
            self.monitor_container.content = ft.Container(
                width=380, height=380, border_radius=190,
                bgcolor="#E0E5EC",
                shadow=ft.BoxShadow(
                    spread_radius=2, blur_radius=40, color="#BEC3C9", offset=ft.Offset(16, 16)
                ),
                border=ft.border.all(2, f"{ink_deep}22"),
                content=ft.Stack([
                    ft.Container(
                        width=310, height=310, border_radius=155,
                        border=ft.border.all(2, f"{ink_deep}33"),
                        left=35, top=35
                    ),
                    ft.Container(
                        width=250, height=250, border_radius=125,
                        border=ft.border.all(1.5, f"{ink_deep}55"),
                        left=65, top=65
                    ),
                    ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(delta_str, size=52, font_family="Georgia", weight=ft.FontWeight.W_100, color="#2D3436"),
                            ft.Container(width=45, height=1, bgcolor=ink_deep, opacity=0.35),
                            ft.Text(
                                "AURA",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ink_deep,
                                style=ft.TextStyle(letter_spacing=6)
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6)
                    )
                ])
            )

        # =========================================================
        # 3. CERCLE MODERNE (avec rotation continue de l'anneau)
        # =========================================================
        elif design == "Cercle Moderne":
            # Un tour complet toutes les 60 secondes
            rotation_angle = (self.state["elapsed_seconds"] % 60) * (3.14159 / 30)

            self.monitor_container.content = ft.Container(
                width=320, height=320,
                alignment=ft.alignment.center,
                content=ft.Stack([
                    ft.Container(
                        content=ft.ProgressRing(
                            value=min(1.0, current_total / obj_h) if obj_h > 0 else 0,
                            stroke_width=10,
                            color=ft.colors.INDIGO_600,
                            bgcolor=ft.colors.INDIGO_50,
                            width=280, height=280
                        ),
                        rotate=ft.Rotate(angle=rotation_angle),
                        animate_rotation=ft.Animation(1000, ft.AnimationCurve.LINEAR)
                    ),
                    ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(delta_str, size=46, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_900),
                            ft.Text(f"{pct}% de l'objectif", size=13, color=ft.colors.GREY_600, weight=ft.FontWeight.W_500),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=10, vertical=3),
                                bgcolor=ft.colors.INDIGO_50,
                                border_radius=12,
                                content=ft.Text(f"{current_total:.2f} / {obj_h:.1f}h", size=11, color=ft.colors.INDIGO_700, weight=ft.FontWeight.BOLD)
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6)
                    )
                ], alignment=ft.alignment.center)
            )

        # =========================================================
        # 4. JAUGE LIQUIDE (crête de vague qui ondule en continu)
        # =========================================================
        elif design == "Jauge Liquide":
            indigo = "#4F46E5"
            water_height = int(220 * (pct / 100))
            # Décalage de phase : un cycle complet toutes les 4 secondes
            wave_offset = (self.state["elapsed_seconds"] % 4) * 25

            wave_svg = f"""
            <svg viewBox="0 0 440 25" xmlns="http://www.w3.org/2000/svg">
                <g transform="translate({-wave_offset},0)">
                    <path d="M-100,12 Q -75,2 -50,12 T 0,12 T 50,12 T 100,12 T 150,12 T 200,12 T 250,12 T 300,12 T 350,12 T 400,12 T 450,12 T 500,12 T 550,12"
                          fill="none" stroke="{indigo}" stroke-width="3" stroke-linecap="round" opacity="0.85" />
                </g>
            </svg>
            """
            b64_wave = base64.b64encode(wave_svg.encode('utf-8')).decode('utf-8')

            self.monitor_container.content = ft.Container(
                width=440, height=220, bgcolor="#F8FAFC", border_radius=20,
                border=ft.border.all(3, indigo),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Stack([
                    # Bloc de liquide (hauteur)
                    ft.Container(
                        width=440,
                        height=water_height,
                        bgcolor=ft.colors.with_opacity(0.35, indigo),
                        bottom=0,
                        left=0
                    ),
                    # Crête de vague ondulante (phase recalculée à chaque tick)
                    ft.Container(
                        width=440,
                        height=25,
                        bottom=max(0, water_height - 12),
                        left=0,
                        content=ft.Image(src_base64=b64_wave, width=440, height=25, fit=ft.ImageFit.FILL)
                    ),
                    # Affichage central
                    ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(delta_str, size=52, weight=ft.FontWeight.BOLD, color="#1E293B"),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=16, vertical=5),
                                bgcolor=indigo,
                                border_radius=20,
                                content=ft.Text(
                                    f"{pct}% de l'objectif ({current_total:.2f}/{obj_h}h)",
                                    size=12,
                                    color=ft.colors.WHITE,
                                    weight=ft.FontWeight.BOLD
                                )
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
                    )
                ])
            )

        # =========================================================
        # 5. BATTEMENT ECG (curseur lumineux qui balaie l'onde en boucle)
        # =========================================================
        elif design == "Battement ECG":
            ecg_red = "#EF4444"
            # Le curseur balaie la largeur du tracé toutes les 4 secondes, en boucle
            sweep_x = (self.state["elapsed_seconds"] % 4) / 4.0 * 400

            ecg_animated_svg = f"""
            <svg viewBox="0 0 400 60" xmlns="http://www.w3.org/2000/svg">
                <path d="M0,30 L80,30 L90,15 L100,45 L110,30 L160,30 L170,5 L180,55 L190,30 L250,30 L260,20 L270,40 L280,30 L400,30"
                      fill="none" stroke="{ecg_red}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.55" />
                <line x1="{sweep_x:.0f}" y1="0" x2="{sweep_x:.0f}" y2="60" stroke="{ecg_red}" stroke-width="1.5" opacity="0.8" />
                <circle cx="{sweep_x:.0f}" cy="30" r="4" fill="{ecg_red}" />
            </svg>
            """
            svg_b64 = base64.b64encode(ecg_animated_svg.encode('utf-8')).decode('utf-8')

            self.monitor_container.content = ft.Container(
                width=460, height=240, bgcolor="#0A0E17", border_radius=16,
                border=ft.border.all(1.5, "#1E293B"),
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.icons.FAVORITE, color=ecg_red, size=16),
                            ft.Text("ECG MONITOR - RYTHME ACTIF", size=11, font_family="monospace", color=ecg_red, weight=ft.FontWeight.BOLD)
                        ], spacing=6),
                        ft.Text("72 BPM", font_family="monospace", size=12, color="#64748B")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Text(delta_str, size=54, font_family="monospace", color=ecg_red, weight=ft.FontWeight.W_200)
                    ),
                    ft.Image(src_base64=svg_b64, width=420, height=45, fit=ft.ImageFit.CONTAIN),
                    ft.Row([
                        ft.Text("• IMPULSION CONTINUE", size=10, font_family="monospace", color="#64748B"),
                        ft.Text(f"EFFECTIF: {current_total:.2f}h", size=10, font_family="monospace", color=ecg_red)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        # =========================================================
        # 6. KUMO ZEN (le tracé calligraphique se redessine en boucle de 30s)
        # =========================================================
        else:
            ink_deep = "#5D0000"
            kumo_prog = (self.state["elapsed_seconds"] % 30) / 30.0
            dash_len = 160
            dash_offset = int(dash_len * (1 - kumo_prog))

            kumo_svg = f"""
            <svg viewBox="0 0 550 320" xmlns="http://www.w3.org/2000/svg">
                <!-- Nuage supérieur gauche : tracé qui se redessine en boucle de 30s -->
                <g stroke="{ink_deep}" stroke-width="1.4" fill="none" opacity="0.6" stroke-linecap="round">
                    <path d="M20,60 C35,45 50,50 65,42 C80,30 100,32 110,48 C125,40 145,55 135,68"
                          stroke-dasharray="{dash_len}" stroke-dashoffset="{dash_offset}" />
                    <path d="M30,72 Q 80,80 140,70" stroke-dasharray="25,5" stroke-width="1.1" />
                </g>
                <!-- Nuage supérieur droit -->
                <g stroke="{ink_deep}" stroke-width="1.4" fill="none" opacity="0.45" stroke-linecap="round">
                    <path d="M420,50 C440,35 460,40 475,30 C495,20 515,25 525,45" />
                    <path d="M410,62 Q 470,70 530,58" stroke-dasharray="20,4" stroke-width="1.0" />
                </g>
                <!-- Nuage inférieur gauche -->
                <g stroke="{ink_deep}" stroke-width="1.2" fill="none" opacity="0.4" stroke-linecap="round">
                    <path d="M15,240 C35,225 55,230 70,220 C90,210 110,215 120,235" />
                </g>
                <!-- Cartouche et Sceau Signature japonais bas droit -->
                <g transform="translate(460, 230)" opacity="0.55">
                    <rect x="0" y="0" width="60" height="60" fill="none" stroke="{ink_deep}" stroke-width="1.2" stroke-dasharray="4,2" />
                    <text x="30" y="26" fill="{ink_deep}" font-size="14" font-family="Georgia" text-anchor="middle" font-weight="bold">雲</text>
                    <text x="30" y="48" fill="{ink_deep}" font-size="14" font-family="Georgia" text-anchor="middle" font-weight="bold">気</text>
                </g>
            </svg>
            """
            svg_b64 = base64.b64encode(kumo_svg.encode('utf-8')).decode('utf-8')

            self.monitor_container.content = ft.Container(
                width=550, height=320, border_radius=35,
                bgcolor="#E0E5EC",
                shadow=ft.BoxShadow(
                    spread_radius=2, blur_radius=35, color="#BEC3C9", offset=ft.Offset(16, 16)
                ),
                content=ft.Stack([
                    # Toile de fond calligraphique
                    ft.Image(src_base64=svg_b64, width=550, height=320, fit=ft.ImageFit.COVER),
                    # Cartouche Sceau traditionnel haut gauche
                    ft.Container(
                        left=30, top=25,
                        width=34, height=34,
                        border=ft.border.all(1.5, ink_deep),
                        alignment=ft.alignment.center,
                        content=ft.Text("雲", size=18, color=ink_deep, font_family="Georgia", weight=ft.FontWeight.BOLD)
                    ),
                    # Horloge centrale
                    ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(delta_str, size=62, font_family="Georgia", weight=ft.FontWeight.W_100, color="#2D3436"),
                            ft.Container(width=50, height=1, bgcolor=ink_deep, opacity=0.3),
                            ft.Text(
                                "K U M O   Z E N",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ink_deep,
                                style=ft.TextStyle(letter_spacing=6)
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
                    )
                ])
            )

        # Actualisation immédiate du conteneur dans Flet
        self.page.update()

    def stop_timer(self, e):
        fran = self.state["config"].get("franchise_min", 30)
        now_dt = datetime.now()
        eff = calculate_duration(self.state["timer_start_dt"].time(), now_dt.time(), 0, fran)
        df = load_data_db()
        fait_h = 0.0
        if not df.empty:
            fait_h = df[df['Date'].dt.date == now_dt.date()]['Effectif_h'].sum()
        total = fait_h + eff

        if total >= self.state["config"].get("objectif_h", 7.0):
            self.finaliser_session(eff, self.state["timer_activity"], "Objectif atteint")
        else:
            self.open_modal_cloture(eff, total)

    def finaliser_session(self, duree, activite, commentaire):
        save_entry_db({
            "Date": pd.to_datetime(datetime.now().date()),
            "Arrivée": self.state["timer_start_dt"].strftime("%H:%M"),
            "Départ": datetime.now().strftime("%H:%M"),
            "Pause": 0, "Activité": activite, "Commentaire": commentaire,
            "Effectif_h": duree, "Solde_h": 0
        })
        self.state["timer_active"] = False
        self.state["elapsed_seconds"] = 0
        self.btn_start.visible = True
        self.btn_stop.visible = False
        self.btn_pause.visible = False
        self.act_select.disabled = False
        self.txt_time_display.value = "00:00:00"

        # MàJ Game
        g = self.state["game"]
        g["counters"]["total_hours"] += duree
        g["counters"]["days_logged"] += 1
        g, _ = update_streak_logic(g)
        g = check_achievements(g)
        save_game_data(g)

        self.refresh_dashboard()
        self.refresh_sidebar()
        self.page.update()

    # --- DIALOGUES ---
    def open_modal_cloture(self, eff, total):
        obj = self.state["config"].get("objectif_h", 7.0)
        n_act = ft.Dropdown(
            label="Nouvelle activité",
            options=[ft.dropdown.Option(a) for a in self.state["config"]["activites"]],
            value=self.state["config"]["activites"][0]
        )

        def on_continue(e):
            save_entry_db({
                "Date": pd.to_datetime(datetime.now().date()),
                "Arrivée": self.state["timer_start_dt"].strftime("%H:%M"),
                "Départ": datetime.now().strftime("%H:%M"),
                "Pause": 0, "Activité": self.state["timer_activity"],
                "Commentaire": "Segment terminé", "Effectif_h": eff, "Solde_h": 0
            })
            self.state["timer_start_dt"] = datetime.now()
            self.state["timer_activity"] = n_act.value
            self.dlg_cloture.open = False
            self.page.update()

        def on_deficit(e):
            self.dlg_cloture.open = False
            self.finaliser_session(eff, self.state["timer_activity"], "Déficit accepté")

        def on_admin(e):
            comp = max(0.0, obj - total)
            self.dlg_cloture.open = False
            self.finaliser_session(eff + comp, "Administration", "Complété automatiquement")

        self.dlg_cloture = ft.AlertDialog(
            title=ft.Text("🎯 Bilan de session"),
            content=ft.Column([
                ft.Text(f"Cumul journée : {total:.2f}h / {obj}h"),
                ft.Divider(),
                ft.Text("🚀 Continuer le travail :"),
                n_act,
                ft.ElevatedButton("VALIDER ET ENCHAÎNER", on_click=on_continue, bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE),
                ft.Divider(),
                ft.Text("🛑 Clôturer la journée :"),
                ft.Row([
                    ft.ElevatedButton("📉 DÉFICIT", on_click=on_deficit),
                    ft.ElevatedButton(f"🤖 ADMIN (+{max(0.0, obj - total):.2f}h)", on_click=on_admin)
                ])
            ], tight=True),
            actions=[]
        )
        self.page.dialog = self.dlg_cloture
        self.dlg_cloture.open = True
        self.page.update()

    def trigger_random_pause(self):
        it = random.choice(CATALOGUE_RECUPS)
        self.open_pause_modal(it)

    def open_pause_modal(self, it):
        def on_val(e):
            g = self.state["game"]
            g["vitality_ener"] = g.get("vitality_ener", 0) + 15
            cnt = g.setdefault("counters", {})
            cnt["pauses_clicked"] = cnt.get("pauses_clicked", 0) + 1

            # Progression du Contrat Barista (si actif)
            contrat_msg = ""
            contrat = g.get("active_contract")
            if contrat:
                today_str = str(datetime.now().date())
                if contrat.get("last_date") != today_str:
                    contrat["last_date"] = today_str
                    contrat["pauses_today"] = 0

                contrat["pauses_today"] = contrat.get("pauses_today", 0) + 1
                
                # 2 pauses requises pour valider la journée
                if contrat["pauses_today"] >= 2:
                    contrat["days_done"] = contrat.get("days_done", 0) + 1
                    contrat["pauses_today"] = 0
                    if contrat["days_done"] >= contrat.get("target_days", 3):
                        # Objectif atteint : versement des 300 ⚡
                        g["vitality_ener"] += 300
                        g["active_contract"] = None
                        contrat_msg = " | 🎉 Contrat Barista validé (+300 ⚡) !"
                    else:
                        contrat_msg = f" | ☕ Contrat Barista : Jour {contrat['days_done']}/3 validé !"

            self.state["game"] = check_achievements(g)
            save_game_data(self.state["game"])

            # Fermeture de la boîte de dialogue et mise à jour
            self.dlg_pause.open = False
            self.refresh_vitalite()
            self.refresh_dashboard()
            self.refresh_sidebar()

            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Pause active validée (+15 ⚡){contrat_msg}"),
                bgcolor=ft.colors.AMBER_800 if contrat_msg else ft.colors.GREEN_700
            )
            self.page.snack_bar.open = True
            self.page.update()

        # Chemin de l'image de l'exercice
        p = get_resource_path(os.path.join("assets", "exercices", it.get("img", "")))
        
        # Aperçu visuel : image locale si disponible, sinon affichage de l'icône grand format
        if os.path.exists(p):
            visuel = ft.Image(
                src=p,
                width=450,
                height=260,
                fit=ft.ImageFit.CONTAIN,
                border_radius=12
            )
        else:
            visuel = ft.Container(
                content=ft.Text(it.get("icon", "🧘"), size=70),
                width=450,
                height=180,
                alignment=ft.alignment.center,
                bgcolor=ft.colors.BLUE_GREY_50,
                border_radius=12
            )

        # Conteneur dimensionné pour éviter que la modale ne soit rétrécie
        content_box = ft.Container(
            width=500,
            padding=10,
            content=ft.Column(
                controls=[
                    visuel,
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    ft.Text(
                        it.get("desc", ""),
                        size=15,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.colors.BLUE_GREY_900
                    ),
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    ft.ElevatedButton(
                        "✅ VALIDER L'EXERCICE (+15 ⚡)",
                        icon=ft.icons.CHECK_CIRCLE,
                        on_click=on_val,
                        bgcolor=ft.colors.GREEN_600,
                        color=ft.colors.WHITE,
                        height=48,
                        width=float("inf")
                    )
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            )
        )

        self.dlg_pause = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Text(f"{it.get('icon', '')} {it.get('title', 'Pause Active')}", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(it.get("cat", "Récup"), size=12, color=ft.colors.INDIGO_700, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.colors.INDIGO_50,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=15
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            content=content_box
        )
        self.page.dialog = self.dlg_pause
        self.dlg_pause.open = True
        self.page.update()

    def open_vortex_modal(self):
        def on_buy_vortex(e):
            g = self.state["game"]
            ener = g.get("vitality_ener", 0)
            if ener >= 300:
                g["vitality_ener"] -= 300
                inv = g.setdefault("inventory", {})
                inv["streak_fixer"] = inv.get("streak_fixer", 0) + 1
                save_game_data(g)
                self.dlg_vortex.open = False
                self.refresh_vitalite()
                self.refresh_sidebar()
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("🌀 Relique temporelle acquise (+1 Gel de série) !"),
                    bgcolor=ft.colors.INDIGO_700
                )
                self.page.snack_bar.open = True
            else:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Énergie insuffisante (Requis: 300 ⚡ | Disponible: {ener} ⚡)"),
                    bgcolor=ft.colors.RED_700
                )
                self.page.snack_bar.open = True
            self.page.update()

        ener_actuelle = self.state["game"].get("vitality_ener", 0)
        self.dlg_vortex = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Text("🌀 Vortex Arabica", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"{ener_actuelle} ⚡", size=16, color=ft.colors.AMBER_700, weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            content=ft.Container(
                width=420,
                padding=10,
                content=ft.Column([
                    ft.Text(
                        "Cette relique permet de geler et restaurer une série de travail rompue par un oubli de pointage.",
                        size=14, color=ft.colors.GREY_800
                    ),
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    ft.Container(
                        padding=12,
                        bgcolor=ft.colors.INDIGO_50,
                        border_radius=8,
                        content=ft.Row([
                            ft.Icon(ft.icons.SHIELD_MOON, color=ft.colors.INDIGO_600),
                            ft.Text("Effet : +1 Bouclier Temporel (Inventaire)", weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_900)
                        ])
                    ),
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    ft.ElevatedButton(
                        "ACQUÉRIR LA RELIQUE (-300 ⚡)",
                        icon=ft.icons.SHOPPING_BAG,
                        on_click=on_buy_vortex,
                        bgcolor=ft.colors.INDIGO_600,
                        color=ft.colors.WHITE,
                        width=float("inf"),
                        height=45
                    )
                ], tight=True)
            )
        )
        self.page.dialog = self.dlg_vortex
        self.dlg_vortex.open = True
        self.page.update()

    # --- BOUTIQUE DE LA RÉCUP' ---
    def render_shop_cards(self, filter_kw=""):
        self.grid_shop.controls.clear()
        words = [w.strip().lower() for w in filter_kw.split() if w.strip()]

        for it in CATALOGUE_RECUPS:
            match = True
            if words:
                match = any(
                    any(w in k for k in it["keywords"]) or
                    w in it["title"].lower() or
                    w in it["cat"].lower()
                    for w in words
                )
            if match:
                def make_launch(item=it):
                    def _l(e): self.open_pause_modal(item)
                    return _l

                card = ft.Card(
                    content=ft.Container(
                        padding=15,
                        alignment=ft.alignment.center,
                        content=ft.Column([
                            ft.Text(it["icon"], size=30),
                            ft.Text(it["title"], weight=ft.FontWeight.BOLD),
                            ft.Text(it["desc"], size=11, color=ft.colors.GREY_600, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.ElevatedButton("Lancer", on_click=make_launch(), width=float("inf"))
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
                self.grid_shop.controls.append(card)
        self.page.update()

    # --- SANCTUAIRE DE VITALITÉ ---
    def refresh_vitalite(self):
        g = self.state["game"]
        self.txt_ener.value = f"{g.get('vitality_ener', 0)} ⚡"
        self.txt_pods.value = f"{g['inventory'].get('joker_coffe', 0)} ☕"

    def buy_capsule(self, e):
        g = self.state["game"]
        if g["vitality_ener"] >= 50:
            g["vitality_ener"] -= 50
            g["inventory"]["joker_coffe"] += 1
            save_game_data(g)
            self.refresh_vitalite()
            self.page.update()
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("Énergie insuffisante !"), bgcolor=ft.colors.RED_700)
            self.page.snack_bar.open = True
            self.page.update()

    # --- CONTRAT BARISTA CORRIGÉ ---
    def sign_contract(self, e):
        g = self.state["game"]
        ener = g.get("vitality_ener", 0)
        contrat_actuel = g.get("active_contract")

        # Vérification si un contrat est déjà en cours
        if contrat_actuel is not None:
            jours_faits = contrat_actuel.get("days_done", 0)
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Contrat déjà actif : Jour {jours_faits}/3 en cours !"),
                bgcolor=ft.colors.AMBER_900
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Vérification des réserves d'énergie
        if ener < 100:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Énergie insuffisante ! 100 ⚡ requis pour signer le contrat."),
                bgcolor=ft.colors.RED_700
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Signature du contrat
        g["vitality_ener"] -= 100
        g["active_contract"] = {
            "days_done": 0,
            "target_days": 3,
            "pauses_today": 0,
            "last_date": str(datetime.now().date())
        }
        save_game_data(g)
        self.refresh_vitalite()
        self.refresh_sidebar()
        self.page.snack_bar = ft.SnackBar(
            ft.Text("☕ Contrat Barista signé (-100 ⚡) ! Tenez 3 jours avec 2 pauses/j pour remporter 300 ⚡."),
            bgcolor=ft.colors.GREEN_700
        )
        self.page.snack_bar.open = True
        self.page.update()

    def brew_coffee(self, e):
        g = self.state["game"]
        if g["inventory"].get("joker_coffe", 0) <= 0:
            return

        g["inventory"]["joker_coffe"] -= 1
        save_game_data(g)
        self.refresh_vitalite()

        # Loterie 6 prix
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

        g["vitality_ener"] += g_e
        if g_f > 0:
            g["inventory"]["streak_fixer"] = g["inventory"].get("streak_fixer", 0) + 1
        save_game_data(g)
        self.refresh_vitalite()

        self.coffee_reveal_area.visible = True
        self.coffee_reveal_area.content = ft.Container(
            padding=20, border_radius=12, border=ft.border.all(3, color), bgcolor=ft.colors.WHITE,
            content=ft.Column([
                ft.Text(nom, size=24, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(m_msg, weight=ft.FontWeight.BOLD),
                ft.Text(f"{'+' if g_e>0 else ''}{g_e} ⚡" if g_e != 0 else "0 ⚡", size=32, weight=ft.FontWeight.BOLD),
                ft.Text(f'"{c_msg}"', italic=True)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        self.page.update()

    # --- DASHBOARD & HISTORIQUE ---
    def refresh_dashboard(self):
        df = load_data_db()
        obj_h = self.state["config"].get("objectif_h", 7.0)
        self.table_journal.rows.clear()

        if not df.empty:
            tot = df['Effectif_h'].sum()
            self.txt_total_hours_report.value = f"Total des heures enregistrées : {tot:.2f} h"

            for _, r in df.head(20).iterrows():
                row_id = r['id']
                def make_del(i=row_id):
                    def _d(e):
                        delete_entry_db(i)
                        self.refresh_dashboard()
                        self.refresh_sidebar()
                    return _d

                self.table_journal.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(r['Date'].strftime("%d/%m/%Y"))),
                        ft.DataCell(ft.Text(f"{r['Arrivée']} - {r['Départ']}")),
                        ft.DataCell(ft.Text(f"{r['Pause']}m")),
                        ft.DataCell(ft.Text(str(r['Activité']))),
                        ft.DataCell(ft.Text(str(r['Commentaire']))),
                        ft.DataCell(ft.Text(f"{r['Effectif_h']:.2f}h")),
                        ft.DataCell(ft.IconButton(ft.icons.DELETE_OUTLINE, icon_color=ft.colors.RED_400, on_click=make_del()))
                    ])
                )

            # Remplissage Graphique barres
            df_recent = df.sort_values("Date").tail(7)
            groups = []
            x_labels = []
            for idx, (_, r) in enumerate(df_recent.iterrows()):
                groups.append(
                    ft.BarChartGroup(
                        x=idx,
                        bar_rods=[ft.BarChartRod(from_y=0, to_y=r['Effectif_h'], color=ft.colors.INDIGO_500, width=18)]
                    )
                )
                x_labels.append(ft.ChartAxisLabel(value=idx, label=ft.Text(r['Date'].strftime("%d/%m"), size=10)))
            self.chart_bars.bar_groups = groups
            self.chart_bars.bottom_axis.labels = x_labels

        self.page.update()

    # --- ONGLETS ---
    def build_pointage_tab(self):
        in_date = ft.TextField(label="Date", value=datetime.now().strftime("%Y-%m-%d"), width=120)
        in_t1 = ft.TextField(label="Arrivée", value="08:30", width=80)
        in_t2 = ft.TextField(label="Départ", value="17:00", width=80)
        in_p = ft.TextField(label="Pause (min)", value="45", width=90)
        in_act = ft.Dropdown(label="Activité", options=[ft.dropdown.Option(a) for a in self.state["config"]["activites"]], value=self.state["config"]["activites"][0], width=140)

        def on_submit_manual(e):
            try:
                t1m = datetime.strptime(in_t1.value, "%H:%M").time()
                t2m = datetime.strptime(in_t2.value, "%H:%M").time()
                eff = calculate_duration(t1m, t2m, int(in_p.value), self.state["config"]["franchise_min"])
                save_entry_db({
                    "Date": pd.to_datetime(in_date.value), "Arrivée": in_t1.value, "Départ": in_t2.value,
                    "Pause": int(in_p.value), "Activité": in_act.value, "Commentaire": "Manuel",
                    "Effectif_h": eff, "Solde_h": 0
                })
                self.refresh_dashboard()
                self.refresh_sidebar()
                self.page.snack_bar = ft.SnackBar(ft.Text("Entrée manuelle enregistrée !"), bgcolor=ft.colors.GREEN_700)
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as err:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Erreur : {err}"), bgcolor=ft.colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()

        quick_t = ft.TextField(label="Heure de reprise", value="14:00", width=120)
        quick_act = ft.Dropdown(label="Activité", options=[ft.dropdown.Option(a) for a in self.state["config"]["activites"]], value=self.state["config"]["activites"][0], width=140)
        quick_memo = ft.TextField(label="Note / Message pour demain", multiline=True, width=350)

        def on_quick_exit(e):
            if quick_memo.value:
                save_memo(quick_memo.value)
            t_rep = datetime.strptime(quick_t.value, "%H:%M").time()
            eff = calculate_duration(t_rep, datetime.now().time(), 0, self.state["config"]["franchise_min"])
            save_entry_db({
                "Date": pd.to_datetime(datetime.now().date()), "Arrivée": quick_t.value,
                "Départ": datetime.now().strftime("%H:%M"), "Pause": 0, "Activité": quick_act.value,
                "Commentaire": "Fin Rapide", "Effectif_h": eff, "Solde_h": 0
            })
            save_game_data(self.state["game"])
            self.page.window.close()

        abs_d1 = ft.TextField(label="Début (AAAA-MM-JJ)", value=datetime.now().strftime("%Y-%m-%d"), width=150)
        abs_d2 = ft.TextField(label="Fin (AAAA-MM-JJ)", value=datetime.now().strftime("%Y-%m-%d"), width=150)
        abs_motif = ft.Dropdown(label="Motif", options=[ft.dropdown.Option(m) for m in ["RTT", "FÉRIÉ", "CONGÉS ANNUELS", "MALADIE"]], value="RTT", width=150)

        def on_val_absence(e):
            try:
                d1 = datetime.strptime(abs_d1.value, "%Y-%m-%d").date()
                d2 = datetime.strptime(abs_d2.value, "%Y-%m-%d").date()
                delta = (d2 - d1).days + 1
                curr = d1
                while curr <= d2:
                    save_entry_db({
                        "Date": pd.to_datetime(curr), "Arrivée": "00:00", "Départ": "00:00",
                        "Pause": 0, "Activité": abs_motif.value, "Commentaire": "Absence",
                        "Effectif_h": 7.0, "Solde_h": 0
                    })
                    curr += timedelta(days=1)
                reward = 20 * delta if abs_motif.value in ["RTT", "FÉRIÉ", "CONGÉS ANNUELS"] else 0
                self.state["game"]["vitality_ener"] += reward
                save_game_data(self.state["game"])
                self.refresh_dashboard()
                self.refresh_vitalite()
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Absence enregistrée (+{reward} ⚡)"), bgcolor=ft.colors.GREEN_700)
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as err:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Erreur : {err}"), bgcolor=ft.colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()

        return ft.Container(
            padding=20,
            content=ft.ListView([
                ft.Row([self.design_choice, self.act_select], alignment=ft.MainAxisAlignment.CENTER),
                self.monitor_container,
                ft.Row([self.btn_start, self.btn_stop, self.btn_pause], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.ExpansionTile(
                    title=ft.Text("📝 Saisie Manuelle"),
                    controls=[ft.Row([in_date, in_t1, in_t2, in_p, in_act, ft.ElevatedButton("Enregistrer", on_click=on_submit_manual)])]
                ),
                ft.ExpansionTile(
                    title=ft.Text("🚪 Départ Rapide"),
                    controls=[ft.Column([ft.Row([quick_t, quick_act]), quick_memo, ft.ElevatedButton("💾 CLÔTURER LA JOURNÉE", on_click=on_quick_exit)])]
                ),
                ft.ExpansionTile(
                    title=ft.Text("🏖️ Déclaration d'Absence"),
                    controls=[ft.Row([abs_d1, abs_d2, abs_motif, ft.ElevatedButton("Valider", on_click=on_val_absence)])]
                ),
            ], spacing=15)
        )

    def build_vitalite_tab(self):
        return ft.Container(
            padding=20,
            content=ft.ListView([
                ft.Row([
                    ft.Card(content=ft.Container(padding=15, content=ft.Column([ft.Text("ÉNERGIE TOTALE"), self.txt_ener]))),
                    ft.Card(content=ft.Container(padding=15, content=ft.Column([ft.Text("DOSETTES EN STOCK"), self.txt_pods]))),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text("🛍️ Le Comptoir du Barista", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Card(content=ft.Container(padding=12, width=240, content=ft.Column([
                        ft.Text("Capsule Grand Cru", weight=ft.FontWeight.BOLD),
                        ft.Text("Extraction machine.", size=11),
                        ft.ElevatedButton("ACHETER (-50⚡)", on_click=self.buy_capsule)
                    ]))),
                    ft.Card(content=ft.Container(padding=12, width=240, content=ft.Column([
                        ft.Text("Contrat Barista", weight=ft.FontWeight.BOLD),
                        ft.Text("Misez 100⚡ sur 3j.", size=11),
                        ft.ElevatedButton("SIGNER (-100⚡)", on_click=self.sign_contract)
                    ]))),
                    ft.Card(content=ft.Container(padding=12, width=240, content=ft.Column([
                        ft.Text("Vortex Arabica", weight=ft.FontWeight.BOLD),
                        ft.Text("Réparez votre série.", size=11),
                        ft.ElevatedButton("ACTIVER (-300⚡)", on_click=lambda e: self.open_vortex_modal())
                    ]))),
                ]),
                ft.Divider(),
                ft.Text("☕ Percolateur Haute Pression", size=18, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("PRÉPARER MON CAFÉ (Consomme 1 Dosette)", on_click=self.brew_coffee, bgcolor=ft.colors.BROWN_600, color=ft.colors.WHITE),
                self.coffee_reveal_area
            ], spacing=15)
        )

    def build_boutique_tab(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("🧘 Boutique de la Récup'", size=20, weight=ft.FontWeight.BOLD),
                self.search_recup,
                self.grid_shop
            ], expand=True)
        )

    def build_trophees_tab(self):
        xp = self.state["game"].get("xp", 0)
        items = []
        for tr in LISTE_TROPHEES:
            unl = tr["id"] in self.state["game"].get("achievements_unlocked", [])
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.CHECK_CIRCLE if unl else ft.icons.LOCK, color=ft.colors.GREEN if unl else ft.colors.GREY_400),
                    title=ft.Text(tr["name"]),
                    subtitle=ft.Text(f"{tr['desc_mission']} (+{tr['xp']} XP)"),
                    opacity=1.0 if unl else 0.4
                )
            )
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("🏆 Galerie des Succès", size=20, weight=ft.FontWeight.BOLD),
                ft.ProgressBar(value=min(xp / 3000, 1.0)),
                ft.Text(f"XP Totale : {xp} / 3000"),
                ft.ListView(items, expand=True)
            ], expand=True)
        )

    def build_journal_tab(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("📅 Historique des Saisies", size=20, weight=ft.FontWeight.BOLD),
                ft.ListView([self.table_journal], expand=True)
            ], expand=True)
        )

    def build_rapports_tab(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("📊 Rapports d'Activité", size=20, weight=ft.FontWeight.BOLD),
                self.txt_total_hours_report,
                self.chart_bars
            ], expand=True)
        )

    def build_config_tab(self):
        obj_in = ft.TextField(label="Objectif quotidien (h)", value=str(self.state["config"].get("objectif_h", 7.0)), width=150)
        fran_in = ft.TextField(label="Franchise pause (min)", value=str(self.state["config"].get("franchise_min", 30)), width=150)

        unlocked_skins = self.state["game"].get("unlocked", ["Classique"])
        skin_dd = ft.Dropdown(
            label="Skin Optigotchi",
            options=[ft.dropdown.Option(s) for s in unlocked_skins],
            value=self.state["game"]["current"].get("skin", "Classique"),
            width=200
        )

        unlocked_packs = ["Stoïcisme"]
        for tr in LISTE_TROPHEES:
            if tr["id"] in self.state["game"].get("achievements_unlocked", []) and tr.get("pack_unlock"):
                unlocked_packs.append(tr["pack_unlock"])
        pack_dd = ft.Dropdown(
            label="Pack de Citations",
            options=[ft.dropdown.Option(p) for p in unlocked_packs],
            value=self.state["game"]["current"].get("pack", "Stoïcisme"),
            width=200
        )

        def save_conf(e):
            self.state["config"]["objectif_h"] = float(obj_in.value)
            self.state["config"]["franchise_min"] = int(fran_in.value)
            save_config(self.state["config"])
            self.state["game"]["current"]["skin"] = skin_dd.value
            self.state["game"]["current"]["pack"] = pack_dd.value
            save_game_data(self.state["game"])
            self.current_quote = None
            self.refresh_sidebar()
            self.page.snack_bar = ft.SnackBar(ft.Text("Configuration enregistrée !"), bgcolor=ft.colors.GREEN_700)
            self.page.snack_bar.open = True
            self.page.update()

        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("⚙️ Paramètres & Personnalisation", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([obj_in, fran_in]),
                ft.Row([skin_dd, pack_dd]),
                ft.ElevatedButton("SAUVEGARDER", on_click=save_conf, bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE)
            ])
        )