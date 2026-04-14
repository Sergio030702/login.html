
from flask import Flask, render_template, jsonify
import google.generativeai as genai
import pandas as pd
import requests

app = Flask(__name__)

# Configuración de la IA
genai.configure(api_key="AIzaSyASJ1odza9Q_O-s_u-8hgkfM16csZHRhoM")
model = genai.GenerativeModel('gemini-1.5-flash')

def obtener_resultados_reales():
    """Extrae los últimos terminales de la Lotería de Florida."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        # Leemos la tabla de resultados
        tables = pd.read_html(res.text)
        df = tables[0]
        
        terminales = []
        # Tomamos los últimos 10 del mediodía y 10 de la noche
        for val in df.iloc[:, 1].dropna().head(10): # Columna Mediodía
            terminales.append(str(int(val))[-2:].zfill(2))
        for val in df.iloc[:, 2].dropna().head(10): # Columna Noche
            terminales.append(str(int(val))[-2:].zfill(2))
            
        return terminales
    except Exception as e:
        print(f"Error scrap: {e}")
        return ["No se pudieron obtener datos en tiempo real"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    datos_recientes = obtener_resultados_reales()
    
    prompt = f"""
    Eres un analista experto en la Bolita Cubana y la Charada. 
    Analiza estos terminales recientes de Florida Pick 3: {datos_recientes}.
    
    TAREA:
    1. Busca patrones repetitivos, números que 'llaman' a otros y la mística de la Charada.
    2. Proporciona los 5 números más probables (00-99).
    3. Explica brevemente la razón de cada uno.
    
    IMPORTANTE: Resalta los números finales en negrita.
    """
    
    try:
        response = model.generate_content(prompt)
        return jsonify({"respuesta": response.text})
    except Exception as e:
        return jsonify({"respuesta": "Error consultando a la IA. Verifica tu API Key."})

# Configuración obligatoria para Vercel
app.debug = False
