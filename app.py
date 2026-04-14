import os
from flask import Flask, render_template, jsonify
import google.generativeai as genai
import pandas as pd
import requests

app = Flask(__name__)

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Lee la llave desde las variables de entorno de Vercel
api_key_sistema = os.environ.get("GEMINI_API_KEY")

if api_key_sistema:
    genai.configure(api_key=api_key_sistema)
else:
    print("ALERTA: Variable GEMINI_API_KEY no detectada.")

def obtener_resultados_reales():
    """Extrae los últimos terminales de la Lotería de Florida."""
    try:
        url = "https://www.loteriasflorida.com/resultados-pasados-pick-3"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        
        # Procesamiento de la tabla
        tables = pd.read_html(res.text)
        df = tables[0]
        
        terminales = []
        # Columnas 1 (Mediodía) y 2 (Noche)
        for col_idx in [1, 2]:
            for val in df.iloc[:, col_idx].dropna().head(10):
                # Limpieza: Convertir a número entero y luego a texto de 2 dígitos
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
    if not api_key_sistema:
        return jsonify({"respuesta": "Error: GEMINI_API_KEY no configurada en Vercel."})

    datos_recientes = obtener_resultados_reales()
    
    prompt = f"""
    Eres un analista experto en la Bolita Cubana y la Charada. 
    Analiza estos terminales recientes de Florida Pick 3: {datos_recientes}.
    
    TAREA:
    1. Identifica patrones, repeticiones y lógica de la Charada.
    2. Sugiere los 5 números más probables (00-99).
    3. Explica brevemente la razón de cada uno.
    
    IMPORTANTE: Resalta los números finales en negrita.
    """
    
    # --- LÓGICA DE INTENTOS (SOLUCIÓN AL ERROR 404) ---
    try:
        # Intento A: Modelo Flash (Más rápido y moderno)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return jsonify({"respuesta": response.text})
    
    except Exception as e:
        # Intento B: Si el anterior falla (404), usamos el modelo Pro (Más estable)
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            return jsonify({"respuesta": response.text})
        except Exception as e2:
            # Si ambos fallan, devolvemos el error detallado para diagnóstico
            return jsonify({"respuesta": f"Error de modelos de Google: {str(e)}"})

# Configuración necesaria para Vercel
app.debug = False
