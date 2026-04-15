import os
import requests
from flask import Flask, render_template, jsonify
import pandas as pd
from collections import Counter

app = Flask(__name__)

# Configuración de Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_analisis_completo():
    """Extrae historial largo para identificar patrones."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        tables = pd.read_html(res.text)
        df = tables[0]
        
        historial = []
        # Analizamos las últimas 50 filas de Mediodía (Col 1) y Noche (Col 2)
        # Esto nos da una base de 100 resultados para buscar patrones
        for col in [1, 2]:
            for val in df.iloc[:, col].dropna().head(50):
                n = str(int(float(val)))[-2:].zfill(2)
                historial.append(n)
        
        # Sacamos los 5 que más salen (Frecuencia)
        frecuentes = Counter(historial).most_common(5)
        ultimos_10 = historial[:10]
        
        return {
            "historial": historial,
            "frecuentes": frecuentes,
            "recientes": ultimos_10
        }
    except Exception as e:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "Error: Configura GROQ_API_KEY en Vercel."})

    data_stats = obtener_analisis_completo()
    
    if not data_stats:
        return jsonify({"respuesta": "Error leyendo el historial de la web de Florida."})

    # Instrucciones para que la IA aprenda del historial
    prompt = f"""
    Eres un experto en estadística de loterías y la Charada Cubana.
    
    HISTORIAL DE LOS ÚLTIMOS 100 SORTEOS:
    - Resultados recientes: {data_stats['recientes']}
    - Números con mayor frecuencia: {data_stats['frecuentes']}
    - Lista completa para análisis de patrones: {data_stats['historial']}

    TAREA:
    1. Identifica qué números están 'calientes' (salen mucho) y cuáles están 'atrasados'.
    2. Usa la mística de la Charada para ver qué números 'llaman' a los recientes.
    3. Dame los 5 mejores pronósticos.
    4. Explica brevemente el patrón que encontraste.
    
    Resalta los números en **negrita**.
    """
    
    url_groq = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Analista de patrones de lotería."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6 # Balance entre datos y predicción
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        
        if "choices" in res_data:
            return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
        else:
            return jsonify({"respuesta": "Groq está ocupado, intenta en 10 segundos."})
    except Exception as e:
        return jsonify({"respuesta": f"Fallo de conexión: {str(e)}"})

app.debug = False
