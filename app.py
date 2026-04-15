import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# --- CONFIGURACIÓN ---
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5) if REDIS_URL else None
except:
    r = None

def obtener_tripletas_florida():
    """Trae los resultados reales de Florida Pick 3"""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        # Busca el formato número-número-número
        matches = re.findall(r'(\d)-(\d)-(\d)', res.text)
        # Devuelve las tripletas reales
        return ["-".join(m) for m in matches] if matches else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    tripletas = obtener_tripletas_florida()
    
    # 1. GUARDADO SILENCIOSO EN REDIS
    if r and tripletas:
        try:
            r.lpush("historial_tripletas", *tripletas[:2])
            r.ltrim("historial_tripletas", 0, 99)
        except:
            pass

    # 2. RESPUESTA PARA EL CRON
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Datos guardados"}), 200

    if not tripletas:
        return jsonify({"respuesta": "⚠️ No hay conexión con la pizarra de Florida."})

    # 3. DATOS REALES PARA LA IA
    ultima_tripleta = tripletas[0] # Ejemplo real: "6-5-6"
    partes = ultima_tripleta.split('-')
    fijo = partes[-1]
    corridos = f"{partes[0]} y {partes[1]}"
    
    try:
        historial = r.lrange("historial_tripletas", 0, 15) if r else tripletas[:10]
    except:
        historial = tripletas[:10]
    
    historial_texto = " | ".join(historial)

    # 4. PROMPT REFORZADO (SIN EJEMPLOS FALSOS)
    prompt_maestro = f"""
    ANALISTA JEFE DE BANCA - INFORME TÉCNICO ESTRICTO

    DATOS REALES DEL SORTEO:
    - Tripleta Actual: {ultima_tripleta}
    - Fijo (Terminal): {fijo}
    - Corridos: {corridos}
    - Historial de Secuencias: {historial_texto}

    INSTRUCCIONES:
    1. Basado en que el fijo fue {fijo}, determina los 5 números con mayor probabilidad estadística de salir en el próximo sorteo.
    2. Analiza si los corridos ({corridos}) tienen fuerza para subir a fijos.
    3. No inventes ejemplos. Usa la Charada Cubana para dar los nombres.
    4. Sé constante. Tu análisis debe ser lógico y basado en patrones de repetición.

    FORMATO:
    ### 🎱 PIZARRA DE ALTA PRECISIÓN ###
    (Lista los 5 números con su probabilidad y la razón técnica basada en el historial)

    ---
    **RESUMEN:** Una sola frase técnica sobre la tendencia.
    """

    # 5. LLAMADA A LA IA CON TEMPERATURA BAJA (MÁXIMA SERIEDAD)
    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Error: Falta la API KEY."})

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Eres un analista estadístico serio de lotería. No eres creativo, eres preciso y lógico."},
                    {"role": "user", "content": prompt_maestro}
                ],
                "temperature": 0.2, # <--- ESTO ES LO QUE LO HACE SERIO Y CONSTANTE
                "max_tokens": 800
            }, 
            headers={"Authorization": f"Bearer {GROQ_API_KEY.strip()}"}, 
            timeout=25
        )

        res_data = response.json()
        if "choices" not in res_data:
            return jsonify({"respuesta": "❌ La IA está pensando, intenta en un momento."})

        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})

    except Exception as e:
        return jsonify({"respuesta": f"❌ Error en el sistema: {str(e)}"})

app = app
