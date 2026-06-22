import os
from pathlib import Path
from core.log import log
from dotenv import dotenv_values
from core import messages as m

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

DEFAULT_CONFIG = {
    m.VERBOSE: "False",
    m.APP_RUNNING: "True",
    m.PORT: "48051",
    m.IPIA: "0.0.0.0",
    m.PORTIA: "48050",
    m.DEFAUT_TIMEOUT: "5", # Lembre-se de verificar se não era para ser DEFAULT_TIMEOUT
    m.HELLO_TIMEOUT: "5",
    m.BOT_INTERVAL: "3"
}

if not ENV_FILE.exists():
    with open(ENV_FILE, "w") as file:
        for key, value in DEFAULT_CONFIG.items():
            file.write(f"{key}={value}\n")
    log(f"Arquivo {ENV_FILE} não encontrado. Gerado com os valores padrão do CEDRI.", level=1)

settings = {
    **DEFAULT_CONFIG,
    **dotenv_values(ENV_FILE)
}

INITIAL_ROUTES = [
    ("LERM", 44.5, 68),
    ("CHARGE", 2.6, 2.5),
    ("START", 0, 0),
    ("LE", 26.5, 0),
    ("LEI", 10.5, 1.5),
    ("L2I", 6, 1.5),
    ("LCGAV", 19, -10),
    ("LCA", 18.5, -15.5),
    ("LIC", 18.5, -16),
    ("LSE", 10.5, -2.5),
    ("LCAR", 6, -1.5),
    ("RP", 49, -2.5),
    ("CO-WORK", 48, -8),
    ("AEESTIG", 41.5, -7.5),
    ("AUDITOR", 65, -13),
    ("WC1", 68, -65),
    ("STARTUP", 42.5, 34),
    ("WC2", 42, 28),
    ("NUCLEOS", 40.5, 8),
    ("LMC1", 31.5, 62.5),
    ("LMFH", 31.5, 68.5),
    ("GICOS", 15, 60),
    ("LMCM", 10.5, 60),
    ("LM2", 15, 63.5),
    ("LG", 11, 64),
    ("SOO1", 29.5, 31.5),
    ("LTM2-1", 29, 27.5),
    ("LTM2-2", 29, 28.5),
    ("CIMO", 15, 32),
    ("LTM3", 14.5, 29),
    ("FABLAB", 19, 32),
    ("LQA", -7, 33.5),
    ("LPQ", -7, 30.5)
]


MAX_POPULATION = 300.0
MAX_TIME_SECONDS = 3600.0
NUM_CLASSES = 60
GHOST_ROOM_PENALTY = -9999.0

# Parâmetros Tradutor / LSTM
WINDOW_SIZE = 5
VECTOR_SIZE = 74
HOURS_IN_DAY = 24.0
DAYS_IN_YEAR = 365.0

# Parâmetros Reinforcement Learning & Sonhos
MAX_EXPERIENCES = 6000
DREAMS_COUNT = 3
DREAM_EPOCHS = 1
DREAM_CHECK_INTERVAL_SEC = 3

# Pesos de Recompensa (Reward)
REWARD_EMPTY_PENALTY = -0.2
REWARD_HELP_WEIGHT = 0.8
REWARD_POP_WEIGHT = 0.2
REWARD_HELP_FACTOR = 0.5