import os
import requests
import re
from flask import Flask, render_template, jsonify
from collections import Counter

app = Flask(__name__)

# Configuración de Groq desde variables de entorno
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def obtener_historial_real():
    """Busca resultados reales usando expresiones regulares para evitar bloqueos."""
    try:
        # Usamos LotteryUSA que es la más estable
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        res = requests.get(url, headers=headers, timeout=12)
        res.raise_for_status()
        
        # Buscamos patrones de números tipo '5-2-9' en el código de la página
        # Esto es más efectivo que intentar leer tablas
        patron = re.findall(r'\d-\d-\d', res.text)
        
        historial = []
        for combinacion in patron:
            # Extraemos el último dígito (terminal)
            terminal = combinacion.split('-')[-1].strip().zfill(2)
            historial.append(terminal)
            
        return historial if len(historial) > 0 else None
    except Exception as e:
        print(f"Error técnico: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    if not GROQ_API_KEY:
        return jsonify({"respuesta": "Error: Configura GROQ_API_KEY en Vercel."})

    # Intentamos obtener los datos reales
    historial = obtener_historial_real()
    
    if not historial:
        return jsonify({"respuesta": "⚠️ Los servidores de resultados están saturados o bloqueados. Por favor, intenta de nuevo en unos minutos."})

    # Estadísticas para el prompt de la IA
    conteo = Counter(historial)
    frecuentes = conteo.most_common(5)
    recientes = historial[:10]
    
    # Prompt estricto para evitar alucinaciones
    prompt = f"""
    Eres un analista estadístico experto en la Bolita Cubana. 
    Analiza estos TERMINALES REALES de Pick 3 Florida (últimos sorteos): {historial}.
    
    DATOS CLAVE:
    1. El terminal más reciente es: {recientes[0]}.
    2. Los números que más se repiten son: {frecuentes}.
    
    TAREA:
    - Identifica patrones de frecuencia y números 'atrasados'.
    - Usa la lógica de la Charada Cubana para proponer 5 números probables.
    - No inventes datos que no estén en la lista.
    - Explica brevemente tu razonamiento basado en la estadística de estos números.

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
            {"role": "system", "content": "Analista serio de lotería. No inventas resultados."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3 # Temperatura baja para que sea preciso
    }

    try:
        response = requests.post(url_groq, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})
    except:
        return jsonify({"respuesta": "Error de conexión con la inteligencia artificial."})

app.debug = False
