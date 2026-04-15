import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# Configuración de variables (Asegúrate de que coincidan en Vercel)
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Conexión a Redis Labs
try:
    if REDIS_URL:
        # decode_responses=True para manejar texto directo
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
    else:
        r = None
except Exception:
    r = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        # Extraemos el terminal (último número)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_web()
    
    # 1. Guardar en Redis si hay datos
    if r and vivos:
        try:
            noche, dia = vivos[0], vivos[1]
            r.lpush("historial_bolita", dia, noche)
            r.ltrim("historial_bolita", 0, 99)
        except:
            pass

    # 2. COMPROBACIÓN DEL CRON (Corregida)
    # Usamos request.headers (de Flask) sin la 's' al final
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Actualización automática completada"}), 200

    if not vivos:
        return jsonify({"respuesta": "❌ Error: No se pudo conectar con los resultados de Florida."})

    # 3. Preparar pronóstico con IA
    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Varios")
    
    prompt = f"Analista de Bolita Cubana. Último: {ultimo} ({significado}). Historial: {vivos}. Dame 5 pronósticos en **negrita** con sus significados de la charada cubana."

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Falta configurar GROQ_API_KEY en Vercel."})

        headers_ai = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, # Súbelo de 0.3 a 0.7 para que sea más variada
            "max_tokens": 500
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers_ai, timeout=15)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": "❌ La IA tardó mucho en responder. Prueba de nuevo."})

app.debug = False
