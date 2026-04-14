import os
import requests
from flask import Flask, render_template, jsonify
import pandas as pd

app = Flask(__name__)

# --- CONFIGURACIÓN ---
API_KEY = os.environ.get("GEMINI_API_KEY")

def obtener_resultados_reales():
    """Extrae los últimos terminales de la Lotería de Florida."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(res.text)
        df = tables[0]
        terminales = []
        for col_idx in [1, 2]:
            for val in df.iloc[:, col_idx].dropna().head(10):
                num_limpio = str(int(float(val)))
                terminales.append(num_limpio[-2:].zfill(2))
        return terminales
    except:
        return ["00", "11", "22", "33"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not API_KEY:
        return jsonify({"respuesta": "Error: No hay API KEY en Vercel."})

    datos = obtener_resultados_reales()
    
    # URL Directa de Google AI (Versión estable v1)
    # Esto evita el error 404 de la librería
    url_google = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Eres experto en Bolita Cubana. Analiza estos terminales: {datos}. Dame 5 números probables (00-99) con su razón según la Charada. Resalta los números en negrita."
            }]
        }]
    }

    try:
        response = requests.post(url_google, json=payload, timeout=15)
        res_json = response.json()
        
        # Extraer el texto de la respuesta de Google
        if "candidates" in res_json:
            texto_ia = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"respuesta": texto_ia})
        else:
            # Si Google devuelve un error, lo mostramos claro
            error_google = res_json.get("error", {}).get("message", "Error desconocido")
            return jsonify({"respuesta": f"Google dice: {error_google}"})
            
    except Exception as e:
        return jsonify({"respuesta": f"Fallo de conexión: {str(e)}"})

app.debug = False
