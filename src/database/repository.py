import sqlite3
from pathlib import Path
from core.log import log
from config import INITIAL_ROUTES

current_file = Path(__file__).resolve()
BASE_DIR = current_file.parent.parent.parent

DB_PATH = BASE_DIR / "data" / "data.db"

# ==========================================
# QUERIES DE CRIAÇÃO (SCHEMAS)
# ==========================================

CREATE_PATH_TBL = """CREATE TABLE IF NOT EXISTS paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER UNIQUE NOT NULL,
    name TEXT UNIQUE,
    x REAL NOT NULL,
    y REAL NOT NULL
)"""

CREATE_TOKEN_TBL = """CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL
)"""

# A Foreign Key agora aponta para o nosso location_id explícito
CREATE_MEMORIES_TBL = """CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    arrive_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    helping_time REAL DEFAULT 0.0,
    people_count INTEGER DEFAULT 0,
    used INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (location_id) REFERENCES paths (location_id)
)"""

CREATE_UNIQUE_PEOPLE_TBL = """CREATE TABLE IF NOT EXISTS unique_people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    person_id TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories (id),
    UNIQUE(memory_id, person_id) 
)"""

def start():
    """Initializes the database and creates necessary tables."""
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            cursor = conn.cursor()
            cursor.execute(CREATE_PATH_TBL)
            cursor.execute(CREATE_TOKEN_TBL)
            cursor.execute(CREATE_MEMORIES_TBL)
            cursor.execute(CREATE_UNIQUE_PEOPLE_TBL)

            routes_with_id = [
                (i + 1, route[0], route[1], route[2]) 
                for i, route in enumerate(INITIAL_ROUTES)
            ]
            
            cursor.executemany(
                "INSERT OR IGNORE INTO paths (location_id, name, x, y) VALUES (?, ?, ?, ?)", 
                routes_with_id
            )

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_used ON memories (used)")

            conn.commit()
            log("Database initialized successfully.", level=1)
            return True
    except sqlite3.Error as e:
        log(f"Database error: {e}", level=3)
        return False