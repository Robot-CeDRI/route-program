"""
Utilitário para traduzir formatos entre o Mundo Real e o Modelo IA.
"""
import math
from datetime import datetime
from config import (
    INITIAL_ROUTES, MAX_POPULATION, MAX_TIME_SECONDS, 
    NUM_CLASSES, GHOST_ROOM_PENALTY, WINDOW_SIZE, 
    VECTOR_SIZE, HOURS_IN_DAY, DAYS_IN_YEAR
)

# ==========================================
# 1. TRADUÇÃO DE VETORES
# ==========================================

def location_to_action_vector(location_id: int) -> list:
    """
    One-Hot Encoding: Cria um array do tamanho de NUM_CLASSES cheio de zeros (0.0).
    Apenas a posição do ID correto recebe o valor um (1.0).
    """
    vector = [0.0] * NUM_CLASSES
    safe_id = min(abs(location_id), NUM_CLASSES - 1)
    vector[safe_id] = 1.0
    return vector

def action_vector_to_location(vector: list) -> int:
    """
    A IA devolve pontuações (Q-Values). 
    Ignoramos as salas "fantasmas" que não existem no INITIAL_ROUTES.
    """
    if not vector or len(vector) != NUM_CLASSES:
        return 1
        
    total_real_rooms = len(INITIAL_ROUTES)
    valid_scores = vector[0 : total_real_rooms + 1].copy()
    
    # Forçamos o ID 0 a ser péssimo, pois as PKs do SQLite começam no 1
    valid_scores[0] = GHOST_ROOM_PENALTY 
    
    best_id = valid_scores.index(max(valid_scores))
    return best_id if best_id > 0 else 1

# ==========================================
# 2. NORMALIZAÇÃO DE ESTADO
# ==========================================
def normalize_memory_tuple(row) -> list:
    _, loc_id, arrive_str, end_str, helping_time, population, *_ = row
    
    try:
        arrive_dt = datetime.strptime(arrive_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") if end_str else datetime.now()
    except ValueError:
        arrive_dt = datetime.now()
        end_dt = arrive_dt

    loc_vector = location_to_action_vector(loc_id)

    time_at_point_sec = (end_dt - arrive_dt).total_seconds()
    time_norm = min(max(time_at_point_sec / MAX_TIME_SECONDS, 0.0), 1.0)
    help_norm = min(max(helping_time / MAX_TIME_SECONDS, 0.0), 1.0)
    pop_norm = min(max(population / MAX_POPULATION, 0.0), 1.0)

    hour_fraction = arrive_dt.hour + (arrive_dt.minute / 60.0)
    daily_sin = math.sin(2 * math.pi * hour_fraction / HOURS_IN_DAY)
    daily_cos = math.cos(2 * math.pi * hour_fraction / HOURS_IN_DAY)

    day_of_year = arrive_dt.timetuple().tm_yday
    annual_sin = math.sin(2 * math.pi * day_of_year / DAYS_IN_YEAR)
    annual_cos = math.cos(2 * math.pi * day_of_year / DAYS_IN_YEAR)

    weekday = arrive_dt.weekday() 
    weekday_vector = [0.0] * 7
    weekday_vector[weekday] = 1.0

    return loc_vector + [time_norm, help_norm, pop_norm, daily_sin, daily_cos, annual_sin, annual_cos] + weekday_vector

def build_sliding_window(history_rows: list, window_size: int = WINDOW_SIZE) -> list:
    """
    Transforma um histórico de tuplas brutas numa matriz (Janela Deslizante).
    Se o histórico for menor que o window_size, aplica zero-padding no início.
    Retorna uma lista de 'window_size' vetores.
    """
    window = []
    for row in history_rows:
        window.append(normalize_memory_tuple(row))
        
    zero_padding = [0.0] * VECTOR_SIZE 
    
    while len(window) < window_size:
        window.insert(0, zero_padding)
        
    return window[-window_size:]