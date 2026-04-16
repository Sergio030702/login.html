import os, re, requests, redis
from flask import Flask, jsonify
from datetime import datetime

# Intento de importar charada
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a Redis
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# ==========================================
# FUNCIONES DE EXTRACCIÓN (SCRAPER)
# ==========================================

def obtener_pizarra():
    """Busca resultados con un método más resistente a bloqueos"""
    urls = [
        "https://www.lotteryusa.com/florida/pick-4/",
        "https://www.lotteryusa.com/florida/pick-5/"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        # Buscamos Pick 4
        res4 = requests.get(urls[0], timeout=12, headers=headers)
        b4 = re.findall(r'result-ball">(\d)', res4.text)[:4]
        
        # Buscamos Pick 5
        res5 = requests.get(urls[1], timeout=12, headers=headers)
        b5 = re.findall(r'result-ball">(\d)', res5.text)[:5]
        
        if len(b4) >= 4 and len(b5) >= 5:
            # Pizarra: CentenaFijo - Corrido1 - Corrido2
            pizarra = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            fijo = f"{b4[2]}{b4[3]}"
            turno = "M" if datetime.now().hour < 18 else "N"
            return {"p": pizarra, "f": fijo, "t": turno}
    except Exception as e:
        print(f"Error de conexión: {e}")
    return None

def buscar_rastro(pizarra_actual):
    """Analiza el historial en Redis para buscar qué salió después de números similares"""
    if not pizarra_actual: return []
    
    historial = r.lrange("historial_bolita", 0, -1)
    partes = pizarra_actual.split('-')
    if len(partes) < 1: return []
    
    fijo_hoy = partes[0][-2:]
    corridos_hoy = partes[1:]
    
    hits = []
    # Escaneamos el pasado (del más nuevo al más viejo)
    for i in range(len(historial) - 1):
        p_pasada = historial[i+1] # El sorteo anterior en el historial
        # Si el fijo o corridos coinciden con lo que hubo en el pasado
        if fijo_hoy in p_pasada or any(c in p_pasada for c in corridos_hoy):
            # El "Rastro" es lo que salió JUSTO DESPUÉS de esa coincidencia
            despues = historial[i].split('-')[0][-2:]
            hits.append(despues)
            
    # Retornar los 3 más frecuentes sin repetir
    return sorted(list(set(hits)), key=hits.count, reverse=True)[:3]

# ==========================================
# RUTA PRINCIPAL
# ==========================================

@app.route('/')
def home():
    datos = obtener_pizarra()
    
    # Si la web falla, usamos el último guardado para no dar error
    if not datos:
        ultima_p = r.lindex("historial_bolita", 0)
        rastro = buscar_rastro(ultima_p)
        return jsonify({
            "estatus": "MODO HISTORIAL (Web Lotería en mantenimiento)",
            "ultima_pizarra_db": ultima_p,
            "rastro_detectado": rastro,
            "nota": "La web oficial no respondió. Mostrando análisis del último cierre."
        })

    # Si la web responde:
    # 1. Guardamos el resultado del día para control interno
    hoy = datetime.now().strftime("%Y-%m-%d")
    r.hset(f"registro:{hoy}:{datos['t']}", mapping={"p": datos['p'], "f": datos['f']})
    
    # 2. Actualizamos el historial general si el número es nuevo
    ultimo_h = r.lindex("historial_bolita", 0)
    if ultimo_h != datos['p']:
        r.lpush("historial_bolita", datos['p'])
        r.ltrim("historial_bolita", 0, 500) # Mantener historial sano bajo 30MB

    # 3. Generar análisis
    rastro = buscar_rastro(datos['p'])
    desc_fijo = LISTA_CHARADA.get(datos['f'], "N/A")
    proximo = "NOCHE" if datos['t'] == "M" else "MAÑANA"

    return jsonify({
        "estatus": "SISTEMA ONLINE",
        "pizarra_actual": datos['p'],
        "fijo_hoy": f"{datos['f']} - {desc_fijo}",
        "analisis_rastro": rastro,
        "pronostico_para": f"Sorteo de la {proximo}",
        "mensaje": f"Después de salir el {datos['f']}, el historial sugiere vigilar: {', '.join(rastro)}"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
