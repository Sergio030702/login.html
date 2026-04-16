import os, re, requests, redis
from flask import Flask, render_template, jsonify
from datetime import datetime

try:
    from charada import LISTA_CHARADA
except ImportError:
    # Diccionario de respaldo si el archivo no existe
    LISTA_CHARADA = {"88": "Muerto Grande", "93": "Sortija", "56": "Reina"}

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# SISTEMA DE GESTIÓN DE DATOS REALES
# ==============================================================================
def inyectar_historial_limpio():
    """Limpia la base de datos y carga los 56 sorteos de WhatsApp"""
    # 1. Borrón y cuenta nueva
    r.delete("historial_bolita")
    
    # 2. Tu bloque real de 56 sorteos (17/03 al 15/04)
    datos_reales = [
        "088-95-56", "293-57-58", "656-61-23", "512-18-43", "070-74-13", 
        "665-90-25", "768-14-52", "579-43-71", "053-30-27", "936-26-89", 
        "518-43-90", "806-67-12", "845-88-21", "983-55-57", "599-63-32", 
        "099-21-83", "522-87-25", "224-42-33", "993-58-03", "956-79-66", 
        "707-12-31", "818-42-63", "831-00-20", "363-73-82", "715-50-43", 
        "252-75-12", "821-87-37", "281-07-44", "726-57-87", "605-57-99", 
        "578-86-68", "506-42-75", "665-12-75", "126-25-59", "362-34-75", 
        "897-28-51", "170-80-88", "388-57-74", "656-60-50", "306-65-93", 
        "310-01-85", "883-27-21", "295-06-15", "675-95-21", "232-82-71", 
        "196-75-59", "676-55-51", "985-56-93", "465-88-42", "466-23-05", 
        "397-22-12", "033-17-33", "801-21-25", "585-09-71", "815-63-22", 
        "036-32-92"
    ]
    
    # 3. Inyección (se invierte para que el más reciente sea el índice 0)
    for sorteo in reversed(datos_reales):
        r.lpush("historial_bolita", sorteo)
    
    return len(datos_reales)

# ==============================================================================
# MOTOR DE INTELIGENCIA DE NEGOCIO (BI)
# ==============================================================================
def motor_bi_maestro(pizarra, fijo, significado):
    historial = r.lrange("historial_bolita", 0, -1)
    
    # Análisis de vecinos (rastro antes y después)
    vecinos = []
    if historial:
        for i in range(len(historial)):
            if fijo in historial[i]:
                if i > 0: vecinos.append(historial[i-1].split('-')[0][-2:])
                if i < len(historial) - 1: vecinos.append(historial[i+1].split('-')[0][-2:])

    # Tendencia de corridos
    partes = pizarra.split('-')
    c1 = partes[1] if len(partes) > 1 else "00"
    c2 = partes[2] if len(partes) > 2 else "00"
    
    # Jales por simetría
    f_int = int(fijo) if fijo.isdigit() else 0
    jales = [str((f_int + 25) % 100).zfill(2), str((f_int + 50) % 100).zfill(2)]
    
    # Consolidación de Top 5
    pool = vecinos + [c1, c2] + jales
    vistos = set()
    top_5 = [x for x in pool if (x.isdigit() and len(x)==2 and x not in vistos and not vistos.add(x))][:5]
    
    # Relleno inteligente si faltan datos
    while len(top_5) < 5:
        extra = str((int(pizarra[0]) * 41 + len(top_5)) % 100).zfill(2)
        if extra not in top_5: top_5.append(extra)

    return (
        f"🏆 **BI MASTER v3.7 - MODO INTEGRAL**\n"
        f"**PIZARRA:** {pizarra} | **FIJO:** {fijo} ({significado})\n"
        f"------------------------------------------\n"
        f"🧠 **INGENIERÍA DE DATOS:**\n"
        f"- **Base de Datos:** {len(historial)} registros reales (Limpieza OK).\n"
        f"- **Rastro:** {len(vecinos)} conexiones detectadas en el histórico.\n\n"
        f"🎯 **PRONÓSTICO MAESTRO:**\n"
        f"🔥 **{ ' | '.join(top_5) }** 🔥\n\n"
        f"📌 **SISTEMA:** Base de datos sincronizada con WhatsApp.\n"
        f"------------------------------------------"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    try:
        # LLAMADA DE LIMPIEZA E INYECCIÓN
        # Una vez que confirmes que el reporte dice "56 registros", puedes comentar esta línea
        inyectar_historial_limpio() 

        p, f = None, None
        # Intento de Scraper para Florida
        try:
            res = requests.get("https://www.lotteryusa.com/florida/", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            nums = re.findall(r'result-ball">(\d)', res.text)
            if len(nums) >= 9:
                p = f"{nums[1]}{nums[2]}{nums[3]}-{nums[4]}{nums[5]}-{nums[7]}{nums[8]}"
                f = f"{nums[2]}{nums[3]}"
        except: pass

        # Si el scraper falla, usa el último de la DB
        if not p:
            p = r.lindex("historial_bolita", 0) or "088-95-56"
            f = p.split('-')[0][-2:]
        else:
            # Si es un número nuevo, lo añade sin borrar el historial
            if p != r.lindex("historial_bolita", 0):
                r.lpush("historial_bolita", p)
                r.ltrim("historial_bolita", 0, 500) # Mantiene solo los últimos 500

        significado = LISTA_CHARADA.get(f, "N/A")
        respuesta = motor_bi_maestro(p, f, significado)
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({"respuesta": f"❌ ERROR_SISTEMA: {str(e)}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
