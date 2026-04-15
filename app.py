import os
import requests
from flask import Flask, render_template, jsonify
import pandas as pd
from collections import Counter

app = Flask(__name__)

# Configuración de Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_historial_real():
    """Extrae resultados reales de Pick 3 desde una fuente verificada."""
    try:
        # Usamos LotteryUSA que es muy estable y fácil de leer
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # Pandas busca las tablas en la web
        tables = pd.read_html(res.text)
        
        # Normalmente la primera tabla (index 0) tiene los resultados recientes
        df = tables[0]
        
        historial = []
        # Buscamos en la columna donde están los números (suele llamarse 'Result' o ser la segunda columna)
        # Tomamos los últimos resultados disponibles
        for row in df.itertuples():
            # Intentamos extraer el número de la columna correspondiente
            # En Pick 3 suele venir como '1-2-3', nos interesa el terminal
            try:
                num_str = str(row[2]) # La columna 2 suele ser el resultado
                if '-' in num_str:
                    # Si viene como 1-2-3, tomamos el último número
                    terminal = num_str.split('-')[-1].strip().zfill(2)
                    historial.append(terminal)
            except:
                continue
                
        return historial if len(historial) > 0 else None

    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "Error: Falta la clave GROQ_API_KEY en Vercel."})

    # Intentamos obtener los datos reales
    historial = obtener_historial_real()
    
    if not historial:
        return jsonify({"respuesta": "⚠️ No se pudo obtener datos reales de la Florida. La web de resultados no respondió. Por favor, intenta de nuevo más tarde."})

    # Estadísticas para la IA
    conteo = Counter(historial)
    frecuentes = conteo.most_common(5)
    recientes = historial[:10]
    
    prompt = f"""
    Eres un analista de Bolita Cubana. Analiza estos resultados REALES de Pick 3 Florida:
    
    - ÚLTIMOS TERMINALES: {recientes}
    - MÁS REPETIDOS: {frecuentes}
    - HISTORIAL ANALIZADO: {historial}

    BASADO EN ESTOS DATOS:
    1. Busca patrones de repetición o números que no han salido.
    2. Usa la lógica de la Charada Cubana para dar 5 números probables.
    3. Explica tu razonamiento basándote en que el último terminal fue el {recientes[0]}.
    
    Resalta los números en **negrita**.
    """
    
    url_groq = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "system", "content": "Analista estadístico serio."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except:
        return jsonify({"respuesta": "Error al conectar con la IA."})

app.debug = False
