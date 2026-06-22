import sqlite3 as sqlite
from services.cedri_ia.client import ia_client

from core import messages as m
from config import settings, WINDOW_SIZE, VECTOR_SIZE, NUM_CLASSES

from pathlib import Path

current_file = Path(__file__).resolve()
BASE_DIR = current_file.parent.parent.parent

DB_PATH = BASE_DIR / "data" / "data.db"

from core.log import log

DEFAULT_MODEL = {
  "learning_type": "reinforcement",
  "rl_params": {
    "gamma": 0.99,
    "epsilon_initial": 1.0,
    "epsilon_decay": 0.995,
    "buffer_size": 10000
  },
  "architecture": {
    "layers": [
      {
        "type": "LSTM",
        "units": 128,
        "activation": "tanh",
        "input_shape": [WINDOW_SIZE, VECTOR_SIZE]
      },
      {
        "type": "Dense",
        "units": 256,
        "activation": "relu"
      },
      {
        "type": "Dense",
        "units": NUM_CLASSES,
        "activation": "linear"
      }
    ]
  },
  "training_config": {
    "learning_rate": 0.005,
    "loss_function": "mse",
    "optimizer": "adam"
  }
}

def createToken(token : str):
    """creates a new one."""
    try:
        with sqlite.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens (token) VALUES (?)", (token,))
            conn.commit()
            log("New token created successfully.")
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return None

def getToken(new_token : bool = False):
    """Retrieves the last created token from the database, or creates a new one if none exists."""
    try:
        with sqlite.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM tokens ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            if result and not settings[m.NEW] and not new_token:
                return result[0]
            else:
                response = ia_client.create_model(DEFAULT_MODEL)
                token = response.get("token")
                log("Creating token")
                if token:
                    createToken(token)
                    return token
                else:
                    log("Failed to create token:", response, level=4)
                    return None
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return None
    
def deleteToken(token : str):
    """Deletes the current token from the database."""
    try:
        with sqlite.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tokens WHERE token = ?", (token,))
            conn.commit()
            log("Token deleted successfully.")
    except sqlite.Error as e:
        log(f"Database error: {e}", level=3)
        return None