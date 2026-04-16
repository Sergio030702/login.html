import os, re, requests, redis
from flask import Flask, jsonify
from datetime import datetime

# Intento de importar charada, si no existe se crea vacío
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a Redis optimizada (30MB)
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# ==========================================
# CARGA DE DATOS INICIAL (MARZO-ABRIL)
# ==========================================
def cargar_datos_si_vacio():
    """Inyecta el historial de WhatsApp solo si Redis está vacío"""
    if r.llen("historial_bolita") == 0:
        datos = [
            "036-32-92", "815-63-22", "585-09-71", "801-21-25", "033-17-33", "397-22-12", "466-23-05", 
            "465-88-42", "985-56-93", "676-55-51", "196-75-59", "232-82-71", "675-95-21", "295-06-15", 
            "883-27-21", "310-01-85", "306-65-93", "656-60-50", "388-57-74", "170-80-88", "897-28-51", 
            "362-34-75", "126-25-59", "665-12-75", "506-42-75", "578-86-68", "605-57-99", "726-57-87", 
            "281-07-44", "821-87-37", "252-75-12", "715-50-43", "363-73-82", "831-00-20", "818-42-63", 
            "707-12-31", "956-79-66", "993-58-03", "224-42-33", "522-87-25", "099-21-83", "599-63-32", 
            "983-55-57", "845-88-21", "806-67-12", "518-43-90", "936-26-89", "053-30-27", "579-43-71", 
            "768-14-52", "665-90-25", "070-74-13", "512-18-43", "293-57-58", "656-61-23"
        ]
        for d in datos:
            r.rpush("historial_bolita", d)

# Ejecutar carga al iniciar la app
cargar_datos_si_vacio()

# ==========================================
# FUNCIONES DE APOYO
# ==========================================

def obtener_pizarra():
    """Busca los resultados en la web oficial"""
    try:
        # User-agent para evitar bloqueos básicos
        headers = {'User-Agent': 'Mozilla/5.0'}
        r4 = requests.get("https://www.lotteryusa.com/florida/pick-4/", timeout=10, headers=headers)
        r5 = requests.get("https://www.lotteryusa.com/florida/pick-5/", timeout=10, headers=headers)
        
        b4 = re.findall(r'result-ball">(\d)', r4.text)[:4]
        b5 = re.findall(r'result-ball">(\d)', r5.text)[:5]
        
        if len(b4) >= 4 and len(b5) >= 5:
            pizarra = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            fijo = f"{b4[2]}{b4[3]}"
            # Turno: Mediodía (M) antes de las 6 PM, Noche (N) después
            turno = "M" if datetime.now().hour < 18 else "N"
            return {"p": pizarra, "f": fijo, "t": turno}
    except Exception as e:
        print(f"Error scraping: {e}")
    return None

def buscar_rastro(pizarra_actual):
    """Analiza el historial en Redis para encontrar patrones"""
    if not pizarra_actual: return []
    
    historial = r.lrange("historial_bolita", 0, -1)
    # Extraer el fijo (los dos últimos dígitos antes del primer guion)
    fijo_hoy = pizarra_actual.split('-')[0][-2:]
    corridos_hoy = pizarra_actual.split('-')[1:]
    
    hits = []
    for i in range(len(historial) - 1, 0, -1):
        p_vieja = historial[i]
        # Si coincide el fijo o algún corrido
        if fijo_hoy in p_vieja or any(c in p_vieja for c in corridos_hoy):
            # Obtener el fijo del sorteo que ocurrió justo después
            try:
                despues = historial[i-1].split('-')[0][-2:]
                hits.append(despues)
            except: continue
            
    return list(set(hits))[:3]

# ==========================================
# RUTA PRINCIPAL
# ==========================================

@app.route('/')
def home():
    datos = obtener_pizarra()
    
    # PLAN B: Si la web oficial falla, usamos el historial
    if not datos:
        ultima_pizarra = r.lindex("historial_bolita", 0)
        if not ultima_pizarra:
            return "<h3>Error crítico: No hay conexión ni datos en historial.</h3>"
        
        rastro = buscar_rastro(ultima_pizarra)
        return jsonify({
            "estatus": "MODO HISTORIAL (Web Lotería no disponible)",
            "ultima_pizarra_en_db": ultima_pizarra,
            "objetivo_pronostico": "Actualización pendiente",
            "rastro_detectado": rastro,
            "nota": "Mostrando análisis basado en el último resultado guardado."
        })

    # PROCESO NORMAL: Si la web responde bien
    hoy = datetime.now().strftime("%Y%m%d")
    r.hset(f"lot:{hoy}:{datos['t']}", mapping={"res": datos['p'], "fijo": datos['f']})
    
    # Guardar en historial si es un resultado nuevo
    ultimo_guardado = r.lindex("historial_bolita", 0)
    if ultimo_guardado != datos['p']:
        r.lpush("historial_bolita", datos['p'])
        r.ltrim("historial_bolita", 0, 500)

    rastro = buscar_rastro(datos['p'])
    objetivo = "NOCHE" if datos['t'] == "M" else "MEDIODÍA de mañana"
    desc_fijo = LISTA_CHARADA.get(datos['f'], "Sin descripción en charada.py")

    return jsonify({
        "estatus": "SISTEMA ONLINE",
        "pizarra_actual": datos['p'],
        "fijo_hoy": f"{datos['f']} ({desc_fijo})",
        "pronostico_para": objetivo,
        "rastro_historico": rastro,
        "analisis": f"Basado en {datos['p']}, el historial sugiere vigilar: {rastro}"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
