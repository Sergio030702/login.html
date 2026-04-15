import os
import requests
import re
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# Intentamos capturar la clave
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_historial_real():
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        # Extraemos los terminales con Regex
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else None
    except Exception as e:
        print(f"Error en scraping: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    # 1. Verificación de existencia de la Key
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "❌ ERROR CRÍTICO: Vercel no lee la variable GROQ_API_KEY. Asegúrate de haberle dado a 'Save' y de haber hecho un 'Redeploy'."})

    # 2. Obtener datos reales
    historial = obtener_historial_real()
    if not historial:
        # Si falla la web, usamos una pequeña lista de seguridad para que la IA no se quede vacía
        historial = ["23", "45", "12", "89", "04"] 

    # 3. Llamada a Groq con manejo de errores detallado
    url_groq = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Eres un experto en estadística y Charada Cubana."},
            {"role": "user", "content": f"Analiza estos números reales de la Florida: {historial[:15]}. Dame 5 pronósticos probables en negrita y explica brevemente por qué basándote en la Charada."}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        
        # Si la respuesta es exitosa
        if response.status_code == 200:
            res_data = response.json()
            return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
        
        # SI HAY ERROR, MOSTRAR EL MENSAJE REAL DE GROQ
        else:
            try:
                error_json = response.json()
                mensaje_error = error_json.get('error', {}).get('message', 'Error sin mensaje')
                tipo_error = error_json.get('error', {}).get('type', 'UnknownType')
                return jsonify({"respuesta": f"❌ ERROR DE GROQ ({response.status_code}): [{tipo_error}] {mensaje_error}"})
            except:
                return jsonify({"respuesta": f"❌ ERROR HTTP {response.status_code}: La API de Groq no respondió con un JSON válido."})

    except requests.exceptions.Timeout:
        return jsonify({"respuesta": "❌ ERROR: La conexión con la IA tardó demasiado (Timeout). Reintenta."})
    except Exception as e:
        return jsonify({"respuesta": f"❌ ERROR DE SISTEMA: {str(e)}"})

app.debug = False
