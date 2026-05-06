from core import messages
from core.log import log
from services.cedri_ia.client import ia_client

def run():
    is_online = ia_client.hello()
    log("IA Server online? "+ ("[Yes]" if is_online else "[No]"), 0 if is_online else 4)

    if not is_online:
        log("IA Manager is not online. The ip and ports are correct?", 4)
        return False
    return True



