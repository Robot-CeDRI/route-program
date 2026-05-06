import sqlite3 as sqlite
from services.cedri_ia.client import ia_client

from core import messages as m
from config import settings

from core.log import log

DEFAULT_MODEL = {
  "architecture": {
    "layers": [
      {
        "activation": "relu",
        "input_shape": [
          19
        ],
        "type": "Dense",
        "units": 64
      },
      {
        "activation": "linear",
        "type": "Dense",
        "units": 2
      }
    ]
  },
  "learning_type": "supervised",
  "training_config": {
    "learning_rate": 0.001,
    "loss_function": "mse",
    "optimizer": "adam"
  }
}

CREATE_STRING = """CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL
)"""

def __createNewToken(token):
    """creates a new one."""
    try:
        with sqlite.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens (token) VALUES (?)", (token,))
            conn.commit()
            log("New token created successfully.")
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return None

def run():
    """Responsible for the tokens of the models"""
    log("Data Manager running.")
    try:
        with sqlite.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_STRING)
            conn.commit()
            log("Database initialized successfully.")
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return False
    return True

def getToken():
    """Retrieves the current token from the database, or creates a new one if none exists."""
    try:
        with sqlite.connect("data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM tokens ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            if result and not settings[m.NEW]:
                return result[0]
            else:
                response = ia_client.create_model(DEFAULT_MODEL)
                token = response.get("token")
                log("Creating token")
                if token:
                    __createNewToken(token)
                    return token
                else:
                    log("Failed to create token.", level=3)
                    return None
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return None
    
