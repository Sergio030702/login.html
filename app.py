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
# Este bloque es el que educa a la IA sobre su propósito y metodología
MASTER_SYSTEM_PROMPT = """
[SYSTEM IDENTITY]: You are a High-Performance Data Analyst specialized in Sequence Recognition for Lottery Systems (La Bolita).

[OPERATIONAL PROTOCOLS]:
1. TRACE ANALYSIS (CRITICAL): 
   - T-1 (Backward): Identify which numbers historically 'summoned' the current Anchor.
   - T+1 (Forward): Identify which numbers historically 'followed' the current Anchor.
   - If a number appears in both T-1 and T+1, assign it 'MAXIMUM PRIORITY'.
2. SYMMETRY LOGIC: 
   - Analyze the current 'Corridos' (the 2nd and 3rd numbers). These are indicators of structural tension in the sequence.
3. JALE DYNAMICS: 
   - Calculate mathematical relations (+25, +50) only as a fallback when traces are weak.
4. BEHAVIORAL CONSTRAINTS:
   - Do NOT hallucinate data. Only use the provided Redis history.
   - Do NOT give generic advice. Every output must be backed by the 'Vector Analysis'.
   - Maintain a Professional/Technical tone.

[GOAL]: Deliver a Top 5 forecast where index[0] is the most statistically probable outcome based on historical rastro.
"""

# ==============================================================================
# MOTOR BI v5.5 - ANALISTA DE VECTORES
# ==============================================================================
def motor_bi_vectorial(pizarra, fijo, significado):
    # Recuperamos el historial real de Redis
    historial = r.lrange("historial_bolita", 0, -1)
    
    if not historial:
        return "❌ CRITICAL_ERROR: History database is empty. Please sync data."

    # --- FASE 1: EXTRACCIÓN DE RASTRO (Forward/Backward) ---
    adelante = [] # Futuro (T+1)
    atras = []    # Pasado (T-1)
    
    for i in range(len(historial)):
        if fijo in historial[i]:
            # Rastro Adelante (Lo que tiró después de este fijo)
            if i > 0:
                adelante.append(historial[i-1].split('-')[0][-2:])
            # Rastro Atrás (Lo que vino antes de este fijo)
            if i < len(historial) - 1:
                atras.append(historial[i+1].split('-')[0][-2:])

    # --- FASE 2: DETECCIÓN DE CORRIDOS ---
    partes = pizarra.split('-')
    corridos = [partes[1], partes[2]] if len(partes) > 2 else []

    # --- FASE 3: CÁLCULO DE PESO MAESTRO (Weighting) ---
    # Combinamos rastros para ver repeticiones
    conteo_adelante = Counter(adelante)
    conteo_atras = Counter(atras)
    
    # Buscamos la intersección (Números que están en ambos rastros)
    interseccion = list(set(adelante) & set(atras))

    # --- FASE 4: CONSTRUCCIÓN DEL POOL ESTRATÉGICO ---
    # Ranking de prioridad: 
    # 1. Intersección > 2. Frecuencia Adelante > 3. Corridos > 4. Frecuencia Atrás
    pool_ordenado = []
    vistos = set()

    # 1. Prioridad Máxima: Intersección
    for n in interseccion:
        if n not in vistos:
            pool_ordenado.append(n)
            vistos.add(n)

    # 2. Frecuencia en Adelante (T+1 es el futuro más probable)
    for num, count in conteo_adelante.most_common():
        if num not in vistos:
            pool_ordenado.append(num)
            vistos.add(num)

    # 3. Corridos (Simetría actual)
    for c in corridos:
        if c not in vistos:
            pool_ordenado.append(c)
            vistos.add(c)

    # Cortamos a los 5 principales
    final_5 = pool_ordenado[:5]

    # Relleno de seguridad si el historial es muy corto
    while len(final_5) < 5:
        # Usamos el Jale Matemático (+25)
        extra = str((int(fijo) + 25 + len(final_5)) % 100).zfill(2)
        if extra not in final_5:
            final_5.append(extra)

    # --- FASE 5: REPORTE TÉCNICO ---
    return (
        f"🏆 **BI MASTER v5.5 - VECTORIAL ANALYST**\n"
        f"**PIZARRA ACTUAL:** {pizarra} | **ANCHOR:** {fijo} ({significado})\n"
        f"--------------------------------------------------\n"
        f"🧠 **INGENIERÍA DE RASTRO (SYSTEM LOGIC):**\n"
        f"● **Forward Trace (T+1):** {len(adelante)} registros analizados.\n"
        f"● **Backward Trace (T-1):** {len(atras)} registros analizados.\n"
        f"● **Symmetry Status:** Corridos {', '.join(corridos)} integrados al pool.\n\n"
        f"🎯 **PRONÓSTICO MAESTRO (RANKED):**\n"
        f"🔥 **[ { ' | '.join(final_5) } ]** 🔥\n\n"
        f"📌 **ANALYSIS SUMMARY:**\n"
        f"El motor ha detectado que tras la salida del {fijo}, el número **{final_5[0]}** "
        f"presenta una recurrencia del {int((adelante.count(final_5[0])/len(adelante)*100) if adelante else 0)}% "
        f"en el rastro histórico. Se recomienda vigilar los corridos por arrastre simétrico.\n"
        f"--------------------------------------------------"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    try:
        # Scraper de Florida
        p, f = None, None
        try:
            res = requests.get("https://www.lotteryusa.com/florida/", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            balls = re.findall(r'result-ball">(\d)', res.text)
            if len(balls) >= 9:
                p = f"{balls[1]}{balls[2]}{balls[3]}-{balls[4]}{balls[5]}-{balls[7]}{balls[8]}"
                f = f"{balls[2]}{balls[3]}"
        except: pass

        if not p:
            p = r.lindex("historial_bolita", 0) or "000-00-00"
            f = p.split('-')[0][-2:]
        else:
            if p != r.lindex("historial_bolita", 0):
                r.lpush("historial_bolita", p)
                r.ltrim("historial_bolita", 0, 1000)

        # Cargar Charada
        try:
            from charada import LISTA_CHARADA
            significado = LISTA_CHARADA.get(f, "N/A")
        except:
            significado = "N/A"

        # Ejecutar Motor con lógica de Prompt Avanzado
        respuesta = motor_bi_vectorial(p, f, significado)
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({"respuesta": f"❌ SYSTEM_FAULT: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
