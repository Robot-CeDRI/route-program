"""
===============================================================================
AI RL VISUALIZER (tests/visualizer.py)
===============================================================================
Descrição:
Este script testa o modelo de Aprendizado por Reforço (RL). Em vez de medir a 
"precisão de adivinhação", ele mede a EFICIÊNCIA. Ele compara a Recompensa Esperada 
das decisões da IA contra a Recompensa Média do histórico real.
===============================================================================
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

import os
import tempfile
import webbrowser
import json
import sqlite3
from datetime import datetime

from core.log import log
from config import settings, INITIAL_ROUTES
from core import messages as m
from database import token_model
from database.repository import DB_PATH
from services.cedri_ia import model_load
from services.cedri_ia.client import ia_client
from core import ia_translator

settings[m.NEW] = False

def get_location_name(loc_id: int) -> str:
    try:
        return INITIAL_ROUTES[loc_id - 1][0]
    except IndexError:
        return f"Unknown (ID:{loc_id})"

def get_reward_environment_map():
    """Cria um mapa de recompensas esperadas baseado na média histórica de cada sala por hora e dia."""
    map_data = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%w', arrive_time) AS INTEGER) as w,
                    CAST(strftime('%H', arrive_time) AS INTEGER) as h,
                    location_id,
                    AVG(helping_time),
                    AVG(people_count)
                FROM memories
                WHERE arrive_time IS NOT NULL
                GROUP BY w, h, location_id
            """)
            for row in cursor.fetchall():
                w, h, loc_id, avg_help, avg_pop = row
                py_weekday = (w - 1) % 7 # Normalizar para Python (0=Segunda, 6=Domingo)
                
                # Cálculo da recompensa (Igual ao metrics_sync)
                help_score = min(avg_help / (3600.0 * 0.5), 1.0)
                pop_score = min(avg_pop / 300.0, 1.0)
                reward = (help_score * 0.8) + (pop_score * 0.2)
                
                if avg_pop < 1 and avg_help < 1:
                    reward = -0.2 # Penalidade por sala vazia
                    
                key = f"{py_weekday}-{h:02d}-{loc_id}"
                map_data[key] = round(reward, 4)
    except Exception as e:
        log(f"Erro ao mapear recompensas: {e}", level=3)
    return map_data

