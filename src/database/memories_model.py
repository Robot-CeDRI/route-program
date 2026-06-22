import sqlite3
from database.repository import DB_PATH
from core.log import log

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_memory(location_id: int, arrive_time: str) -> int:
    """Cria uma nova sessão na base de dados e devolve o ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (location_id, arrive_time) VALUES (?, ?)",
                (location_id, arrive_time)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        log(f"[DB] Erro ao criar memory: {e}", level=3)
        return None

def update_memory_waiting(memory_id: int, added_people: int, unique_people: list):
    """Soma as pessoas e tenta inserir os IDs únicos."""
    if not memory_id:
        return
        
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if added_people > 0:
                cursor.execute(
                    "UPDATE memories SET people_count = people_count + ? WHERE id = ?",
                    (added_people, memory_id)
                )
            
            if unique_people:
                records = [(memory_id, str(p)) for p in unique_people]
                cursor.executemany(
                    "INSERT OR IGNORE INTO unique_people (memory_id, person_id) VALUES (?, ?)",
                    records
                )
            conn.commit()
    except sqlite3.Error as e:
        log(f"[DB] Erro ao atualizar estado 'waiting': {e}", level=3)

def update_memory_helping(memory_id: int, time_increment: float):
    """Adiciona tempo à coluna helping_time."""
    if not memory_id or time_increment <= 0:
        return
        
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE memories SET helping_time = helping_time + ? WHERE id = ?",
                (time_increment, memory_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        log(f"[DB] Erro ao atualizar estado 'helping': {e}", level=3)

def close_memory(memory_id: int, end_time: str):
    """Encerra a sessão atual registando o momento de saída."""
    if not memory_id:
        return
        
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE memories SET end_time = ? WHERE id = ?",
                (end_time, memory_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        log(f"[DB] Erro ao fechar memory: {e}", level=3)