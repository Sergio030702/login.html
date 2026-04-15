import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# --- CONFIGURACIÓN ---
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5) if REDIS_URL else None
except:
    r = None

def obtener_tripletas_florida():
    """Extrae las tripletas completas (Fijo + Corridos)"""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        # Buscamos el formato X-X-X (ejemplo: 6-5-6)
        matches = re.findall(r'(\d)-(\d)-(\d)', res.text)
        # Retornamos las tripletas como strings: ["6-5-6", "1-0-1", ...]
        return ["-".join(m) for m in matches] if matches else []
    except Exception as e:
        print(f"Error de conexión: {e}")
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    tripletas = obtener_tripletas_florida()
    
    # 1. GUARDADO AUTOMÁTICO EN REDIS
    if r and tripletas:
        try:
            # Guardamos las últimas 2 tripletas (Día y Noche)
            # El asterisco *tripletas[:2] expande la lista para meter los dos elementos
            r.lpush("historial_tripletas", *tripletas[:2])
            # Mantenemos solo las últimas 100 tripletas para no saturar la DB
            r.ltrim("historial_tripletas", 0, 99)
        except Exception as e:
            print(f"Error en Redis: {e}")

    # 2. RESPUESTA PARA EL CRON (Invisible para el usuario)
    if request.headers.get("x-vercel-cron"):
        return jsonify({
            "status": "💾 Historial actualizado automáticamente a medianoche",
            "tripletas_guardadas": tripletas[:2]
        }), 200

    if not tripletas:
        return jsonify({"respuesta": "⚠️ La pizarra de Florida no está disponible ahora mismo."})

    # 3. PREPARAR DATOS PARA EL ANALISTA
    # Tomamos la tripleta más reciente (Noche)
    ultima_raw = tripletas[0].split('-')
    fijo = ultima_raw[-1]  # El terminal (Fijo)
    corridos = ultima_raw[0:2]  # Los dos primeros
    
    # Recuperamos el historial completo de Redis para el análisis de patrones
    try:
        historial_raw = r.lrange("historial_tripletas", 0, 19) if r else tripletas[:10]
    except:
        historial_raw = tripletas[:10]
    
    historial_texto = " | ".join(historial_raw)

    # 4. PROMPT MAESTRO V5.1 (TRIPLETA + MEMORIA ESTADÍSTICA)
    prompt_maestro = f"""
    SISTEMA DE INTELIGENCIA DE BANCA - PROTOCOLO DE ANÁLISIS INTEGRAL V5.1

    PERFIL: Analista Jefe con 30 años de calle. Experto en secuencias de Fijos y Corridos.
    
    DATOS DE LA JORNADA:
    - ÚLTIMA TRIPLETA: {tripletas[0]}
    - EL FIJO (Terminal): {fijo} ({CHARADA.get(fijo, 'Sin definir')})
    - LOS CORRIDOS: {", ".join(corridos)}
    - HISTORIAL DE PIZARRA (Últimas 20 tripletas): {historial_texto}

    TAREA TÉCNICA:
    1. ANALIZA LOS CORRIDOS: Evalúa cómo los números {corridos} están 'empujando' al próximo fijo.
    2. PATRONES DE REPETICIÓN: Basado en el historial {historial_texto}, detecta si hay números que salieron como corridos y ahora les toca ser fijo (vueltos).
    3. DETECCIÓN DE BOLA SORDA: ¿Qué decena o terminal ha desaparecido de la pizarra en las últimas 20 tripletas?

    ENTREGA:
    Presenta 5 Jugadas Maestras con este formato:
    ---
    ### 🎱 PIZARRA DE ALTA PRECISIÓN ###
    
    1. **[Número]** - (Nombre en Charada)
       - **Fuerza:** [X]% 
       - **Justificación:** (Breve análisis técnico basado en la tripleta {tripletas[0]} y el historial).

    ---
    **COMENTARIO DE PASILLO:** (Dime el pálpito de la calle sobre qué número está 'caliente' hoy).
    """

    # 5. LLAMADA A LA IA (GROQ)
    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Configura GROQ_API_KEY en Vercel."})

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Eres el experto máximo en bolita cubana. No saludas, vas directo al análisis técnico de la pizarra."},
                    {"role": "user", "content": prompt_maestro}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }, 
            headers={"Authorization": f"Bearer {GROQ_API_KEY.strip()}"}, 
            timeout=25
        )

        res_data = response.json()
        if "choices" not in res_data:
            error_msg = res_data.get("error", {}).get("message", "Error desconocido")
            return jsonify({"respuesta": f"❌ Error de análisis: {error_msg}"})

        return jsonify({"respuesta": res_data["choices"][0]["message"]["content"]})

    except Exception as e:
        return jsonify({"respuesta": f"❌ Error Crítico: {str(e)}"})

# Requisito para Vercel
app = app
