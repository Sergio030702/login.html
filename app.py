import os, re, requests, redis
from flask import Flask, render_template, jsonify
from datetime import datetime

# Importamos la charada
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# --- CONFIGURACIÓN DE INTELIGENCIA ---
def generar_analisis_ia(pizarra, fijo, rastro, significado):
    """
    Aquí es donde vive la lógica del prompt que enviamos a la IA.
    Prepara un análisis basado en los patrones que detectamos.
    """
    # Determinamos el turno
    hora_actual = datetime.now().hour
    turno_objetivo = "Noche" if hora_actual < 18 else "Mañana"
    
    # Construcción del Prompt de BI (Inteligencia de Negocio)
    prompt = f"""
    Basado en la pizarra {pizarra} con el fijo {fijo} ({significado}).
    El rastro histórico indica que después de estos números suelen venir: {rastro}.
    Objetivo: Pronóstico para la {turno_objetivo}.
    Analizando jales, terminales y el arrastre de los corridos...
    """
    # Aquí puedes conectar con Groq/OpenAI si tienes la API. 
    # Por ahora, generamos una respuesta lógica basada en los datos:
    proyeccion = f"Vigilar la decena del {fijo[0]}0 y los terminales del rastro ({rastro})."
    return proyeccion

def obtener_pizarra_bi():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get("https://www.lotteryusa.com/florida/", timeout=10, headers=headers)
        nums = re.findall(r'result-ball">(\d)', res.text)
        if len(nums) >= 9:
            p = f"{nums[1]}{nums[2]}{nums[3]}-{nums[4]}{nums[5]}-{nums[7]}{nums[8]}"
            f = f"{nums[2]}{nums[3]}"
            return p, f
    except:
        return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar_pronostico')
def generar_pronostico():
    # 1. Obtener datos actuales o de historial (Limpieza de basura)
    p, f = obtener_pizarra_bi()
    
    if not p:
        while r.lindex("historial_bolita", 0) and len(r.lindex("historial_bolita", 0)) < 5:
            r.lpop("historial_bolita")
        p = r.lindex("historial_bolita", 0) or "293-57-58"
        f = p.split('-')[0][-2:] if '-' in p else "93"
    else:
        # Guardar en historial si es nuevo
        if p != r.lindex("historial_bolita", 0):
            r.lpush("historial_bolita", p)
            r.ltrim("historial_bolita", 0, 100)

    # 2. Análisis de Rastro Profundo (Tu historial de marzo/abril)
    historial = r.lrange("historial_bolita", 0, -1)
    hits = []
    for i in range(len(historial) - 1):
        # Buscamos coincidencias en el pasado para predecir el futuro
        p_pasada = historial[i+1]
        if f in p_pasada and len(p_pasada) > 5:
            fijo_despues = historial[i].split('-')[0][-2:]
            hits.append(fijo_despues)
    
    rastro_lista = list(set(hits))[:3] if hits else ["83", "01", "85"]
    rastro_str = ", ".join(rastro_lista)
    
    # 3. Datos de Charada y Análisis IA
    significado = LISTA_CHARADA.get(f, "N/A")
    analisis_ia = generar_analisis_ia(p, f, rastro_str, significado)

    # 4. Respuesta completa para tu HTML
    # Agregué la llave 'ia' por si tu HTML la usa para mostrar el texto largo
    return jsonify({
        "pizarra": p,
        "fijo": f,
        "significado": significado,
        "rastro": rastro_str,
        "ia": analisis_ia,
        "objetivo": "NOCHE" if datetime.now().hour < 18 else "MAÑANA"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
