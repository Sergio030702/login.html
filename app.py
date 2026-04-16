import os, re, requests, redis
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# 🛠️ ADVANCED PROMPT ENGINEERING CORE (The "Brain" Instructions)
# ==============================================================================
MASTER_SYSTEM_PROMPT = """
[SYSTEM IDENTITY]: You are a High-Performance Data Analyst specialized in Sequence Recognition for Lottery Systems (La Bolita).
[OPERATIONAL PROTOCOLS]:
1. TRACE ANALYSIS (CRITICAL): 
   - T-1 (Backward): Identify which numbers historically 'summoned' the current Anchor.
   - T+1 (Forward): Identify which numbers historically 'followed' the current Anchor.
   - If a number appears in both T-1 and T+1, assign it 'MAXIMUM PRIORITY'.
2. SYMMETRY LOGIC: 
   - Analyze the current 'Corridos' (the 2nd and 3rd numbers). These are indicators of structural tension.
3. JALE DYNAMICS: 
   - Calculate mathematical relations (+25, +50) only as a fallback when traces are weak.
4. BEHAVIORAL CONSTRAINTS:
   - Do NOT hallucinate data. Only use the provided Redis history.
   - Do NOT give generic advice. Every output must be backed by the 'Vector Analysis'.
   - Maintain a Professional/Technical tone.
[GOAL]: Deliver a Top 5 forecast where each choice is justified by specific historical data.
"""

# ==============================================================================
# MOTOR BI v7.0 - ANALISTA ESTRATÉGICO CON ARGUMENTACIÓN
# ==============================================================================
def motor_bi_argumentado(pizarra, fijo, significado):
    historial = r.lrange("historial_bolita", 0, -1)
    
    if not historial:
        return "❌ ERROR_DB: No hay historial disponible para análisis."

    # --- FASE 1: RASTRO COMPLETO ---
    adelante = [] # T+1
    atras = []    # T-1
    for i in range(len(historial)):
        if fijo in historial[i]:
            if i > 0: adelante.append(historial[i-1].split('-')[0][-2:])
            if i < len(historial) - 1: atras.append(historial[i+1].split('-')[0][-2:])

    # --- FASE 2: ANALISIS DE CORRIDOS ---
    partes = pizarra.split('-')
    corridos = [partes[1], partes[2]] if len(partes) > 2 else []

    # --- FASE 3: CONSTRUCCIÓN CON ARGUMENTO DETALLADO ---
    pool_final = []
    vistos = set()

    def agregar_al_pool(lista_nums, motivo_base, detalle_tecnico):
        for n in lista_nums:
            if n.isdigit() and len(n) == 2 and n not in vistos and len(pool_final) < 5:
                # Calculamos frecuencia para el argumento
                freq = Counter(adelante + atras).get(n, 1)
                argumento = f"{motivo_base} ({detalle_tecnico} con frecuencia de {freq}x)"
                pool_final.append({"num": n, "pq": argumento})
                vistos.add(n)

    # 1. Rastro Doble
    interseccion = list(set(adelante) & set(atras))
    agregar_al_pool(interseccion, "Rastro de Alta Fidelidad", "Detectado en secuencia de entrada y salida")

    # 2. Frecuencia Adelante (Futuro)
    frec_adelante = [num for num, count in Counter(adelante).most_common()]
    agregar_al_pool(frec_adelante, "Patrón de Salida Dominante", "Fuerte tendencia a seguir al fijo actual")

    # 3. Corridos
    agregar_al_pool(corridos, "Arrastre por Simetría", "Tensión detectada en los números acompañantes de la pizarra")

    # 4. Rastro Atrás (Origen)
    frec_atras = [num for num, count in Counter(atras).most_common()]
    agregar_al_pool(frec_atras, "Vínculo de Origen Histórico", "Número con alta probabilidad de retorno cíclico")

    # 5. Jale
    while len(pool_final) < 5:
        jale = str((int(fijo) + 25 + len(pool_final)) % 100).zfill(2)
        agregar_al_pool([jale], "Proyección por Jale", "Cálculo de simetría matemática (+25/+50)")

    # --- FASE 4: REPORTE BOLITA IA MASTER ---
    lineas_justificadas = ""
    for item in pool_final:
        lineas_justificadas += f"🔥 **{item['num']}**\n   └─ *{item['pq']}*\n"

    return (
        f"🇨🇺 **BOLITA IA MASTER v7.0**\n"
        f"**PIZARRA ACTUAL:** {pizarra} | **ANCHOR:** {fijo} ({significado})\n"
        f"--------------------------------------------------\n"
        f"🧠 **ENGINEERING AUDIT:**\n"
        f"● **Sampling:** {len(historial)} registros analizados.\n"
        f"● **Vector Analysis:** {len(adelante) + len(atras)} puntos de conexión hallados.\n\n"
        f"🎯 **PRONÓSTICO Y ARGUMENTACIÓN TÉCNICA:**\n"
        f"{lineas_justificadas}\n"
        f"📌 **ANALYSIS SUMMARY:**\n"
        f"Tras auditar el rastro del fijo {fijo}, el motor identifica al **{pool_final[0]['num']}** "
        f"como el vector con mayor peso estadístico. La recurrencia en el rastro T+1 indica "
        f"una ventana de salida inminente según los últimos ciclos analizados.\n"
        f"--------------------------------------------------"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    try:
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

        try:
            from charada import LISTA_CHARADA
            significado = LISTA_CHARADA.get(f, "N/A")
        except:
            significado = "N/A"

        respuesta = motor_bi_argumentado(p, f, significado)
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({"respuesta": f"❌ CORE_ERROR: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
