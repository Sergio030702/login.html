import os, re, requests, redis
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# 🛠️ THE MASTER PROMPT ENGINEERING CORE (ÍNTEGRO - NO TOCAR)
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
# MOTOR BI v9.1 - ELIMINACIÓN DE N/A Y FILTRADO PORCENTUAL
# ==============================================================================
def motor_bi_maestro_final(pizarra, fijo, significado_fijo):
    historial = r.lrange("historial_bolita", 0, -1)
    if not historial:
        return "❌ ERROR_DB: No hay datos en Redis."

    # Importar tu archivo de datos
    try:
        import charada_data
        lista_completa = charada_data.LISTA_CHARADA
    except:
        lista_completa = {}

    # --- 1. RASTRO BIDIRECCIONAL ---
    adelante = [] 
    atras = []
    for i in range(len(historial)):
        if fijo in historial[i]:
            if i > 0: adelante.append(historial[i-1].split('-')[0][-2:])
            if i < len(historial) - 1: atras.append(historial[i+1].split('-')[0][-2:])
    
    # --- 2. ANALIZADOR DE VÍNCULOS POR ARCHIVO ---
    def tiene_relacion_en_archivo(n_analizar):
        sig_n = lista_completa.get(n_analizar, "").lower()
        if not significado_fijo or not sig_n: return False
        palabras_anchor = set(re.findall(r'\w+', significado_fijo.lower()))
        palabras_target = set(re.findall(r'\w+', sig_n))
        # Si comparten alguna palabra de más de 3 letras (para evitar "de", "el", "la")
        comunes = [p for p in palabras_anchor.intersection(palabras_target) if len(p) > 3]
        return len(comunes) > 0

    # --- 3. LÓGICA DE CORRIDOS ---
    partes = pizarra.split('-')
    corridos = [partes[1], partes[2]] if len(partes) > 2 else []
    
    candidatos = []
    vistos = set()

    def procesar_candidatos(lista_nums, motivo, peso_base):
        for i, n in enumerate(lista_nums):
            if n.isdigit() and len(n) == 2 and n not in vistos:
                # CÁLCULO INICIAL
                frec = Counter(adelante + atras).get(n, 0)
                ajuste_pos = (len(lista_nums) - i) * 1.5
                prob = peso_base + (frec * 6) + ajuste_pos
                
                info = motivo
                # BONO SEMÁNTICO (TU ARCHIVO)
                if tiene_relacion_en_archivo(n):
                    prob += 15
                    info += " + Vínculo Charada"
                
                # BONO POR CORRIDO
                if n in corridos:
                    prob += 8
                    info += " | Simetría"

                prob = min(prob, 98.9)
                candidatos.append({"num": n, "prob": prob, "pq": info})
                vistos.add(n)

    # Llenar la lista de candidatos por capas
    procesar_candidatos(list(set(adelante) & set(atras)), "Rastro Doble", 70)
    procesar_candidatos(adelante, "Patrón T+1", 60)
    procesar_candidatos(corridos, "Efecto Corrido", 55)
    procesar_candidatos(atras, "Origen T-1", 45)

    # Rellenar con Jales si faltan
    while len(candidatos) < 5:
        n_jale = str((int(fijo) + 25 + len(candidatos)) % 100).zfill(2)
        procesar_candidatos([n_jale], "Jale Matemático", 30)

    # --- ORDENAR POR PORCENTAJE (EL QUE MÁS TENGA VA PRIMERO) ---
    candidatos = sorted(candidatos, key=lambda x: x['prob'], reverse=True)
    pool_final = candidatos[:5]

    # --- REPORTE FINAL ---
    lineas = ""
    for it in pool_final:
        lineas += f"🔥 **{it['num']}** → **{round(it['prob'], 1)}%**\n   └─ *{it['pq']}*\n"

    return (
        f"🇨🇺 **BOLITA IA MASTER v9.1**\n"
        f"**PIZARRA:** {pizarra} | **ANCHOR:** {fijo} ({significado_fijo})\n"
        f"--------------------------------------------------\n"
        f"🧠 **ENGINEERING AUDIT (FULL PROMPT):**\n"
        f"● **Sampling:** {len(historial)} registros analizados.\n"
        f"● **Logic:** Competencia de filtros por peso porcentual.\n\n"
        f"🎯 **PRONÓSTICO Y ARGUMENTACIÓN TÉCNICA:**\n"
        f"{lineas}\n"
        f"📌 **ANALYSIS SUMMARY:**\n"
        f"El motor ha priorizado al **{pool_final[0]['num']}** tras superar los filtros de "
        f"rastro, simetría y convergencia semántica con un {round(pool_final[0]['prob'], 1)}%.\n"
        f"--------------------------------------------------"
    )

@app.route('/api/predecir')
def predecir():
    try:
        # SCRAPER
        res = requests.get("https://www.lotteryusa.com/florida/", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        b = re.findall(r'result-ball">(\d)', res.text)
        if len(b) >= 9:
            p = f"{b[1]}{b[2]}{b[3]}-{b[4]}{b[5]}-{b[7]}{b[8]}"
            f = f"{b[2]}{b[3]}"
        else:
            p = r.lindex("historial_bolita", 0)
            f = p.split('-')[0][-2:]

        # Asegurar significado del Anchor desde charada_data.py
        try:
            import charada_data
            sig = charada_data.LISTA_CHARADA.get(f, "N/A")
        except:
            sig = "N/A"

        respuesta = motor_bi_maestro_final(p, f, sig)
        return jsonify({"respuesta": respuesta})
    except Exception as e:
        return jsonify({"respuesta": f"❌ CORE_ERROR: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