def get_historical_dataset():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, location_id, arrive_time, end_time, helping_time, people_count
                FROM memories
                WHERE arrive_time IS NOT NULL
                ORDER BY arrive_time ASC
                LIMIT 1000
            """)
            return cursor.fetchall()
    except Exception as e:
        log(f"Erro ao buscar dataset: {e}", level=3)
        return []

def generate_dashboard_html(all_timelines, distributions, metrics):
    """Gera o HTML focado no Desempenho do RL."""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cedri IA - Relatório de Eficiência (RL)</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }}
            h1 {{ text-align: center; color: #343a40; margin-bottom: 5px; }}
            .header-controls {{ text-align: center; margin-bottom: 20px; }}
            select {{ padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ced4da; cursor: pointer; }}
            .container {{ display: flex; flex-direction: column; gap: 20px; max-width: 1200px; margin: auto; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .accuracy-box {{ text-align: center; padding: 20px 0; }}
            .acc-title {{ font-size: 1.2em; color: #6c757d; margin-bottom: 10px; }}
            .acc-value {{ font-size: 3.5em; font-weight: bold; margin: 0; }}
            .acc-good {{ color: #28a745; }}
            .acc-warn {{ color: #ffc107; }}
            .acc-bad {{ color: #dc3545; }}
            canvas {{ max-height: 350px; }}
            @media (max-width: 800px) {{ .grid-3, .grid-2 {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <h1>🧠 Teste de Eficiência da IA (Reinforcement Learning)</h1>
        
        <div class="header-controls">
            <select id="daySelector" onchange="renderCharts()">
                <option value="0">Segunda-feira</option>
                <option value="1">Terça-feira</option>
                <option value="2">Quarta-feira</option>
                <option value="3">Quinta-feira</option>
                <option value="4">Sexta-feira</option>
                <option value="5">Sábado</option>
                <option value="6">Domingo</option>
            </select>
        </div>
        
        <div class="container">
            <div class="grid-3">
                <div class="card accuracy-box">
                    <div class="acc-title">Pontuação Global da IA</div>
                    <div class="acc-value" id="globalAiScore" style="color:#007bff;">{metrics['global_ai']:.2f}</div>
                    <p style="color: #6c757d;">Média de Recompensa</p>
                </div>
                <div class="card accuracy-box">
                    <div class="acc-title">Pontuação do Histórico</div>
                    <div class="acc-value" style="color:#6c757d;">{metrics['global_hist']:.2f}</div>
                    <p style="color: #6c757d;">(O que o robô fez no passado)</p>
                </div>
                <div class="card accuracy-box">
                    <div class="acc-title">Melhoria da IA</div>
                    <div class="acc-value" id="improvement">{metrics['improvement']:.1f}%</div>
                    <p style="color: #6c757d;">Eficiência vs Histórico</p>
                </div>
            </div>

            <div class="card">
                <h3>Batalha de Decisões: Pontuação da IA vs Realidade</h3>
                <canvas id="timelineChart"></canvas>
            </div>

            <div class="grid-2">
                <div class="card">
                    <h3>Visitas da IA por Local (Neste dia)</h3>
                    <canvas id="distributionChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            const timelines = {json.dumps(all_timelines)};
            const distributions = {json.dumps(distributions)};
            
            const impVal = parseFloat('{metrics['improvement']:.1f}');
            const impEl = document.getElementById('improvement');
            if(impVal > 0) impEl.className = "acc-value acc-good";
            else if(impVal === 0) impEl.className = "acc-value acc-warn";
            else impEl.className = "acc-value acc-bad";

            let timelineChart, distChart;

            function renderCharts() {{
                const day = document.getElementById('daySelector').value;
                const tData = timelines[day] || [];
                const dData = distributions[day] || {{}};

                if(timelineChart) timelineChart.destroy();
                if(distChart) distChart.destroy();

                timelineChart = new Chart(document.getElementById('timelineChart'), {{
                    type: 'line',
                    data: {{
                        labels: tData.map(d => d.time),
                        datasets: [
                            {{
                                label: 'Recompensa (Escolha da IA)',
                                data: tData.map(d => d.ai_reward),
                                borderColor: 'rgba(54, 162, 235, 1)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                tension: 0.3, fill: true
                            }},
                            {{
                                label: 'Recompensa (O que aconteceu na Realidade)',
                                data: tData.map(d => d.hist_reward),
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: 'transparent',
                                borderDash: [5, 5], tension: 0.3
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            tooltip: {{
                                callbacks: {{
                                    label: function(ctx) {{
                                        const i = ctx.dataIndex;
                                        if (ctx.datasetIndex === 0) return `IA foi para ${{tData[i].ai_loc}} (Pts: ${{tData[i].ai_reward}})`;
                                        return `Passado foi para ${{tData[i].hist_loc}} (Pts: ${{tData[i].hist_reward}})`;
                                    }}
                                }}
                            }}
                        }},
                        scales: {{ y: {{ title: {{ display: true, text: 'Recompensa (Pontuação)' }} }} }}
                    }}
                }});

                distChart = new Chart(document.getElementById('distributionChart'), {{
                    type: 'bar',
                    data: {{
                        labels: Object.keys(dData),
                        datasets: [{{
                            label: 'Nº de Decisões da IA',
                            data: Object.values(dData),
                            backgroundColor: 'rgba(75, 192, 192, 0.8)',
                            borderRadius: 4
                        }}]
                    }}
                }});
            }}
            window.onload = renderCharts;
        </script>
    </body>
    </html>
    """
    
    fd, path = tempfile.mkstemp(suffix=".html", prefix="cedri_rl_efficiency_")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return path

