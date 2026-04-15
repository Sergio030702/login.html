import os
import requests
import re
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_historial_real():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else None
    except:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "❌ ERROR: Revisa la GROQ_API_KEY en Vercel."})

    historial = obtener_historial_real()
    if not historial:
        historial = ["23", "45", "12", "89", "04"] # Seguridad

    url_groq = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    # --- CAMBIO AQUÍ: Usamos el modelo actualizado Llama 3.1 ---
    payload = {
        "model": "llama-3.1-8b-instant", 
        "messages": [
            {"role": "system", "content": "Experto en estadística y Charada Cubana."},
            {"role": "user", "content": f"Analiza estos números reales de Florida: {historial[:15]}. Dame 5 pronósticos de la Charada en negrita."}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        
        if response.status_code == 200:
            res_data = response.json()
            return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
        else:
            error_info = response.json().get('error', {}).get('message', 'Error desconocido')
            return jsonify({"respuesta": f"❌ Error de Groq: {error_info}"})

    except Exception as e:
        return jsonify({"respuesta": f"❌ Error de sistema: {str(e)}"})

app.debug = False
