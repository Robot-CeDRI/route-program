import time
import sqlite3
import threading

from services.cedri_ia.client import ia_client
from database.repository import DB_PATH
from config import settings
from core import messages as m
from core.log import log
from database import token_model

import tasks.metrics_sync as metrics_sync

MODEL_LOAD_DELAY = 1

def reset_memories_for_training():
    """Marca todos os dados do BD como 'used=0' para o novo modelo aprender."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET used = 0")
            conn.commit()
            log("Todas as memórias foram marcadas como 'used=0' para retreino.", level=1)
    except sqlite3.Error as e:
        log(f"Erro ao resetar memórias: {e}", level=3)

def run() -> str:
    """
    Carrega o modelo e retorna o status da operação:
    'READY', 'NEW_MODEL', 'UNREACHABLE', 'ERROR'
    """
    # 1. Tenta pingar a API (Inalcançável)
    if not ia_client.hello():
        return 'UNREACHABLE'

    token = settings.get(m.LAST_TOKEN)
    loaded = False
    
    while not loaded:
        log(f"Verificando status do modelo. Token: {token}", level=4)
        response = ia_client.check_model(token)

        if "detail" in response and not response.get("error"):
             log(f"Aviso de Validação: {response.get('detail')}", level=4)
             return 'ERROR'

        # 2. IA_MANAGER Online, mas token não existe (Token Inválido/Perdido)
        if response.get("error") is True:
            if "not found" in response.get("message", "").lower():
                log("Token é inválido ou foi perdido no IA_MANAGER!", level=3)
                
                # Deleta o antigo, pega um novo e salva no env
                token_model.deleteToken(token)
                new_token = token_model.getToken(new_token=True)
                settings[m.LAST_TOKEN] = new_token
                
                if new_token is None:
                    return 'ERROR'
                
                # Regras: resetar banco e acelerar treino
                reset_memories_for_training()
                log("Disparando rotina de treinamento assíncrona...", level=1)
                threading.Thread(target=metrics_sync.run, name="AsyncTrain").start()
                
                return 'NEW_MODEL'
                
            return 'ERROR'
        
        if response.get("loading") is True:
            log("O modelo está sendo carregado na RAM, aguarde...", level=4)
            time.sleep(MODEL_LOAD_DELAY)
            continue
        
        if response.get("loaded") is True:
            log("Modelo pronto para uso!", level=4)
            return 'READY'
        
        if response.get("loaded") is False:
            log("Mandando sinal de carga (Load) para o IA_MANAGER...", level=4)
            ia_client.load_model(token=token)
            continue

    return 'ERROR'


"""
Success:
{
{
  "message": "string",
  "error": true,
  "training_remaining": 0,
  "loaded": true,
  "loading": true,
  "last_trained": "string"
}
}
Failure:
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
"""