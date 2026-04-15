import os
import requests
from flask import Flask, render_template, jsonify
import pandas as pd
from collections import Counter

app = Flask(__name__)

# Lee la clave desde las variables de entorno de Vercel
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_analisis_completo():
    """Extrae historial largo de Florida Pick 3 para identificar patrones."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        # User-Agent realista para evitar bloqueos de "bot"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # Leemos las tablas usando lxml
        tables = pd.read_html(res.text, flavor='lxml')
        df = tables[0]
        
        historial = []
        # Tomamos las últimas 50 filas de las columnas Mediodía (1) y Noche (2)
        # Esto nos da una base de 100 números para el análisis
        for col in [1, 2]:
            for val in df.iloc[:, col].dropna().head(50):
                # Limpieza de datos (ej: 23.0 -> 23)
                n = str(int(float(val)))[-2:].zfill(2)
                historial.append(n)
        
        # Estadísticas para la IA
        frecuentes = Counter(historial).most_common(5)
        ultimos_10 = historial[:10]
        
        return {
            "historial": historial,
            "frecuentes": frecuentes,
            "recientes": ultimos_10
        }
    except Exception as e:
        return {"error_real": str(e)}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "Error: Falta GROQ_API_KEY en Vercel."})

    data_stats = obtener_analisis_completo()
    
    if "error_real" in data_stats:
        return jsonify({"respuesta": f"Error de conexión con la lotería: {data_stats['error_real']}"})

    # Prompt avanzado con datos históricos
    prompt = f"""
    Eres un analista experto en la Charada Cubana y estadística de lotería.
    
    HISTORIAL ANALIZADO (Últimos 100 sorteos):
    - Resultados más recientes: {data_stats['recientes']}
    - Números más frecuentes (calientes): {data_stats['frecuentes']}
    - Base de datos completa: {data_stats['historial']}

    TAREA:
    1. Identifica patrones estadísticos (atrasados vs calientes).
    2. Usa la Charada para ver qué números 'llaman' a los recientes.
    3. Sugiere los 5 mejores pronósticos (00-99).
    4. Da una explicación breve basada en el patrón encontrado.
    
    IMPORTANTE: Resalta los números finales en **negrita**.
    """
    
    url_groq = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Analista de Bolita Cubana."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        
        if "choices" in res_data:
            return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
        else:
            return jsonify({"respuesta": "Groq está procesando datos, reintenta en un momento."})
    except Exception as e:
        return jsonify({"respuesta": f"Fallo al conectar con la IA: {str(e)}"})

# Configuración para Vercel
app.debug = False
