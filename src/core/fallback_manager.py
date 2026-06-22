"""
===============================================================================
FALLBACK MANAGER (src/core/fallback_manager.py)
===============================================================================
Gerencia as decisões do robô quando a IA está indisponível ou falha.
===============================================================================
"""

import sqlite3
import random
from datetime import datetime
from config import INITIAL_ROUTES
from database.repository import DB_PATH
from core.log import log

def get_best_historical_route() -> int:
    """
    Busca no banco de dados a rota que historicamente tem a maior
    média de pessoas para a hora e dia da semana exatos de agora.
    """
    now = datetime.now()
    current_hour = now.hour
    
    # Em Python: 0=Segunda, 6=Domingo.
    # No SQLite strftime('%w'): 0=Domingo, 1=Segunda, 6=Sábado.
    sq_weekday = (now.weekday() + 1) % 7
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT location_id, AVG(people_count) as avg_pop
                FROM memories
                WHERE CAST(strftime('%w', arrive_time) AS INTEGER) = ? 
                  AND CAST(strftime('%H', arrive_time) AS INTEGER) = ?
                GROUP BY location_id
                ORDER BY avg_pop DESC
                LIMIT 1
            """, (sq_weekday, current_hour))
            
            row = cursor.fetchone()
            if row:
                log(f"[Fallback] Rota histórica escolhida: ID {row[0]} (Média: {row[1]:.1f} pessoas).", level=1)
                return row[0]
                
    except sqlite3.Error as e:
        log(f"Erro ao calcular fallback histórico: {e}", level=3)
        
    return get_random_route()

def get_random_route() -> int:
    """Escolhe uma rota aleatória para forçar exploração."""
    fallback_id = random.randint(1, len(INITIAL_ROUTES))
    log(f"[Fallback] Sem dados históricos. Rota aleatória escolhida: ID {fallback_id}.", level=1)
    return fallback_id