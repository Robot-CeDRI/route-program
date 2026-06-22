import sqlite3
from pathlib import Path
from config import INITIAL_ROUTES
from core.log import log

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "data.db"

def sync_paths():
    log("Iniciando a sincronização dos paths com o BD...", level=1)
    
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS paths (
                id INTEGER PRIMARY KEY,
                name TEXT,
                x REAL NOT NULL,
                y REAL NOT NULL
            )""")
            
            cursor.execute("DELETE FROM paths")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='paths'")
            cursor.executemany(
                "INSERT INTO paths (name, x, y) VALUES (?, ?, ?)", 
                INITIAL_ROUTES
            )
            
            conn.commit()
            log("Tabela 'paths' atualizada com as configurações atuais com sucesso!", level=1)
    except sqlite3.Error as e:
        log(f"Falha ao sincronizar paths: {e}", level=3)

if __name__ == "__main__":
    sync_paths()