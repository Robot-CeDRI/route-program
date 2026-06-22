import math
import datetime
from core.log import log
from config import INITIAL_ROUTES
from database import memories_model as db_model

# ==========================================
# PASSO 1: GESTÃO DE ESTADO
# ==========================================
active_sessions = {
    "default_robot": {
        "new_line"              : True,
        "current_memory_id"     : None,
        "last_location_id"      : None,
        "arrive_time"           : None,
        "last_update_time"      : None
    }
}

# ==========================================
# PASSO 2: APROXIMAÇÃO DE COORDENADAS
# ==========================================
def get_nearest_location(robot_x, robot_y):
    """
    Calcula a distância euclidiana para encontrar o ponto do INITIAL_ROUTES mais próximo.
    Retorna o location_id (que corresponde à PK na tabela paths) e o nome do local.
    """
    nearest_index = 0
    min_distance = float('inf')

    for i, (name, px, py) in enumerate(INITIAL_ROUTES):
        distance = math.sqrt((px - robot_x)**2 + (py - robot_y)**2)
        if distance < min_distance:
            min_distance = distance
            nearest_index = i

    location_id = nearest_index + 1
    location_name = INITIAL_ROUTES[nearest_index][0]
    
    return location_id, location_name

# ==========================================
# CONTROLADOR PRINCIPAL
# ==========================================
def run(data):
    # log(f"Received data: {str(data)}", level=0)
    x, y            = data['x'], data['y']
    people          = data['people']
    is_helping      = data['is_helping']
    moving          = data['moving']
    unique_people   = data['unique_people']
    state           = active_sessions["default_robot"]
    now             = datetime.datetime.now()

    time_since_last = 0.0
    if state["last_update_time"]:
        time_since_last = (now - state["last_update_time"]).total_seconds()
    state["last_update_time"] = now

    # 2.1: Robô em movimento
    if moving and not is_helping:
        if not state["new_line"]:
            state["new_line"] = True
            
            db_model.close_memory(state["current_memory_id"], now.strftime("%Y-%m-%d %H:%M:%S"))
            log(f"Robô entrou em movimento. Sessão no local terminada.", level=1)
            
        return {"message": "Ignorado: Robô em movimento.", "error": False}

    # 2.2: Robô parado ou a ajudar
    if not moving or is_helping:
        if state["new_line"]:
            location_id, location_name = get_nearest_location(x, y)
            
            state["new_line"] = False
            state["last_location_id"] = location_id
            state["arrive_time"] = now
            
            str_now = now.strftime("%Y-%m-%d %H:%M:%S")
            state["current_memory_id"] = db_model.create_memory(location_id, str_now)
            
            log(f"Nova paragem registada: ID={location_id}", level=1)

        # 2.2.a: À espera
        if not moving and not is_helping:
            db_model.update_memory_waiting(state["current_memory_id"], people, unique_people)
            
        # 2.2.b: Ajudando
        elif is_helping:
            db_model.update_memory_helping(state["current_memory_id"], time_since_last)

    return {"message": "Data processed successfully.", "error": False}

"""
Como irá funcionar?
1.
Recebemos a data com essas informações:
class ModelDataValidator(BaseModel):
    x: int
    y: int
    people: int
    is_helping: bool
    moving : bool
    unique_people: List[str]

Esse é o molde de como iremos fazer::
Current_Location    Integer	
Helping_Time        Time -- Acumulativo
Arrive_Time         Time -- min/hora/dia/ano
End_Time            Time -- min/hora/dia/ano
People              Integer

Outra table:
ID
tabela1_id
person_id -- Representa o ID único de uma pessoa

2.
2.1
If moving = true and is_helping = false then
-- Pulamos essa interação, isso apenas significa que o robô está se movendo por aí, sem de fato
    estar parado em um ponto
-- A flag "new_line" fica `true`

-- Dentro da função que deixa "new_line = true" (Isso acontece apenas caso ela ainda não seja `true`)
-- Atualizamos a última tupla para refletir o daytime em que aquele local parou de receber
    informações
end
2.2
Considerando que moving é false ou is_helping é true interpretamos:
Devemos normalizar os dados que recebemos
a. Ele pode estar parado no ponto, esperando para ajudar alguém (moving == false, is_helping == false)
    -- Utilizamos o último ID salvo caso new_line = `false`.
    -- Caso new_line = `true` transformamos o X e Y em ID's por aproximação de coordenadas

    -- Pegamos os dados atuais, pessoas e pessoas_unicas
    -- Armazenamos no banco de dados, criando uma tupla caso não exista OU **SOMANDO**
        com a tupla atual, por exemplo:
        people_tupla atual = 2
        people = 4
        Resultado:
        people_tupla atual = 6
    -- Esse é um processo acumulativo, essa tabela será utilizada na hora de 

b. Ele está ajudando alguém, devemos manter registro (moving == true/false, is helping == true)
    -- Utilizamos o último ID salvo caso new_line = `false`.
    -- Caso new_line = `true` transformamos o X e Y em ID's por aproximação de coordenadas

    -- Atualizamos a tupla atual (ou criamos) SOMANDO a quantidade de tempo que ele passou ajudando
    -- Não adicionamos novas pessoas que ele vê (Como ele pode estar andando pela universidade isso poderia adicionar viés)

"""