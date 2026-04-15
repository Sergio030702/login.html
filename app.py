import os
import requests as web_get # Le cambiamos el nombre para que no choque con Flask
import re
import redis
from flask import Flask, render_template, jsonify, request # 'request' sin S para Vercel
from charada_data import CHARADA

app = Flask(__name__)

# Configuración de Variables
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Conexión a Redis
try:
    if REDIS_URL:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
    else:
        r = None
except Exception:
    r = None

def obtener_datos_web():
    """Busca los números usando el nombre nuevo web_get."""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Usamos web_get aquí
        res = web_get.get(url, headers=headers, timeout=10)
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

    # --- AQUÍ ESTABA EL ERROR (CORREGIDO) ---
    # Usamos 'request' de Flask para ver si es el Cron Job
    is_cron = request.headers.get("x-vercel-cron")
    if is_cron:
        return jsonify({"status": "Actualizado por Cron"}), 200
    # ----------------------------------------

    if not vivos:
        return jsonify({"respuesta": "❌ Error al conectar con Florida."})

    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Varios significados")
    
    prompt = f"Analista de Bolita. Último: {ultimo} ({significado}). Historial: {vivos}. Dame 5 pronósticos en **negrita** con sus significados de la charada cubana."

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Configura GROQ_API_KEY en Vercel."})

        # Usamos web_get para la llamada a Groq
        headers_ai = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        response = web_get.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers_ai, timeout=15)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": f"❌ Error: {str(e)}"})

app.debug = False
