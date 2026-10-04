import streamlit.web.cli as stcli
import os, sys
import threading
import time
import subprocess

def resolve_path(path):
    if getattr(sys, "frozen", False):
        # Si on est dans l'exe, on utilise le dossier temporaire MEIPASS
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

# --- FONCTION MODE APP ---
def open_app_window():
    time.sleep(2) # Attendre que le serveur démarre
    url = "http://localhost:8501"
    # Tenter d'ouvrir en mode "App" (sans barre d'adresse)
    try:
        subprocess.Popen(f'start msedge --app={url}', shell=True)
    except:
        try:
            subprocess.Popen(f'start chrome --app={url}', shell=True)
        except:
            import webbrowser
            webbrowser.open(url)

if __name__ == "__main__":
    # 1. Configuration CRITIQUE pour éviter le "RuntimeError"
    # Cela force Streamlit à comprendre qu'il tourne en mode serveur headless
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    
    # 2. On lance le navigateur en fond
    threading.Thread(target=open_app_window, daemon=True).start()
    
    # 3. Chemin vers votre app
    # Attention: assurez-vous que "app.py" est bien le nom de votre script principal
    script_path = resolve_path("app.py") 
    
    # 4. Configuration des arguments Streamlit
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.port=8501",
        "--theme.base=light"
    ]
    
    # 5. Lancement
    sys.exit(stcli.main())