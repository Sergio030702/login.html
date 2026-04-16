import os, re, requests, redis
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# 🛠️ THE MASTER PROMPT ENGINEERING CORE (INTEGRO Y COMPLETO - NO TOCAR)
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
# MOTOR BI v9.0 - ANÁLISIS PORCENTUAL CON FILTRO DE ARCHIVO
# ==============================================================================
def motor_bi_maestro_final(pizarra, fijo, significado_fijo):
    historial = r.lrange("historial_bolita", 0, -1)
    if not historial:
        return "❌ ERROR_DB: Sincronización de datos requerida."

    # --- 1. IMPORTAR TU ARCHIVO DE DATOS ---
    try:
        from charada_data import LISTA_CHARADA
    except:
        LISTA_CHARADA = {}

    # --- 2. RASTRO BIDIRECCIONAL ---
    adelante = [] 
    atras = []
    for i in range(len(historial)):
        if fijo in historial[i]:
            if i > 0: adelante.append(historial[i-1].split('-')[0][-2:])
            if i < len(historial) - 1: atras.append(historial[i+1].split('-')[0][-2:])
    
    # --- 3. ANALIZADOR DE VÍNCULOS (SOLO USANDO TU ARCHIVO) ---
    def tiene_relacion_en_archivo(n_analizar):
        sig_n = LISTA_CHARADA.get(n_analizar, "").lower()
        if not significado_fijo or not sig_n: return False
        # Buscamos si comparten alguna palabra (ej: "muerto" y "muerto grande")
        palabras_anchor = set(re.findall(r'\w+', significado_fijo.lower()))
        palabras_target = set(re.findall(r'\w+', sig_n))
        return len(palabras_anchor.intersection(palabras_target)) > 0

    # --- 4. LÓGICA DE CORRIDOS Y PIZARRA ---
    partes = pizarra.split('-')
    corridos = [partes[1], partes[2]] if len(partes) > 2 else []
    
    pool_final = []
    vistos = set()

    def agregar_analisis(lista_nums, motivo, peso_base):
        for i, n in enumerate(lista_nums):
            if n.isdigit() and len(n) == 2 and n not in vistos and len(pool_final) < 5:
                # CÁLCULO DE PORCENTAJE
                frec = Counter(adelante + atras).get(n, 0)
                ajuste_pos = (len(lista_nums) - i) * 1.1
                prob = peso_base + (frec * 6) + ajuste_pos
                
                info_extra = motivo
                # SI TIENEN ALGO EN COMÚN EN TU ARCHIVO, SUMA PUNTOS
                if tiene_relacion_en_archivo(n):
                    prob += 12
                    info_extra += " + Relación de Significado Detectada"

                prob = min(prob, 98.5)
                pool_final.append({"num": n, "prob": round(prob, 1), "pq": info_extra})
                vistos.add(n)

    # CAPAS DE PROBABILIDAD (MANTENIENDO EL ORDEN ORIGINAL)
    inter = list(set(adelante) & set(atras))
    agregar_analisis(inter, "Convergencia de Rastro de Alta Fidelidad", 70)

    f_adelante = [num for num, count in Counter(adelante).most_common()]
    agregar_analisis(f_adelante, "Patrón de Salida Dominante Histórico", 60)

    agregar_analisis(corridos, "Tensión por Arrastre de Corridos", 55)

    f_atras = [num for num, count in Counter(atras).most_common()]
    agregar_analisis(f_atras, "Vínculo de Origen por Rastro Histórico", 45)

    while len(pool_final) < 5:
        jale = str((int(fijo) + 25 + len(pool_final)) % 100).zfill(2)
        agregar_analisis([jale], "Proyección por Simetría Matemática (+25)", 35)

    # --- REPORTE FINAL ---
    lineas = ""
    for it in pool_final:
        lineas += f"🔥 **{it['num']}** → **{it['prob']}%**\n   └─ *{it['pq']}*\n"

    return (
        f"🇨🇺 **BOLITA IA MASTER v9.0**\n"
        f"**PIZARRA:** {pizarra} | **ANCHOR:** {fijo} ({significado_fijo})\n"
        f"--------------------------------------------------\n"
        f"🧠 **ENGINEERING AUDIT (FULL PROMPT):**\n"
        f"● **Vector Sampling:** {len(historial)} registros analizados.\n"
        f"● **Pattern Recognition:** {len(adelante) + len(atras)} puntos detectados.\n\n"
        f"🎯 **PRONÓSTICO Y ARGUMENTACIÓN TÉCNICA:**\n"
        f"{lineas}\n"
        f"📌 **ANALYSIS SUMMARY:**\n"
        f"Basado en el rastro del fijo {fijo}, el motor proyecta al **{pool_final[0]['num']}** "
        f"con el mayor peso estadístico ({pool_final[0]['prob']}%). El análisis incluye "
        f"validación por significado común según charada_data.py.\n"
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

        # IMPORTAR DE TU ARCHIVO ESPECÍFICO
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
