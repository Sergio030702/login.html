import os
import requests
import re
from flask import Flask, render_template, jsonify
from upstash_redis import Redis
from charada_data import CHARADA

app = Flask(__name__)

# Configuración de APIs
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# Conexión a Redis (Coche de Almendras)
redis = Redis(
    url=os.environ.get("KV_REST_API_URL"), 
    token=os.environ.get("KV_REST_API_TOKEN")
)

def obtener_datos_web():
    """Busca resultados reales en la web."""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

def gestionar_horarios(nuevos):
    """Guarda los números por horario. Si no hay Redis, no rompe el código."""
    try:
        if len(nuevos) < 2: return None
        noche_hoy, dia_hoy = nuevos[0], nuevos[1]

        # Guardar por horario (Día/Noche)
        for llave, valor in [("historial_noche", noche_hoy), ("historial_dia", dia_hoy)]:
            historial = redis.lrange(llave, 0, 0)
            if not historial or (len(historial) > 0 and historial[0] != valor):
                redis.lpush(llave, valor)
                redis.ltrim(llave, 0, 49)

        # Guardar en historial general
        h_gen = redis.lrange("historial_bolita", 0, 1)
        for n in reversed([dia_hoy, noche_hoy]):
            if n not in h_gen:
                redis.lpush("historial_bolita", n)
        redis.ltrim("historial_bolita", 0, 99)
        
        return {"dia": dia_hoy, "noche": noche_hoy}
    except Exception as e:
        print(f"Aviso Redis: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    # 1. Obtener datos frescos de la web
    vivos = obtener_datos_web()
    res_horarios = gestionar_horarios(vivos)
    
    # Si es el Cron Job (actualización automática)
    if "x-vercel-cron" in requests.headers:
        return jsonify({"status": "Actualizado"}), 200

    # 2. Recuperar historial para la IA
    try:
        h_completo = redis.lrange("historial_bolita", 0, 20) or vivos
        h_dia = redis.lrange("historial_dia", 0, 10) or ([vivos[1]] if len(vivos)>1 else [])
        h_noche = redis.lrange("historial_noche", 0, 10) or ([vivos[0]] if vivos else [])
    except:
        h_completo = vivos
        h_dia = [vivos[1]] if len(vivos)>1 else []
        h_noche = [vivos[0]] if vivos else []

    if not h_completo:
        return jsonify({"respuesta": "⚠️ No hay datos disponibles. Intenta en un momento."})

    # 3. Definir el último número y su significado
    ultimo = h_completo[0]
    significado = CHARADA.get(ultimo, "Significado variado")

    # 4. Llamada a la IA
    prompt = f"""
    Eres 'Bolita IA Master'. 
    DATOS:
    - Último sorteo: {ultimo} ({significado})
    - Tendencia Mediodía: {h_dia[:5]}
    - Tendencia Noche: {h_noche[:5]}
    - Historial: {h_completo[:10]}
    
    TAREA:
    1. Basado en que el último fue {ultimo}, ¿qué números de la charada suelen salir?
    2. Dame 5 pronósticos en **negrita**.
    3. Para cada número, indica TODOS sus significados de la charada cubana.
    4. Sé breve y técnico.
    """

    try:
        if not GROQ_API_KEY: return jsonify({"respuesta": "❌ Falta API KEY"})
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return jsonify({"respuesta": f"❌ Error de IA ({response.status_code})."})
            
        return jsonify({"respuesta": response.json()["choices"][0]["message"]["content"]})
    except Exception as e:
        return jsonify({"respuesta": f"❌ Error de conexión: {str(e)}"})
