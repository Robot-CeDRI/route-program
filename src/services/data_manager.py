from core.log import log
from services import auth_token

def run():
    log("Obtaining IA token...")
    token = auth_token.getToken()

    if token:
        log(f"Token obtained successfully: {token}.", level=1)
        return 
    else:        
        log("Failed to obtain token by all means, no IA exists.", level=4)
        return False

    return True

def sendData():
    pass