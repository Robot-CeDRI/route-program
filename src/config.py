import os
from core import log
from dotenv import dotenv_values
from core import messages as m

ENV_FILE = "../.env"
DEFAULT_CONFIG = {
    m.VERBOSE: "False",
    m.APP_RUNNING: "True",
    m.PORT: "48051",
    m.IPIA: "0.0.0.0",
    m.PORTIA: "48050",
    m.DEFAUT_TIMEOUT: "5",
    m.HELLO_TIMEOUT: "5",
    m.BOT_INTERVAL: "3"
}

if not os.path.exists(ENV_FILE):
    with open(ENV_FILE, "w") as file:
        for key, value in DEFAULT_CONFIG.items():
            file.write(f"{key}={value}\n")
    log(f"Arquivo {ENV_FILE} não encontrado. Gerado com os valores padrão do CEDRI.", level=1)

settings = {
    **DEFAULT_CONFIG,
    **dotenv_values(ENV_FILE)
}