import os, re, requests, redis
from flask import Flask, jsonify
from datetime import datetime

# Intentamos importar la charada, si no existe creamos un diccionario vacío
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a Redis optimizada para 30MB
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# ==========================================
# CARGA DE DATOS (YA FORMATEADA PARA REDIS)
# ==========================================
def cargar_datos_si_vacio():
    """Solo inyecta los datos si la lista está vacía para no repetir"""
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

# Ejecutamos la carga al iniciar
cargar_datos_si_vacio()

# ==========================================
# FUNCIONES DE APOYO
# ==========================================

def obtener_pizarra():
    try:
        r4 = requests.get("https://www.lotteryusa.com/florida/pick-4/", timeout=10)
        r5 = requests.get("https://www.lotteryusa.com/florida/pick-5/", timeout=10)
        b4 = re.findall(r'result-ball">(\d)', r4.text)[:4]
        b5 = re.findall(r'result-ball">(\d)', r5.text)[:5]
        
        if b4 and b5:
            pizarra = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            fijo = f"{b4[2]}{b4[3]}"
            turno = "M" if datetime.now().hour < 18 else "N"
            return {"p": pizarra, "f": fijo, "t": turno}
    except: return None

def buscar_rastro(pizarra_actual):
    historial = r.lrange("historial_bolita", 0, -1)
    fijo_hoy = pizarra_actual.split('-')[0][-2:]
    corridos_hoy = pizarra_actual.split('-')[1:]
    
    hits = []
    # Buscamos coincidencias de fijo o corridos
    for i in range(len(historial) - 1, 0, -1):
        if fijo_hoy in historial[i] or any(c in historial[i] for c in corridos_hoy):
            despues = historial[i-1].split('-')[0][-2:]
            hits.append(despues)
    return list(set(hits))[:3]

# ==========================================
# RUTA PRINCIPAL (ESTA ES LA QUE ABRES)
# ==========================================

@app.route('/')
def home():
    datos = obtener_pizarra()
    if not datos:
        return "<h3>Error: No se pudo obtener la pizarra. Reintenta en un momento.</h3>"

    # 1. Guardar en Redis (Diferenciando por día y turno)
    hoy = datetime.now().strftime("%Y%m%d")
    r.hset(f"lot:{hoy}:{datos['t']}", mapping={"res": datos['p'], "fijo": datos['f']})
    
    # 2. Actualizar historial si el número es nuevo
    ultimo = r.lindex("historial_bolita", 0)
    if ultimo != datos['p']:
        r.lpush("historial_bolita", datos['p'])
        r.ltrim("historial_bolita", 0, 500) # Límite para no llenar los 30MB

    # 3. Analizar patrones
    rastro = buscar_rastro(datos['p'])
    objetivo = "NOCHE" if datos['t'] == "M" else "MEDIODÍA de mañana"
    desc_fijo = LISTA_CHARADA.get(datos['f'], "Sin descripción")

    # Aquí es donde verás el resultado en pantalla
    return jsonify({
        "estatus": "SISTEMA ONLINE",
        "pizarra_hoy": datos['p'],
        "fijo_actual": f"{datos['f']} ({desc_fijo})",
        "objetivo_pronostico": objetivo,
        "rastro_historico": rastro,
        "mensaje": f"Analizando qué salió después de combinaciones similares a {datos['f']}..."
    })

if __name__ == "__main__":
    # Render usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
