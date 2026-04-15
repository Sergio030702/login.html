
import os
import requests as peticion_externa
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# --- CONFIGURACIÓN ---
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    if REDIS_URL:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
    else:
        r = None
except:
    r = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = peticion_externa.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    # 1. Buscar números
    vivos = obtener_datos_web()
    
    # 2. Guardar en Redis
    if r and vivos:
        try:
            r.lpush("historial_bolita", vivos[1], vivos[0])
            r.ltrim("historial_bolita", 0, 99)
        except:
            pass

    # 3. COMPROBACIÓN DEL CRON (Aquí ya no existe la palabra 'requests')
    if request.headers.get("x-vercel-cron"):
        return jsonify({"info": "Actualización automática lista"}), 200

    if not vivos:
        return jsonify({"respuesta": "❌ Error: Florida no responde."})

    # 4. LLAMADA A LA IA
    ultimo = vivos[0]
    prompt = f"Resultado: {ultimo} ({CHARADA.get(ultimo)}). Dame 5 números en **negrita** con charada cubana."

    try:
        headers_ai = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        response = peticion_externa.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers_ai)
        return jsonify({"respuesta": response.json()["choices"][0]["message"]["content"]})
    except:
        return jsonify({"respuesta": "❌ Error en la IA."})
