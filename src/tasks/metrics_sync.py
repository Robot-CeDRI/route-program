"""
===============================================================================
REINFORCEMENT LEARNING SYNCHRONIZER (tasks/metrics_sync.py)
===============================================================================
"""

import time
import sqlite3
import threading

from core.log import log
from database.repository import DB_PATH
from database import token_model
from services.cedri_ia import model_load
from services.cedri_ia.client import ia_client
from core import ia_translator
from config import (
    settings, WINDOW_SIZE, MAX_EXPERIENCES, DREAMS_COUNT, DREAM_EPOCHS,
    DREAM_CHECK_INTERVAL_SEC, REWARD_EMPTY_PENALTY, REWARD_HELP_WEIGHT, 
    REWARD_POP_WEIGHT, REWARD_HELP_FACTOR, MAX_TIME_SECONDS, MAX_POPULATION
)
from core import messages as m

SESSION_ID = "sync_batch_learning"
sync_lock = threading.Lock()

def calculate_reward(helping_time: float, population: int) -> float:
    """
    Calcula a recompensa da ação baseada nos pesos definidos na configuração.
    """
    help_score = min(helping_time / (MAX_TIME_SECONDS * REWARD_HELP_FACTOR), 1.0)
    pop_score = min(population / MAX_POPULATION, 1.0)
    
    if population == 0 and helping_time == 0:
        return REWARD_EMPTY_PENALTY

    return round((help_score * REWARD_HELP_WEIGHT) + (pop_score * REWARD_POP_WEIGHT), 4)

def get_replay_buffer() -> list:
    """Busca as últimas memórias no banco de dados baseando-se em MAX_EXPERIENCES."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, location_id, arrive_time, end_time, helping_time, people_count, used
                FROM memories
                WHERE arrive_time IS NOT NULL
                ORDER BY arrive_time DESC
                LIMIT ?
            """, (MAX_EXPERIENCES,))
            rows = cursor.fetchall()
            rows.reverse()
            return rows
    except sqlite3.Error as e:
        log(f"Database error ao buscar Replay Buffer: {e}", level=3)
        return []

def mark_memories_as_used(memory_ids: list):
    if not memory_ids:
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.executemany("UPDATE memories SET used = 1 WHERE id = ?", [(i,) for i in memory_ids])
            conn.commit()
    except sqlite3.Error as e:
        log(f"Database error ao marcar memórias como usadas: {e}", level=3)

def wait_for_dream_to_finish(token: str) -> bool:
    while True:
        time.sleep(DREAM_CHECK_INTERVAL_SEC)
        response = ia_client.check_model(token)
        
        if response.get("error"):
            log(f"Erro ao verificar o status do sonho: {response.get('detail')}", level=3)
            return False
            
        remaining = response.get("training_remaining", 0)
        if remaining == 0:
            return True
            
        log(f"O IA_MANAGER continua a sonhar... Fila de processos restantes: {remaining}", level=4)

def run():
    if not sync_lock.acquire(blocking=False):
        log("Uma sessão de Sonhos já está em andamento. O Scheduler irá ignorar este ciclo.", level=4)
        return

    try:
        last_token = settings.get(m.LAST_TOKEN)
        if not last_token:
            last_token = token_model.getToken()
            settings[m.LAST_TOKEN] = last_token

        ia_status = model_load.run()
        if ia_status in ['UNREACHABLE', 'ERROR']:
            log("IA_MANAGER inalcançável. O robô adiará os sonhos para o próximo ciclo.", level=2)
            return

        all_memories = get_replay_buffer()
        if len(all_memories) < WINDOW_SIZE:
            log("Memórias insuficientes para criar a janela temporal. Cancelando sincronização.", level=2)
            return

        train_data = []
        new_memory_ids = set()

        for i in range(len(all_memories) - 1):
            current_mem = all_memories[i]
            next_mem = all_memories[i+1]
            
            if current_mem[6] == 0:
                new_memory_ids.add(current_mem[0])
            
            history_s = all_memories[max(0, i - WINDOW_SIZE + 1) : i + 1]
            state = ia_translator.build_sliding_window(history_s, WINDOW_SIZE)
            
            next_loc_id = next_mem[1]
            action_vector = ia_translator.location_to_action_vector(next_loc_id)
            reward = calculate_reward(next_mem[4], next_mem[5])
            
            history_s_prime = all_memories[max(0, i - WINDOW_SIZE + 2) : i + 2]
            next_state = ia_translator.build_sliding_window(history_s_prime, WINDOW_SIZE)
            
            train_data.append({
                "state": state,
                "action": action_vector,
                "reward": reward,
                "next_state": next_state,
                "done": False
            })

        if not new_memory_ids:
            log("Não há vivências novas (used=0). O robô não precisa de sonhar hoje.", level=1)
            return

        payload = {
            "token": last_token,
            "session_id": SESSION_ID,
            "train_data": train_data,
            "epochs": DREAM_EPOCHS
        }

        success_dreams = 0
        log(f"Iniciando ciclo com um Buffer de {len(train_data)} transições...", level=1)

        for dream in range(1, DREAMS_COUNT + 1):
            log(f"=== Iniciando Sonho {dream}/{DREAMS_COUNT} ===", level=1)
            
            response = ia_client.train_model(payload)
            if response.get("error"):
                log(f"Falha de conexão durante o Sonho {dream}: {response.get('detail')}", level=3)
                break 
                
            if not wait_for_dream_to_finish(last_token):
                log(f"Erro ao monitorizar o status do Sonho {dream}. Abortando o resto da noite.", level=3)
                break
                
            success_dreams += 1
            log(f"Sonho {dream} absorvido com sucesso!", level=1)

        if success_dreams > 0:
            mark_memories_as_used(list(new_memory_ids))
            log(f"Ciclo concluído. {len(new_memory_ids)} vivências foram arquivadas como (used=1).", level=1)

    except Exception as e:
        log(f"Erro inesperado durante o metrics_sync: {e}", level=3)
    finally:
        sync_lock.release()