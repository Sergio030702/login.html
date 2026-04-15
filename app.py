import os
import requests
import re
import redis
from flask import Flask, render_template, jsonify, request
from charada_data import CHARADA

app = Flask(__name__)

# --- CONFIGURACIÓN DE ENTORNO ---
REDIS_URL = os.environ.get("loteria_db_REDIS_URL")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Conexión Robusta a Redis
try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5) if REDIS_URL else None
except:
    r = None

def obtener_datos_florida():
    """Extrae los últimos resultados de Florida Pick 3"""
    try:
        url = "https://www.lotteryusa.com/florida/pick-3/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        # Busca patrones tipo 1-2-3
        patron = re.findall(r'\d-\d-\d', res.text)
        # Extrae el terminal (ej: de 1-2-3 saca 03)
        return [c.split('-')[-1].zfill(2) for c in patron] if patron else []
    except Exception as e:
        print(f"Error web: {e}")
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    vivos = obtener_datos_florida()
    
    # 1. GESTIÓN DE BASE DE DATOS (REDIS)
    if r and vivos:
        try:
            # Guardamos los dos últimos sorteos (Día y Noche)
            r.lpush("historial_bolita", vivos[0], vivos[1])
            r.ltrim("historial_bolita", 0, 49) # Mantenemos los últimos 50
        except:
            pass

    # 2. VERIFICACIÓN DE TAREA PROGRAMADA (CRON)
    if request.headers.get("x-vercel-cron"):
        return jsonify({"status": "Base de datos actualizada", "data": vivos}), 200

    if not vivos:
        return jsonify({"respuesta": "⚠️ No se detectan resultados nuevos. Intente en unos minutos."})

    # 3. VARIABLES PARA EL PROMPT MAESTRO
    ultimo = vivos[0]
    significado_ultimo = CHARADA.get(ultimo, "Sin definir")
    historial_contexto = ", ".join(vivos[:10]) # Los últimos 10 para dar contexto estadístico

    # 4. PROMPT CON INGENIERÍA DE NIVEL SENIOR (V4.0)
    prompt_maestro = f"""
    ESTRICTO PROTOCOLO DE ANÁLISIS DE BOLITA CUBANA - MODELO PREDICTIVO V4.0

    PERFIL: Analista Jefe de Banco con 30 años de experiencia. Experto en Simetría Numérica, Ciclos de Atraso y Ley de Probabilidades Acumuladas.
    
    ENTRADA DE DATOS:
    - FIJO RECIENTE (Florida): {ultimo} ({significado_ultimo})
    - SECUENCIA DE SALIDA RECIENTE: {historial_contexto}
    - ESTADO DE DB: Historial en Redis analizado para detectar 'bolas sordas'.

    FASE 1: DIAGNÓSTICO TÉCNICO
    1. Analiza la 'Cábala de Arrastre': ¿Qué números jala el {ultimo} por tradición?
    2. Identifica 'Números Espejo': Si salió el {ultimo}, ¿cuál es su contraparte técnica?
    3. Evaluación de Vacíos: Basado en el historial, ¿qué terminales están atrasados?

    FASE 2: SALIDA DE PRONÓSTICOS PROFESIONALES
    Presenta 5 Jugadas Maestras con este formato exacto:
    
    ---
    ### 🎱 ANÁLISIS DE PIZARRA PROFESIONAL ###
    
    1. **[Número]** - (Nombre en Charada)
       - **Probabilidad:** [X]% 
       - **Justificación:** (Ej: "Arrastre directo del {ultimo}" o "Frecuencia acumulada")
    
    (Repetir hasta el 5, asegurando que los 5 números sean DIFERENTES entre sí)

    ---
    **RESUMEN DEL EXPERTO:** [Pronostica qué terminal o decena dominará la próxima tirada].
    """

    # 5. LLAMADA A LA IA (GROQ)
    try:
        if not GROQ_API_KEY:
            return jsonify({"respuesta": "❌ Error: GROQ_API_KEY no configurada."})

        headers_ai = {
            "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-70b-versatile", # Usamos el modelo 70B para mayor razonamiento
            "messages": [
                {"role": "system", "content": "Eres un experto en estadística de lotería y charada cubana."},
                {"role": "user", "content": prompt_maestro}
            ],
            "temperature": 0.65, # Balance perfecto entre lógica y creatividad
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            json=payload, 
            headers=headers_ai, 
            timeout=20
        )
        
        res_data = response.json()
        prediccion = res_data["choices"][0]["message"]["content"]
        
        return jsonify({"respuesta": prediccion})

    except Exception as e:
        return jsonify({"respuesta": f"❌ Error en el motor de análisis: {str(e)}"})

# Para despliegue en Vercel
app = app
