"""
===============================================================================
MOCK DATA GENERATOR (sensor/mock.py)
===============================================================================
Descrição:
Este script gera um histórico sintético realista de telemetria do robô.
A população agora é tratada como um ecossistema fechado (100 a 300 alunos
por dia), distribuídos por capacidade da sala e horário.
===============================================================================
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# ==========================================
# CONFIGURAÇÕES DE DIRETÓRIO E BD
# ==========================================
CURRENT_DIR = Path(__file__).resolve().parent
DB_PATH = CURRENT_DIR.parent.parent / "data" / "data.db"

# ==========================================
# DEFINIÇÃO DOS GRUPOS E CAPACIDADES
# ==========================================
# Regra 5: Limites físicos absolutos de cada ambiente
ROOM_CAPACITIES = {
    "AUDITOR": 150,
    "WC1": 6, "WC2": 6,
    "CO-WORK": 50, "RP": 40, "AEESTIG": 30,
    "START": 40, "LE": 40, "LEI": 40, "L2I": 30, "LCGAV": 30, "LCA": 30, "LIC": 30, "LSE": 30, "LCAR": 30,
    "STARTUP": 20, "NUCLEOS": 20,
    "LMC1": 25, "LMFH": 25, "GICOS": 25, "LMCM": 25, "LM2": 25, "LG": 25,
    "SOO1": 20, "LTM2-1": 20, "LTM2-2": 20, "CIMO": 20, "LTM3": 20, "FABLAB": 20, "LQA": 20, "LPQ": 20
}

GROUPS = {
    1: ["START", "LE", "LEI", "L2I", "LCGAV", "LCA", "LIC", "LSE", "LCAR"], # Salas de aula principais
    2: ["RP", "CO-WORK", "AEESTIG"],                                        # Áreas de convivência
    3: ["AUDITOR", "WC1"],                                                  # Auditório e Banheiros
    4: ["STARTUP", "WC2", "NUCLEOS"],                                       # Empreendedorismo e Banheiros
    5: ["LMC1", "LMFH", "GICOS", "LMCM", "LM2", "LG"],                      # Laboratórios 1
    6: ["SOO1", "LTM2-1", "LTM2-2", "CIMO", "LTM3", "FABLAB", "LQA", "LPQ"] # Laboratórios 2
}

# Pesos base para distribuição da população espalhada
GROUP_WEIGHTS = {
    1: 0.35, 
    2: 0.25, 
    3: 0.15, 
    4: 0.10, 
    5: 0.10, 
    6: 0.05  
}

# ==========================================
# LÓGICA DE GERAÇÃO
# ==========================================
def calculate_population(daily_total: int, route_name: str, group_num: int, dt: datetime) -> int:
    """Calcula a população observada na sala, baseada na fatia diária e capacidades."""
    weekday = dt.weekday() # 0 = Segunda, 4 = Sexta, 5 = Sábado, 6 = Domingo
    hour = dt.hour
    
    # 1. Definir os blocos de tempo
    is_break = (7 <= hour < 9) or (12 <= hour < 14) or (17 <= hour <= 19)
    is_class = (9 <= hour < 12) or (14 <= hour < 17)
    is_night = (20 <= hour <= 23) or (0 <= hour < 7)

    # 2. Regra 2: Fração da população que está "acessível" e espalhada pelo campus
    if is_break:
        accessible_fraction = random.uniform(0.60, 0.90) # Maioria está fora das salas
    elif is_class:
        accessible_fraction = random.uniform(0.15, 0.35) # Maioria guardada nas salas, poucos visíveis
    elif is_night:
        accessible_fraction = random.uniform(0.0, 0.05)  # Campus quase deserto
    else:
        accessible_fraction = random.uniform(0.30, 0.50)

    # Regra 3: Sextas à tarde costumam esvaziar
    if weekday == 4 and hour >= 14:
        accessible_fraction *= 0.6

    active_population = daily_total * accessible_fraction

    # 3. Regras de Complexidade e Distribuição por Sala
    room_weight = GROUP_WEIGHTS.get(group_num, 0.1)
    dynamic_multiplier = 1.0

    # Regra 4: Durante as aulas, áreas de descanso (G2) concentram os alunos livres
    if is_class and group_num == 2:
        dynamic_multiplier = 3.0

    # Segundas e Quartas os blocos G1 e G5 dominam
    if weekday in [0, 2] and group_num in [1, 5]:
        dynamic_multiplier = 1.5

    # WCs têm fluxo constante mas em pequenos volumes, com picos nos intervalos
    if route_name in ["WC1", "WC2"]:
        dynamic_multiplier = 2.5 if is_break else 0.8

    # Eventos no auditório (Ex: Sextas-feiras)
    if weekday == 4 and is_class and route_name == "AUDITOR":
        dynamic_multiplier = 4.0

    # 4. Cálculo da População Local
    slice_fraction = room_weight * dynamic_multiplier
    raw_pop = active_population * slice_fraction
    
    # Adicionar o ruído estocástico (+/- 10%)
    noise = random.uniform(0.9, 1.1)
    final_pop = int(raw_pop * noise)
    
    # Regra 5: Limitar estritamente à capacidade da sala
    max_capacity = ROOM_CAPACITIES.get(route_name, 30)
    return max(0, min(final_pop, max_capacity))

def generate_mock_data(days_in_past=30, sessions_per_day=50):
    """Gera dados retroativos e insere diretamente na tabela memories."""
    
    if not DB_PATH.exists():
        print(f"[ERRO] Banco de dados não encontrado em {DB_PATH}")
        return

    location_map = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT location_id, name FROM paths")
            for row in cursor.fetchall():
                location_map[row[1]] = row[0]
    except sqlite3.Error as e:
        print(f"[ERRO DB] Falha ao ler tabela paths: {e}")
        return

    route_info = {}
    for group_num, routes in GROUPS.items():
        for route_name in routes:
            if route_name in location_map:
                route_info[route_name] = {
                    "db_id": location_map[route_name],
                    "group": group_num,
                    "capacity": ROOM_CAPACITIES.get(route_name, 30)
                }

    if not route_info:
        print("[ERRO] Nenhuma rota encontrada.")
        return

    mock_records = []
    now = datetime.now()
    
    print(f"Gerando histórico para os últimos {days_in_past} dias...")
    
    for day_offset in range(days_in_past, -1, -1):
        current_date = now - timedelta(days=day_offset)
        weekday = current_date.weekday()
        
        # Regra 1: População total espalhada no dia (Mínimo 100, Máximo 300)
        if weekday in [5, 6]:
            daily_total = random.randint(15, 50)  # Fim de semana vazio
        else:
            daily_total = random.randint(100, 300) # Dias letivos
            
        for _ in range(sessions_per_day):
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            session_start = current_date.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
            
            duration_minutes = random.randint(2, 45)
            session_end = session_start + timedelta(minutes=duration_minutes)
            
            route_name = random.choice(list(route_info.keys()))
            info = route_info[route_name]
            
            # População espalhada e regulada
            population = calculate_population(daily_total, route_name, info["group"], session_start)            
            
            # Cálculo de tempo de ajuda baseado na DENSIDADE da sala (ao invés de um limite global irreal)
            help_factor = population / info["capacity"] 
            max_duration_seconds = (duration_minutes * 60) * 0.3
            helping_time_seconds = max_duration_seconds * help_factor * random.uniform(0.8, 1.2)
            
            mock_records.append((
                info["db_id"],                               # location_id
                session_start.strftime("%Y-%m-%d %H:%M:%S"), # arrive_time
                session_end.strftime("%Y-%m-%d %H:%M:%S"),   # end_time
                round(helping_time_seconds, 2),              # helping_time
                population,                                  # people_count
                0                                            # used flag
            ))

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO memories (location_id, arrive_time, end_time, helping_time, people_count, used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, mock_records)
            conn.commit()
            print(f"[SUCESSO] {len(mock_records)} registros mockados inseridos no banco de dados!")
    except sqlite3.Error as e:
        print(f"[ERRO DB] Falha ao inserir memórias falsas: {e}")

if __name__ == "__main__":
    generate_mock_data(days_in_past=360, sessions_per_day=48)