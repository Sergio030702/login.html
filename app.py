import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis
from charada_data import CHARADA

app = Flask(__name__)

# 1. CONEXIÓN CON LOS NOMBRES QUE VEO EN TU CAPTURA
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Vercel le puso prefijos a tus variables basándose en el nombre que le diste
REDIS_URL = os.environ.get("loteria_db_REDIS_URL") or os.environ.get("KV_REST_API_URL")
REDIS_TOKEN = os.environ.get("loteria_db_REDIS_TOKEN") or os.environ.get("KV_REST_API_TOKEN")

try:
    if REDIS_URL and REDIS_TOKEN:
        # Quitamos "redis://" si Vercel lo puso doble por error
        clean_url = REDIS_URL.replace("redis://", "").replace("https://", "")
        redis = Redis(url=f"https://{clean_url}", token=REDIS_TOKEN)
    else:
        redis = None
except Exception:
    redis = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
    # Verificación de diagnóstico
    if not REDIS_URL:
        return jsonify({"respuesta": "❌ Error: El código no ve la variable 'loteria_db_REDIS_URL'. Ve a Settings > Environment Variables y revisa el nombre exacto."})

    vivos = obtener_datos_web()
    if not vivos:
        return jsonify({"respuesta": "❌ Error de conexión con Florida. Intenta en un minuto."})

    # Guardado rápido
    try:
        if redis and len(vivos) >= 2:
            noche, dia = vivos[0], vivos[1]
            redis.lpush("historial_bolita", dia, noche)
            redis.ltrim("historial_bolita", 0, 99)
            ultimo, significado = noche, CHARADA.get(noche, "Varios")
        else:
            ultimo, significado = vivos[0], CHARADA.get(vivos[0], "Varios")
    except:
        ultimo, significado = vivos[0], CHARADA.get(vivos[0], "Varios")

    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "OK"}), 200

    prompt = f"Lotería Florida. Último: {ultimo} ({significado}). Dame 5 pronósticos en **negrita** con significados de la charada cubana."

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        return jsonify({"respuesta": response.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": f"❌ Error de IA: {str(e)}"})
