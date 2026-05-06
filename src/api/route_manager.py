from core import messages
from core.log import log
from services.cedri_ia.client import ia_client

HELLO_TIMEOUT = 5.0
BOT_INTERVAL = 3 # seconds between bot routes # 1 hour default

PROCESS_TEST = {
  "input": [
    1.5,
    2.3,
    0.8
  ],
  "session_id": "session-XYZ-123",
  "token": ""
}

def run():
    is_online = ia_client.hello()
    log("IA Server online? "+ ("[Yes]" if is_online else "[No]"), 0 if is_online else 4)

    if not is_online:
        log("IA Manager is not online. The ip and ports are correct?", 4)
        # Não significa que o programa precisa parar, caso ainda tenhamos rotas armazenadas devemos
        # continuar em ciclo, juntando dados para os próximos treinos.
        # Implementar depois
        return False
    
    return True

    
def stop():
    pass



