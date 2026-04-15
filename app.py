import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis
from charada_data import CHARADA

app = Flask(__name__)

# 1. CONFIGURACIÓN Y DIAGNÓSTICO DE VARIABLES
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Vercel a veces usa KV_REST_API_URL o REDIS_URL. Probamos ambas.
REDIS_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("REDIS_URL")
REDIS_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("REDIS_TOKEN")

try:
    if REDIS_URL and REDIS_TOKEN:
        redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
    else:
        redis = None
except Exception:
    redis = None

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except Exception:
        return []

def gestionar_horarios(nuevos):
    if not redis or not nuevos or len(nuevos) < 2:
        return None
    try:
        noche_hoy, dia_hoy = nuevos[0], nuevos[1]
        # Guardar en gavetas
        for llave, valor in [("historial_noche", noche_hoy), ("historial_dia", dia_hoy)]:
            historial = redis.lrange(llave, 0, 0)
            if not historial or historial[0] != valor:
                redis.lpush(llave, valor)
                redis.ltrim(llave, 0, 49)
        # Historial general
        redis.lpush("historial_bolita", dia_hoy, noche_hoy)
        redis.ltrim("historial_bolita", 0, 99)
        return {"dia": dia_hoy, "noche": noche_hoy}
    except Exception:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    # VERIFICACIÓN DE SEGURIDAD
    if not REDIS_URL:
        return jsonify({"respuesta": "❌ Error: Las variables de Redis no se detectan. Revisa Settings > Environment Variables en Vercel."})

    vivos = obtener_datos_web()
    if not vivos:
        return jsonify({"respuesta": "❌ Error: No se pudieron obtener datos de la web de Florida (bloqueo temporal)."})

    res_horarios = gestionar_horarios(vivos)
    
    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "Actualizado"}), 200

    if not GROQ_API_KEY:
        return jsonify({"respuesta": "❌ Error: Falta la API Key de Groq."})

    # Intentar sacar historial de Redis, si falla usar los vivos
    try:
        h_dia = redis.lrange("historial_dia", 0, 5) or [vivos[1]]
        h_noche = redis.lrange("historial_noche", 0, 5) or [vivos[0]]
        ultimo = vivos[0]
    except Exception:
        h_dia, h_noche, ultimo = [vivos[1]], [vivos[0]], vivos[0]

    prompt = f"Analiza para la lotería: Último {ultimo} ({CHARADA.get(ultimo)}). Mediodía: {h_dia}. Noche: {h_noche}. Dame 5 números en negrita con significados de la charada."

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        return jsonify({"respuesta": response.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": f"❌ Error de IA: {str(e)}"})
