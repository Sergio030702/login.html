import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# --- CONFIGURACIÓN DE ENTORNO ---
# Estas variables deben estar en Vercel -> Settings -> Environment Variables
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Conexión Segura a Redis
try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5) if REDIS_URL else None
except:
    r = None

def obtener_datos_florida():
    """Scraping de resultados de Florida Pick 3"""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        patron = re.findall(r'\d-\d-\d', res.text)
        # Extraemos el terminal (ej: de 1-2-3 sacamos el '03')
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except:
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_florida()
    
    # 1. ACTUALIZACIÓN DE HISTORIAL EN REDIS
    if r and vivos:
        try:
            # Guardamos los resultados actuales
            r.lpush("historial_bolita", *vivos)
            r.ltrim("historial_bolita", 0, 49) # Mantenemos los últimos 50 registros
        except:
            pass

    # 2. GESTIÓN DEL CRON (Solo para actualización automática)
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Base de datos sincronizada", "resultados": vivos}), 200

    if not vivos:
        return jsonify({"respuesta": "⚠️ La web de Florida no responde. Intenta de nuevo en unos segundos."})

    # 3. PREPARACIÓN DEL CONTEXTO PARA EL EXPERTO
    ultimo = vivos[0]
    significado_ultimo = CHARADA.get(ultimo, "Sin definir")
    # Recuperamos los últimos 10 de Redis para que la IA vea el patrón
    try:
        historial_ia = r.lrange("historial_bolita", 0, 9) if r else vivos[:10]
    except:
        historial_ia = vivos[:10]
    
    contexto_str = ", ".join(historial_ia)

    # 4. PROMPT DE INGENIERÍA V4.0 (EL BANQUERO VIEJO)
    prompt_maestro = f"""
    ESTRICTO PROTOCOLO DE ANÁLISIS DE BOLITA CUBANA - MODELO PREDICTIVO V4.0

    PERFIL: Analista Jefe de Banca con 30 años de experiencia. Experto en Simetría Numérica y Ciclos de Atraso.
    
    DATOS DE ENTRADA:
    - ÚLTIMO FIJO: {ultimo} ({significado_ultimo})
    - SECUENCIA RECIENTE: {contexto_str}
    - MÉTODO: Detección de 'Bolas Sordas' y 'Números de Arrastre'.

    TAREA:
    Proporciona 5 Jugadas Maestras basadas en la racha actual.
    
    FORMATO DE SALIDA:
    ### 🎱 ANÁLISIS DE PIZARRA PROFESIONAL ###
    
    1. **[Número]** - (Nombre en Charada)
       - **Probabilidad:** [X]% 
       - **Justificación:** (Breve análisis técnico de por qué este número es el 'vuelto' o compañero del {ultimo})

    (Repetir para 5 números DIFERENTES)

    ---
    **RESUMEN DEL EXPERTO:** [Una frase sobre la tendencia del día].
    """

    # 5. LLAMADA SEGURA A GROQ API
    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Error: Configura GROQ_API_KEY en Vercel."})

        headers_ai = {
            "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Eres un experto banquero de lotería cubana. Tu tono es profesional y técnico."},
                {"role": "user", "content": prompt_maestro}
            ],
            "temperature": 0.65,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            json=payload, 
            headers=headers_ai, 
            timeout=25
        )

        res_data = response.json()

        # Validación de respuesta para evitar error 'choices'
        if "choices" not in res_data:
            error_msg = res_data.get("error", {}).get("message", "Error desconocido")
            return jsonify({"respuesta": f"❌ Error de Groq: {error_msg}"})

        prediccion = res_data["choices"][0]["message"]["content"]
        return jsonify({"respuesta": prediccion})

    except Exception as e:
        return jsonify({"respuesta": f"❌ Error Crítico: {str(e)}"})

# Requisito para Vercel
app = app