def run_test():
    log("Iniciando Avaliação de Eficiência RL...", level=1)

    last_token = settings.get(m.LAST_TOKEN)
    if not last_token:
        last_token = token_model.getToken()
        settings[m.LAST_TOKEN] = last_token
    
    if not model_load.run():
        log("Falha ao carregar modelo. Abortando teste.", level=3)
        return

    dataset = get_historical_dataset()
    if len(dataset) < 6:
        log("Sem dados históricos suficientes (mínimo 6) para LSTM.", level=3)
        return

    # Mapear o ambiente para sabermos calcular as pontuações justas
    env_map = get_reward_environment_map()

    all_timelines = {i: [] for i in range(7)}
    all_distributions = {i: {} for i in range(7)}
    
    total_ai_reward = 0.0
    total_hist_reward = 0.0
    eval_count = 0

    log(f"A testar a IA contra {len(dataset)-5} cenários históricos...", level=0)

    WINDOW_SIZE = 5
    for i in range(WINDOW_SIZE - 1, len(dataset) - 1):
        # A janela de estado atual (S)
        history_slice = dataset[i - WINDOW_SIZE + 1 : i + 1]
        
        # A realidade (Para onde ele foi no passado = A_hist)
        next_record = dataset[i + 1]
        hist_loc_id = next_record[1]
        
        try:
            arr_time = next_record[2]
            dt = datetime.strptime(arr_time, "%Y-%m-%d %H:%M:%S")
            weekday, hour = dt.weekday(), dt.hour
            time_str = dt.strftime("%H:%M")
        except ValueError:
            continue

        lstm_input = ia_translator.build_sliding_window(history_slice, WINDOW_SIZE)
        
        payload = {
            "token": last_token,
            "session_id": "accuracy_eval_test",
            "input": lstm_input
        }
        
        response = ia_client.process_data(payload)
        if response.get("error"):
            continue

        # Decisão da IA (A_pred)
        raw_output = response.get("output", [])
        vector_result = raw_output[0] if isinstance(raw_output[0], list) else raw_output
        ai_loc_id = ia_translator.action_vector_to_location(vector_result)
        
        # Lookups no Mapa de Recompensas
        # Se a sala for desconhecida naquele horário, a penalidade padrão é -0.2
        key_ai = f"{weekday}-{hour:02d}-{ai_loc_id}"
        ai_expected_reward = env_map.get(key_ai, -0.2)
        
        key_hist = f"{weekday}-{hour:02d}-{hist_loc_id}"
        hist_expected_reward = env_map.get(key_hist, -0.2)
        
        # Acumular
        total_ai_reward += ai_expected_reward
        total_hist_reward += hist_expected_reward
        eval_count += 1

        ai_name = get_location_name(ai_loc_id)
        hist_name = get_location_name(hist_loc_id)

        all_timelines[weekday].append({
            "time": time_str,
            "ai_loc": ai_name,
            "ai_reward": ai_expected_reward,
            "hist_loc": hist_name,
            "hist_reward": hist_expected_reward
        })

        if ai_name not in all_distributions[weekday]:
            all_distributions[weekday][ai_name] = 0
        all_distributions[weekday][ai_name] += 1

    # Cálculos Finais
    avg_ai = total_ai_reward / eval_count if eval_count > 0 else 0
    avg_hist = total_hist_reward / eval_count if eval_count > 0 else 0
    
    # Calcular % de melhoria (Cuidado com divisões por zero ou por números negativos)
    improvement = 0
    if avg_hist != 0:
        improvement = ((avg_ai - avg_hist) / abs(avg_hist)) * 100

    metrics = {
        "global_ai": avg_ai,
        "global_hist": avg_hist,
        "improvement": improvement
    }

    log("A gerar o Relatório de Eficiência RL...", level=1)
    html_path = generate_dashboard_html(all_timelines, all_distributions, metrics)
    
    log(f"Abrindo navegador em: {html_path}", level=1)
    webbrowser.open(f"file://{os.path.realpath(html_path)}")

if __name__ == "__main__":
    run_test()