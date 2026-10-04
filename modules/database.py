import sqlite3
import pandas as pd
import os
from .constants import DB_FILE, CSV_FILE_OLD

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            arrivee TEXT,
            depart TEXT,
            pause INTEGER,
            activite TEXT,
            commentaire TEXT,
            effectif_h REAL,
            solde_h REAL
        )
    ''')
    conn.commit()

    cur.execute('SELECT COUNT(*) FROM journal')
    count = cur.fetchone()[0]
    if count == 0 and os.path.exists(CSV_FILE_OLD):
        try:
            try:
                df_csv = pd.read_csv(CSV_FILE_OLD, sep=None, engine='python', encoding='utf-8')
            except UnicodeDecodeError:
                df_csv = pd.read_csv(CSV_FILE_OLD, sep=None, engine='python', encoding='latin-1')

            df_csv.rename(columns={'ArrivÃ©e': 'Arrivée', 'DÃ©part': 'Départ', 'ActivitÃ©': 'Activité'}, inplace=True)
            for _, row in df_csv.iterrows():
                if pd.isna(row.get('Date')): continue
                cur.execute('''
                    INSERT INTO journal (date, arrivee, depart, pause, activite, commentaire, effectif_h, solde_h)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(row.get('Date')),
                    str(row.get('Arrivée', '00:00')),
                    str(row.get('Départ', '00:00')),
                    int(row.get('Pause', 0)) if pd.notna(row.get('Pause')) else 0,
                    str(row.get('Activité', 'Autre')),
                    str(row.get('Commentaire', '')) if pd.notna(row.get('Commentaire')) else '',
                    float(row.get('Effectif_h', 0.0)) if pd.notna(row.get('Effectif_h')) else 0.0,
                    float(row.get('Solde_h', 0.0)) if pd.notna(row.get('Solde_h')) else 0.0
                ))
            conn.commit()
        except Exception as e:
            print(f"Erreur migration CSV : {e}")

    conn.close()

def load_data_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM journal ORDER BY date DESC, id DESC", conn)
        conn.close()
        if not df.empty:
            df['Date'] = pd.to_datetime(df['date'])
            df = df.rename(columns={
                'arrivee': 'Arrivée', 'depart': 'Départ', 'pause': 'Pause',
                'activite': 'Activité', 'commentaire': 'Commentaire',
                'effectif_h': 'Effectif_h', 'solde_h': 'Solde_h'
            })
            cols = ['id', 'Date', 'Arrivée', 'Départ', 'Pause', 'Activité', 'Commentaire', 'Effectif_h', 'Solde_h']
            return df[[c for c in cols if c in df.columns]]
        return pd.DataFrame(columns=['id', 'Date', 'Arrivée', 'Départ', 'Pause', 'Activité', 'Commentaire', 'Effectif_h', 'Solde_h'])
    except Exception:
        return pd.DataFrame(columns=['id', 'Date', 'Arrivée', 'Départ', 'Pause', 'Activité', 'Commentaire', 'Effectif_h', 'Solde_h'])

def save_entry_db(entry):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    d = entry['Date']
    if hasattr(d, 'strftime'): d = d.strftime("%Y-%m-%d")
    cur.execute('''
        INSERT INTO journal (date, arrivee, depart, pause, activite, commentaire, effectif_h, solde_h)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(d), str(entry['Arrivée']), str(entry['Départ']), int(entry['Pause']),
        str(entry['Activité']), str(entry.get('Commentaire', '')),
        float(entry['Effectif_h']), float(entry.get('Solde_h', 0.0))
    ))
    conn.commit()
    conn.close()

def delete_entry_db(entry_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM journal WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def update_db_from_df(df_to_save):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM journal")
    for _, row in df_to_save.iterrows():
        d = row['Date']
        if hasattr(d, 'strftime'): d = d.strftime("%Y-%m-%d")
        cur.execute('''
            INSERT INTO journal (date, arrivee, depart, pause, activite, commentaire, effectif_h, solde_h)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(d), str(row['Arrivée']), str(row['Départ']), int(row['Pause']),
            str(row['Activité']), str(row.get('Commentaire', '')),
            float(row['Effectif_h']), float(row.get('Solde_h', 0.0))
        ))
    conn.commit()
    conn.close()