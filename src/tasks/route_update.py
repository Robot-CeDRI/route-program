"""
===============================================================================
ROUTE INFERENCE SCRIPT
===============================================================================
Consulta o estado atual, avalia se o IA_MANAGER está disponível e toma a 
melhor decisão de rota (IA ou Histórico) para o robô.
===============================================================================
"""

import sqlite3
from core.log import log
from database import token_model
from database.repository import DB_PATH
from services.cedri_ia import model_load
from services.cedri_ia.client import ia_client
from core import ia_translator
from core import fallback_manager
from core import messages as m

from config import settings, WINDOW_SIZE


def get_recent_states():
    """Retorna os últimos registos do histórico de localização baseados no WINDOW_SIZE."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, location_id, arrive_time, end_time, helping_time, people_count
                FROM memories
                ORDER BY arrive_time DESC
                LIMIT {WINDOW_SIZE}
            """)
            rows = cursor.fetchall()
            rows.reverse()
            return rows
    except sqlite3.Error as e:
        log(f"Database error ao buscar últimas rotas: {e}", level=3)
        return []

def process_action_decision(next_route_id: int):
    """Envia o ID escolhido para o robô ou sistema de navegação."""
    log(f" ROTA TOMADA: {next_route_id} <-", level=1)
    # TODO: Integrar chamada de navegação do robô real aqui

def run():
    last_token = settings.get(m.LAST_TOKEN)
    if not last_token:
        last_token = token_model.getToken()
        settings[m.LAST_TOKEN] = last_token
    
    log(f"Iniciando predição de rota. Token: {last_token}", level=1)

    # Verifica a integridade da IA antes de tentar prever
    ia_status = model_load.run()

    # CASO 1: IA inalcançável (Sem internet, Servidor Offline)
    if ia_status == 'UNREACHABLE':
        log("IA_MANAGER inalcançável. Usando Fallback Histórico.", level=2)
        next_route_id = fallback_manager.get_best_historical_route()
        return process_action_decision(next_route_id)

    # CASO 2: Token inválido (Novo modelo acabou de ser gerado e foi para treino)
    if ia_status == 'NEW_MODEL':
        log("Novo modelo criado (Não treinado). Usando Fallback Histórico.", level=2)
        next_route_id = fallback_manager.get_best_historical_route()
        return process_action_decision(next_route_id)

    # CASO ERRO CRÍTICO
    if ia_status == 'ERROR':
        log("Erro genérico na IA_MANAGER. Usando Fallback Histórico.", level=3)
        next_route_id = fallback_manager.get_best_historical_route()
        return process_action_decision(next_route_id)

    # ==========================================
    # CASO SUCESSO: O MODELO ESTÁ 'READY'
    # ==========================================
    current_state_tuples = get_recent_states()

    if not current_state_tuples:
        log("Sem dados no banco local para gerar contexto. Rota aleatória.", level=2)
        next_route_id = fallback_manager.get_random_route()
        return process_action_decision(next_route_id)

    # Montagem do pacote IA
    lstm_input = ia_translator.build_sliding_window(current_state_tuples, window_size=5)
    body = {
        "token": settings.get(m.LAST_TOKEN),
        "session_id": "inference_route_job",
        "input": lstm_input
    }

    log("Solicitando previsão de rota para a IA...", level=0)
    response = ia_client.process_data(body)      

    # CASO 3: IA Online, Token válido, mas ocorreu um erro no Processamento
    if response.get("error"):
        log(f"Erro durante a predição da IA: {response.get('detail')}. Fallback acionado.", level=3)
        next_route_id = fallback_manager.get_best_historical_route()
        return process_action_decision(next_route_id)
    
    raw_output = response.get("output", [])
    if not raw_output:
        log("IA_MANAGER retornou um output vazio/quebrado. Fallback acionado.", level=3)
        next_route_id = fallback_manager.get_best_historical_route()
        return process_action_decision(next_route_id)

    # CASO 4: IA devolveu os Q-Values com absoluto sucesso!
    vector_result = raw_output[0] if isinstance(raw_output[0], list) else raw_output
    next_route_id = ia_translator.action_vector_to_location(vector_result)
    
    process_action_decision(next_route_id)