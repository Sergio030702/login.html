import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis  # Usamos el cliente oficial para Python

app = Flask(__name__)

# Configuración de APIs
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Conexión automática a Redis usando las variables que Vercel ya te puso
redis = Redis(
    url=os.environ.get("KV_REST_API_URL"), 
    token=os.environ.get("KV_REST_API_TOKEN")
)

def obtener_datos_web():
    """Lee Florida Pick 3 de hoy."""
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
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "❌ Falta GROQ_API_KEY"})

    # 1. Obtener números de la web
    nuevos = obtener_datos_web()
    
    # 2. Gestionar la Memoria con Redis
    try:
        # Recuperamos el historial guardado (lo guarda como lista de strings)
        historial = redis.lrange("historial_bolita", 0, 100) or []
        
        # Si hay números nuevos, los guardamos si no están ya en el tope
        for n in reversed(nuevos):
            if n not in historial[:2]:
                redis.lpush("historial_bolita", n)
                historial.insert(0, n)
        
        # Mantenemos solo los últimos 100 sorteos para análisis
        redis.ltrim("historial_bolita", 0, 99)
    except Exception as e:
        print(f"Error Redis: {e}")
        historial = nuevos if nuevos else ["12", "45", "89"] # Respaldo

    # 3. La IA analiza el historial real acumulado
    prompt = f"""
    Eres un analista técnico de lotería con memoria histórica.
    HISTORIAL REAL: {historial[:20]}
    
    TAREA:
    1. Basado en que el último número fue {historial[0]}, ¿cuáles son los 5 números (00-99) con más probabilidad hoy?
    2. Usa la Charada Cubana para dar el significado de cada uno.
    3. Sé directo, usa **negrita** para los números y no filosofes.
    """

    try:
        url_groq = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post(url_groq, json=payload, headers=headers)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": f"❌ Error: {str(e)}"})

app.debug = False
