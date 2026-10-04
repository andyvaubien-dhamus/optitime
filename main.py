import flet as ft
import threading
import time
import os
import sys

from modules.database import init_db
from modules.utils import load_config, load_game_data, save_game_data, get_resource_path
from modules.views import AppViews

def main(page: ft.Page):
    page.title = "OptiTime Desktop"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1180
    page.window.height = 840
    page.padding = 0

    # --- ENREGISTREMENT DU DOSSIER ASSETS DANS FLET ---
    assets_folder = get_resource_path("assets")
    page.assets_dir = assets_folder

    # Définition de l'icône de la fenêtre sous Windows
    icon_ico_path = os.path.join(assets_folder, "icon.ico")
    icon_png_path = os.path.join(assets_folder, "icon.png")
    if os.path.exists(icon_ico_path):
        page.window.icon = icon_ico_path
    elif os.path.exists(icon_png_path):
        page.window.icon = icon_png_path

    # Initialisation SQLite & Migration
    init_db()

    app_state = {
        "config": load_config(),
        "game": load_game_data(),
        "timer_active": False,
        "timer_start_dt": None,
        "elapsed_seconds": 0,
        "timer_activity": "Production"
    }

    views = AppViews(page, app_state)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(text="⏱️ Pointage", content=views.build_pointage_tab()),
            ft.Tab(text="⚡ Vitalité", content=views.build_vitalite_tab()),
            ft.Tab(text="🧘 Boutique", content=views.build_boutique_tab()),
            ft.Tab(text="🏆 Trophées", content=views.build_trophees_tab()),
            ft.Tab(text="📅 Journal", content=views.build_journal_tab()),
            ft.Tab(text="📊 Rapports", content=views.build_rapports_tab()),
            ft.Tab(text="⚙️ Config", content=views.build_config_tab()),
        ],
        expand=True
    )

    # Fonction de sortie propre
    def quit_app(e):
        save_game_data(app_state["game"])
        try:
            page.window.close()
        except Exception:
            sys.exit(0)

    # En-tête dynamique Sidebar : logo.png > icon.png + texte > texte seul
    logo_path = os.path.join(assets_folder, "logo.png")
    if os.path.exists(logo_path):
        header_widget = ft.Image(
            src=logo_path,
            height=45,
            fit=ft.ImageFit.CONTAIN
        )
    elif os.path.exists(icon_png_path):
        header_widget = ft.Row([
            ft.Image(src=icon_png_path, width=32, height=32, fit=ft.ImageFit.CONTAIN),
            ft.Text("OptiTime", size=20, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER)
    else:
        header_widget = ft.Text("⏱️ OptiTime", size=20, weight=ft.FontWeight.BOLD)

    sidebar = ft.Container(
        width=250,
        padding=15,
        bgcolor="#F8FAFC",
        border=ft.border.only(right=ft.BorderSide(1, "#E2E8F0")),
        content=ft.Column([
            header_widget,
            views.avatar_display,
            views.optigotchi_msg,
            ft.Divider(),
            views.memo_sidebar,
            views.sidebar_quote_box,
            ft.Divider(),
            ft.ElevatedButton(
                "❌ QUITTER",
                on_click=quit_app,
                bgcolor=ft.colors.RED_400,
                color=ft.colors.WHITE,
                width=float("inf")
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
    )

    page.add(
        ft.Row([sidebar, tabs], expand=True, spacing=0)
    )

    views.render_shop_cards("")
    views.refresh_vitalite()
    views.refresh_dashboard()
    views.refresh_sidebar()

    # Horloge temps réel (1s)
    def clock_thread():
        while True:
            time.sleep(1)
            views.update_clock_tick()

    threading.Thread(target=clock_thread, daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)