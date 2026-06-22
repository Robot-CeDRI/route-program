"""
===============================================================================
REAL-TIME TELEMETRY SIMULATOR (sensor/simulator.py)
===============================================================================
Descrição:
Atua como um "gêmeo digital" do robô, concebido para realizar testes de stress 
e de integração na API de telemetria. Envia requisições HTTP (POST) contínuas 
a cada 10 segundos, replicando com exatidão a máquina de estados do robô 
físico a navegar pelo ambiente.

Como funciona:
1. Navegação por Bases: O robô seleciona um ponto do campus e permanece em 
   patrulha estática nesse local por períodos de 30 a 60 minutos antes de 
   transitar para a próxima base.
2. Gatilhos de Interação: Possui 2% de probabilidade a cada ciclo de ser 
   abordado. Ao ser ativado, engatilha um de dois comportamentos:
   - Categoria 1 (Dúvidas Rápida): O robô pausa as rondas e permanece estático 
     (is_helping=True, moving=False) durante 1 a 5 minutos.
   - Categoria 2 (Guia Turístico): O robô ativa os motores e acompanha o 
     utilizador até outro local (is_helping=True, moving=True) num trajeto 
     que dura de 10 a 20 minutos (ida e volta).
3. Visão Computacional Simulada: Durante o ciclo de 10 segundos, há 30% de 
   probabilidade de "ver" pessoas (1 a 3 indivíduos). Destes encontros, há 
   10% de probabilidade de identificar um rosto registado (enviando um 
   identificador único anonimizado).

Condições e Possibilidades:
- Requisito: A aplicação FastAPI (Route Manager) deve estar online e 
  acessível no IP/Porta configurados.
- Teste de Estado: Este script foi desenhado primariamente para validar 
  se a lógica de `new_line` e transição de sessões do `data_receiver.py` 
  consegue interpretar e reagir às mudanças entre estado de espera, 
  movimento e ajuda contínua.
===============================================================================
"""

import httpx
import time
import random

# ==========================================
# CONFIGURAÇÕES DE REDE
# ==========================================
ip = "0.0.0.0"
port = "48051"
base_url = f"http://{ip}:{port}"

hello_timeout = 3
default_timeout = 6

# ==========================================
# ROTAS BASE PARA SIMULAÇÃO
# ==========================================
LOCATIONS = [
    ("START", 0, 0),
    ("LEI", 10.5, 1.5),
    ("CO-WORK", 48, -8),
    ("STARTUP", 42.5, 34),
    ("FABLAB", 19, 32)
]

def _make_request(method: str, endpoint: str, payload: dict = None, timeout: float = None) -> dict:
    url = f"{base_url}{endpoint}"
    req_timeout = timeout if timeout is not None else default_timeout
        
    try:
        if method.upper() == "GET":
            response = httpx.get(url, timeout=req_timeout)
        elif method.upper() == "POST":
            response = httpx.post(url, timeout=req_timeout, json=payload)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        print(f"[ERRO] HTTP error (Status {exc.response.status_code}) on {exc.request.url}.")
        return {"error": True}
    except httpx.RequestError as exc:
        print(f"[ERRO] Failure {exc.request.url}. Is the IA Manager turned on?")
        return {"error": True}
    except Exception as e:
        print(f"[ERRO] Unexpected error calling {url}: {e}")
        return {"error": True}

# ==========================================
# LÓGICA DE SIMULAÇÃO
# ==========================================
def run_simulation():
    print("Iniciando simulador de telemetria do robô...")
    
    current_loc = random.choice(LOCATIONS)
    ticks_until_move = random.choice([30, 60]) * 6 
    
    help_state = "IDLE"
    help_ticks_left = 0

    while True:
        if help_state != "GUIDING":
            ticks_until_move -= 1
            if ticks_until_move <= 0:
                current_loc = random.choice(LOCATIONS)
                ticks_until_move = random.choice([30, 60]) * 6
                print(f"\n[MOVIMENTO] Robô mudou de base para: {current_loc[0]}")

        moving = False
        is_helping = False

        if help_state == "IDLE":
            if random.random() < 0.02:
                if random.random() < 0.7:
                    help_state = "QA"
                    help_ticks_left = random.randint(1, 5) * 6
                    print(f"\n[AJUDA] Iniciou Q&A em {current_loc[0]} (Cat 1) por {help_ticks_left // 6} min")
                else:
                    help_state = "GUIDING"
                    help_ticks_left = random.randint(10, 20) * 6
                    print(f"\n[AJUDA] A guiar aluno a partir de {current_loc[0]} (Cat 2) por {help_ticks_left // 6} min")
        else:
            is_helping = True
            help_ticks_left -= 1
            
            if help_state == "GUIDING":
                moving = True
                
            if help_ticks_left <= 0:
                print(f"\n[FIM AJUDA] Terminou ação de {help_state}. A voltar à rotina.")
                help_state = "IDLE"

        people_count = 0
        unique_people = []
        
        if random.random() < 0.3:
            people_count = random.randint(1, 3)
            if random.random() < 0.1:
                unique_id = f"student_hash_{random.randint(1000, 9999)}"
                unique_people.append(unique_id)

        if is_helping:
            people_count = max(1, people_count)

        payload = {
            "x": current_loc[1],
            "y": current_loc[2],
            "people": people_count,
            "is_helping": is_helping,
            "moving": moving,
            "unique_people": unique_people
        }

        print(f"[{time.strftime('%H:%M:%S')}] A enviar -> Loc: {current_loc[0]} | Move: {moving} | Help: {is_helping} | People: {people_count}")
        
        _make_request(
            method="POST",
            endpoint="/api/models/send-data",
            payload=payload
        )

        time.sleep(10)

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\nSimulador encerrado manualmente pelo utilizador.")