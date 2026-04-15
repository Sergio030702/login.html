import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis
from charada_data import CHARADA

app = Flask(__name__)

# Configuración
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
redis = Redis(url=os.environ.get("KV_REST_API_URL"), token=os.environ.get("KV_REST_API_TOKEN"))

def obtener_datos_web():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

def gestionar_horarios(nuevos):
    """Organiza los números en gavetas: Día, Noche y General."""
    try:
        if len(nuevos) < 2: return None
        noche_hoy, dia_hoy = nuevos[0], nuevos[1]

        # Guardar en gavetas separadas
        for llave, valor in [("historial_noche", noche_hoy), ("historial_dia", dia_hoy)]:
            historial = redis.lrange(llave, 0, 0)
            if not historial or historial[0] != valor:
                redis.lpush(llave, valor)
                redis.ltrim(llave, 0, 49)

        # Historial general para la IA
        historial_gen = redis.lrange("historial_bolita", 0, 1)
        for n in reversed([dia_hoy, noche_hoy]):
            if n not in historial_gen:
                redis.lpush("historial_bolita", n)
        redis.ltrim("historial_bolita", 0, 99)
        
        return {"dia": dia_hoy, "noche": noche_hoy}
    except:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_web()
    res_horarios = gestionar_horarios(vivos)
    
    # Si es el Despertador (Cron Job), solo actualiza y termina
    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "Memoria de horarios actualizada"}), 200

    # Si es el usuario, pedimos análisis a la IA
    historial_completo = redis.lrange("historial_bolita", 0, 20)
    h_dia = redis.lrange("historial_dia", 0, 5)
    h_noche = redis.lrange("historial_noche", 0, 5)

    prompt = f"""
    Eres 'Bolita IA Master'. Analiza estos datos:
    - MEDIODÍA (Hoy y anteriores): {h_dia}
    - NOCHE (Anoche y anteriores): {h_noche}
    - ÚLTIMO TOTAL: {historial_completo[0]}
    
    INSTRUCCIONES:
    1. Usa la Charada Cubana: {historial_completo[0]} es {CHARADA.get(historial_completo[0], 'varios significados')}.
    2. Identifica si un número está saliendo mucho por el día o por la noche.
    3. Dame 5 pronósticos en **negrita** con todos sus significados de la charada.
    4. Sé técnico y directo. Prohibido filosofar.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        return jsonify({"respuesta": response.json()["choices"][0]["message"]["content"]})
    except:
        return jsonify({"respuesta": "❌ Error de conexión con la IA."})
