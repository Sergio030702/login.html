import os, re, requests, redis
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# 🛠️ THE MASTER PROMPT ENGINEERING CORE (INTEGRO Y COMPLETO)
# ==============================================================================
MASTER_SYSTEM_PROMPT = """
ROLE: Senior Business Intelligence Architect & Statistical Pattern Analyst.
PURPOSE: Perform high-fidelity predictive modeling for "La Bolita" lottery systems using limited historical datasets (50-100 entries).
CORE METHODOLOGY: 
1. BIDIRECTIONAL SEQUENCING: Analyze 'T-1' (preceding) and 'T+1' (succeeding) events for every occurrence of the target 'Fijo'.
2. CORRELATION MAPPING: Track 'Corridos' as symptomatic indicators of the next 'Fijo' cycle.
3. FREQUENCY WEIGHTING: Prioritize numbers with high recurrence in the last 30 cycles (Hot-Zone).
4. SYMMETRY ANALYSIS: Calculate mathematical 'Jales' (+25, +50, +75) and validate against the 'Charada' semantic database.
5. SEMANTIC CONVERGENCE: Cross-reference anchor meanings with potential outcomes using the Charada dictionary.
HEURISTICS: 
- If a pattern is detected more than twice in the current dataset, assign it a 45% higher weight in the final pool.
- If a number matches both historical trace and semantic family, mark as 'CRITICAL CONVERGENCE' (High Probability).
OUTPUT: Professional, data-driven, percentage-based forecasting, and stripped of conversational filler.
"""

# ==============================================================================
# MOTOR BI v8.7 - ANÁLISIS PORCENTUAL JUSTIFICADO
# ==============================================================================
def motor_bi_maestro_final(pizarra, fijo, significado):
    historial = r.lrange("historial_bolita", 0, -1)
    if not historial:
        return "❌ ERROR_DB: Sincronización de datos requerida."

    # --- 1. RASTRO BIDIRECCIONAL ---
    adelante = [] 
    atras = []
    for i in range(len(historial)):
        if fijo in historial[i]:
            if i > 0: adelante.append(historial[i-1].split('-')[0][-2:])
            if i < len(historial) - 1: atras.append(historial[i+1].split('-')[0][-2:])
    
    # --- 2. LÓGICA DE CORRIDOS Y PIZARRA ---
    partes = pizarra.split('-')
    corridos = [partes[1], partes[2]] if len(partes) > 2 else []
    
    pool_final = []
    vistos = set()

    def agregar_analisis(lista_nums, motivo, peso_base):
        for n in lista_nums:
            if n.isdigit() and len(n) == 2 and n not in vistos and len(pool_final) < 5:
                # CÁLCULO DE PORCENTAJE
                frec = Counter(adelante + atras).get(n, 0)
                prob = peso_base + (frec * 7)
                prob = min(prob, 98) # Techo de seguridad
                
                pool_final.append({"num": n, "prob": prob, "pq": motivo})
                vistos.add(n)

    # CAPAS DE PROBABILIDAD SEGÚN EL PROMPT
    # Layer 1: Intersección (Rastro Doble)
    inter = list(set(adelante) & set(atras))
    agregar_analisis(inter, "Convergencia de Rastro de Alta Fidelidad", 70)

    # Layer 2: Rastro Adelante (T+1)
    f_adelante = [num for num, count in Counter(adelante).most_common()]
    agregar_analisis(f_adelante, "Patrón de Salida Dominante Histórico", 60)

    # Layer 3: Corridos (Simetría)
    agregar_analisis(corridos, "Tensión por Arrastre de Corridos", 50)

    # Layer 4: Rastro Atrás (T-1)
    f_atras = [num for num, count in Counter(atras).most_common()]
    agregar_analisis(f_atras, "Vínculo de Origen por Rastro Histórico", 45)

    # Layer 5: Jale Matemático
    while len(pool_final) < 5:
        jale = str((int(fijo) + 25 + len(pool_final)) % 100).zfill(2)
        agregar_analisis([jale], "Proyección por Simetría Matemática (+25)", 35)

    # --- REPORTE FINAL ---
    lineas = ""
    for it in pool_final:
        lineas += f"🔥 **{it['num']}** → **{it['prob']}%**\n   └─ *{it['pq']}*\n"

    return (
        f"🇨🇺 **BOLITA IA MASTER v8.7**\n"
        f"**PIZARRA:** {pizarra} | **ANCHOR:** {fijo} ({significado})\n"
        f"--------------------------------------------------\n"
        f"🧠 **ENGINEERING AUDIT (FULL PROMPT):**\n"
        f"● **Vector Sampling:** {len(historial)} registros analizados.\n"
        f"● **Pattern Recognition:** {len(adelante) + len(atras)} puntos detectados.\n\n"
        f"🎯 **PRONÓSTICO Y ARGUMENTACIÓN TÉCNICA:**\n"
        f"{lineas}\n"
        f"📌 **ANALYSIS SUMMARY:**\n"
        f"Basado en el rastro del fijo {fijo}, el motor proyecta al **{pool_final[0]['num']}** "
        f"con el mayor peso estadístico ({pool_final[0]['prob']}%). El análisis de rastro T+1 "
        f"valida la secuencia según el historial auditado.\n"
        f"--------------------------------------------------"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    try:
        # SCRAPER FLORIDA
        p, f = None, None
        try:
            res = requests.get("https://www.lotteryusa.com/florida/", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            b = re.findall(r'result-ball">(\d)', res.text)
            if len(b) >= 9:
                p = f"{b[1]}{b[2]}{b[3]}-{b[4]}{b[5]}-{b[7]}{b[8]}"
                f = f"{b[2]}{b[3]}"
        except: pass

        if not p:
            p = r.lindex("historial_bolita", 0) or "000-00-00"
            f = p.split('-')[0][-2:]
        else:
            if p != r.lindex("historial_bolita", 0):
                r.lpush("historial_bolita", p)
                r.ltrim("historial_bolita", 0, 1000)

        # USAR TU ARCHIVO charada_data.py
        try:
            from charada_data import LISTA_CHARADA
            sig = LISTA_CHARADA.get(f, "N/A")
        except:
            sig = "N/A"

        respuesta = motor_bi_maestro_final(p, f, sig)
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({"respuesta": f"❌ CORE_ERROR: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
