from flask import Flask, render_template, jsonify
import google.generativeai as genai
import pandas as pd
import requests

app = Flask(__name__)

# 1. Usamos la API Key que proporcionaste
genai.configure(api_key="AIzaSyASJ1odza9Q_O-s_u-8hgkfM16csZHRhoM")

# 2. Cambiamos a la versión 'latest' que es más estable para la API gratuita
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def obtener_resultados_reales():
    """Extrae los últimos terminales de la Lotería de Florida."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        
        # Leemos la tabla de resultados
        tables = pd.read_html(res.text)
        df = tables[0]
        
        terminales = []
        # Limpiamos y extraemos terminales de Mediodía y Noche
        for col_idx in [1, 2]:
            for val in df.iloc[:, col_idx].dropna().head(10):
                # Convertimos a string, quitamos decimales y tomamos los últimos 2
                num_str = str(int(float(val)))
                terminales.append(num_str[-2:].zfill(2))
            
        return terminales
    except Exception as e:
        return [f"Error al obtener datos: {str(e)}"]

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
    1. Busca patrones repetitivos y relación con la Charada.
    2. Proporciona los 5 números más probables (00-99).
    3. Explica brevemente la razón de cada uno.
    
    IMPORTANTE: Pon los números finales en negrita.
    """
    
    try:
        # Generar contenido
        response = model.generate_content(prompt)
        return jsonify({"respuesta": response.text})
    except Exception as e:
        # 3. CAMBIO CLAVE: Esto te dirá el error real en la pantalla de tu web
        error_msg = str(e)
        if "location not supported" in error_msg.lower():
            return jsonify({"respuesta": "Error: Google no admite tu ubicación actual (Cuba). Usa un VPN para generar la API Key o acceder."})
        return jsonify({"respuesta": f"Error detallado: {error_msg}"})

# Vercel no necesita app.run()
