import os
import requests
from flask import Flask, render_template, jsonify
import pandas as pd

app = Flask(__name__)

# Recuperamos la clave de Vercel
API_KEY = os.environ.get("GEMINI_API_KEY")

def obtener_datos_florida():
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        tables = pd.read_html(res.text)
        df = tables[0]
        terminales = []
        # Mediodía y Noche
        for col in [1, 2]:
            for val in df.iloc[:, col].dropna().head(10):
                n = str(int(float(val)))
                terminales.append(n[-2:].zfill(2))
        return terminales
    except:
        return ["No se pudo leer la web de Florida"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not API_KEY:
        return jsonify({"respuesta": "Error: Falta la API_KEY en Vercel."})

    resultados = obtener_datos_florida()
    
    # FORZAMOS LA URL A LA VERSIÓN 1 ESTABLE (v1)
    # Esto elimina el error de 'v1beta'
    endpoint = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Analiza estos terminales de la bolita: {resultados}. Dame 5 números probables (00-99) usando la Charada Cubana. Pon los números en negrita."
            }]
        }]
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        data = response.json()

        if "candidates" in data:
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"respuesta": texto})
        else:
            # Si Google da error, lo mostramos directo
            msg = data.get("error", {}).get("message", "Error desconocido")
            return jsonify({"respuesta": f"Google responde: {msg}"})
    except Exception as e:
        return jsonify({"respuesta": f"Error de conexión: {str(e)}"})

# Para Vercel
app.debug = False
