import os
from flask import Flask, render_template, jsonify
import google.generativeai as genai
import pandas as pd
import requests

app = Flask(__name__)

# --- CONFIGURACIÓN DE SEGURIDAD ---
# El código busca la llave que configuraste en Vercel
api_key_sistema = os.environ.get("GEMINI_API_KEY")

if api_key_sistema:
    genai.configure(api_key=api_key_sistema)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("ERROR: No se encontró la variable GEMINI_API_KEY en el sistema.")

def obtener_resultados_reales():
    """Extrae los últimos terminales de la Lotería de Florida."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        
        # Leemos la tabla de resultados
        tables = pd.read_html(res.text)
        df = tables[0]
        
        terminales = []
        # Tomamos datos de las columnas Mediodía (1) y Noche (2)
        for col_idx in [1, 2]:
            for val in df.iloc[:, col_idx].dropna().head(10):
                # Limpieza de datos (por si vienen como 23.0)
                num_limpio = str(int(float(val)))
                terminales.append(num_limpio[-2:].zfill(2))
            
        return terminales
    except Exception as e:
        return [f"Error al obtener datos: {str(e)}"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    # Verificación de seguridad por si la API KEY falta
    if not api_key_sistema:
        return jsonify({"respuesta": "Error: La API Key no está configurada en Vercel."})

    datos_recientes = obtener_resultados_reales()
    
    prompt = f"""
    Eres un analista experto en la Bolita Cubana y la Charada. 
    Analiza estos terminales recientes de Florida Pick 3: {datos_recientes}.
    
    TAREA:
    1. Busca patrones repetitivos y relación con la mística de la Charada.
    2. Proporciona los 5 números más probables (00-99).
    3. Explica brevemente la razón de cada uno.
    
    IMPORTANTE: Pon los números finales en negrita.
    """
    
    try:
        response = model.generate_content(prompt)
        return jsonify({"respuesta": response.text})
    except Exception as e:
        # Esto te ayudará a diagnosticar si Google bloquea la petición
        return jsonify({"respuesta": f"Error en la consulta: {str(e)}"})

# Configuración obligatoria para despliegue en Vercel
app.debug = False
