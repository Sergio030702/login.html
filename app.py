import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis
from charada_data import CHARADA

app = Flask(__name__)

# 1. AJUSTE DINÁMICO DE VARIABLES
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Intentamos capturar cualquier variante de nombre que Vercel haya asignado
REDIS_URL = os.environ.get("loteria_db_REDIS_URL") or os.environ.get("KV_REST_API_URL")
REDIS_TOKEN = os.environ.get("loteria_db_REDIS_TOKEN") or os.environ.get("KV_REST_API_TOKEN")

# Inicialización segura
try:
    if REDIS_URL and REDIS_TOKEN:
        # Upstash requiere https:// en el SDK de Python
        url_f = REDIS_URL if REDIS_URL.startswith("https://") else f"https://{REDIS_URL.replace('redis://', '')}"
        redis_client = Redis(url=url_f, token=REDIS_TOKEN)
    else:
        redis_client = None
except:
    redis_client = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        # Extraer solo el último dígito (el terminal)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_web()
    
    # Si la web falla, usamos números de respaldo para que no de error
    if not vivos:
        vivos = ["01", "01"] 

    # Guardado silencioso (si falla, el programa sigue)
    try:
        if redis_client and len(vivos) >= 2:
            noche, dia = vivos[0], vivos[1]
            redis_client.lpush("historial_bolita", dia, noche)
            redis_client.ltrim("historial_bolita", 0, 99)
    except:
        pass

    # Responder al Cron Job rápido
    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "cron_ok"}), 200

    # Preparar el análisis para la IA
    ultimo = vivos[0]
    significado = CHARADA.get(ultimo, "Significado variado")
    
    prompt = f"Eres Bolita IA Master. Último resultado: {ultimo} ({significado}). Historial: {vivos}. Dame 5 pronósticos en **negrita** con sus significados de la charada cubana. Sé breve."

    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Error: Configura GROQ_API_KEY en Vercel."})

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        
        # Si la IA responde bien
        if response.status_code == 200:
            data = response.json()
            return jsonify({"respuesta": data["choices"][0]["message"]["content"]})
        else:
            return jsonify({"respuesta": "❌ La IA está saturada. Intenta de nuevo en unos segundos."})

    except Exception as e:
        # Este es el mensaje que ves en pantalla
        return jsonify({"respuesta": f"❌ Error de procesamiento. Verifica tu conexión."})

app.debug = False
