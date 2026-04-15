import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# Configuración
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    if REDIS_URL:
        # decode_responses=True para que los números lleguen como texto y no como bytes
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
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_web()
    
    # Intentar guardar en Redis
    if r and vivos:
        try:
            # vivos[0] es noche, vivos[1] es mediodía
            noche, dia = vivos[0], vivos[1]
            r.lpush("historial_bolita", dia, noche)
            r.ltrim("historial_bolita", 0, 99)
        except:
            pass

    # --- NUEVA FORMA DE DETECTAR EL CRON (SIN 'REQUESTS') ---
    # Usamos request.headers (el de Flask) que es lo correcto
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Actualización automática OK"}), 200
    # -------------------------------------------------------

    if not vivos:
        return jsonify({"respuesta": "❌ Error al leer Florida. Intenta de nuevo."})

    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Varios significados")
    
    prompt = f"Analista de Bolita Cubana. Último: {ultimo} ({significado}). Historial: {vivos}. Dame 5 pronósticos en **negrita** con sus significados de la charada. Sé breve."

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Falta la llave de la IA (GROQ_API_KEY)."})

        headers_ai = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers_ai, timeout=15)
        res_json = response.json()
        return jsonify({"respuesta": res_json["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": "❌ Error de conexión. Prueba otra vez."})

app.debug = False
