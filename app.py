import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify
from charada_data import CHARADA

app = Flask(__name__)

# 1. CONEXIÓN A REDIS LABS
# Vercel leerá la URL que pusiste en las variables de entorno
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    if REDIS_URL:
        # Usamos decode_responses=True para manejar texto directo
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
    else:
        r = None
except Exception as e:
    print(f"Error al conectar con Redis: {e}")
    r = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_web()
    
    # Intentar guardar historial
    if r and vivos:
        try:
            noche, dia = vivos[0], vivos[1]
            r.lpush("historial_bolita", dia, noche)
            r.ltrim("historial_bolita", 0, 99)
        except Exception as e:
            print(f"No se pudo guardar en Redis: {e}")

    # Si es el Cron Job (actualización automática)
    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "Actualización completada"}), 200

    # Si la web falla por completo
    if not vivos:
        return jsonify({"respuesta": "❌ Error al obtener resultados de Florida."})

    # Preparar el análisis
    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Significado variado")
    
    prompt = f"""
    Analista de Bolita Cubana. 
    Resultado de hoy: {ultimo} ({significado}). 
    Historial reciente: {vivos}.
    
    TAREA: 
    1. Dame 5 pronósticos en **negrita**. 
    2. Explica brevemente cada uno con la charada. 
    3. Responde directo y profesional.
    """

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Configura GROQ_API_KEY en Vercel."})

        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": "❌ La IA tardó demasiado en responder. Prueba otra vez."})

app.debug = False
