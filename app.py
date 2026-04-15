import os
import requests  # Para llamar a la web de Florida y Groq
import re
import redis
from flask import Flask, render_template, jsonify, request # Para manejar la petición del usuario
from charada_data import CHARADA

app = Flask(__name__)

# Configuración
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    if REDIS_URL:
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
    
    # Guardado en Redis
    if r and vivos:
        try:
            noche, dia = vivos[0], vivos[1]
            r.lpush("historial_bolita", dia, noche)
            r.ltrim("historial_bolita", 0, 99)
        except:
            pass

    # --- CORRECCIÓN AQUÍ ---
    # Usamos 'request' (el de Flask) no 'requests' (la librería)
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Actualizado correctamente"}), 200
    # -----------------------

    if not vivos:
        return jsonify({"respuesta": "❌ Error al obtener resultados."})

    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Varios significados")
    
    prompt = f"Analista de Bolita. Último: {ultimo} ({significado}). Historial: {vivos}. Dame 5 pronósticos en **negrita** con significados."

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Falta API KEY en Vercel."})

        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except:
        return jsonify({"respuesta": "❌ Error en la IA. Intenta de nuevo."})
