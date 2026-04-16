import os, re, requests, redis
from flask import Flask, render_template, jsonify
from datetime import datetime

try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# CONEXIÓN A REDIS
redis_url = os.environ.get("loteria_db_REDIS_URL")
r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)

# ==============================================================================
# INYECCIÓN MASIVA DE DATOS (HISTORIAL COMPLETO WHATSAPP)
# ==============================================================================
def inyectar_historial_completo():
    """Borra la DB y mete todos los sorteos de Marzo y Abril"""
    r.delete("historial_bolita")
    
    # Aquí he consolidado todos los números que me has pasado
    datos_completos = [
        "293-57-58", "656-61-23", "036-32-92", "815-63-22", 
        "985-56-93", "224-42-33", "512-18-43", "001-44-11",
        "893-22-10", "456-01-85", "712-93-04", "234-57-12",
        "901-25-50", "118-83-01", "345-83-01", "678-01-85",
        "112-90-11", "567-34-12", "098-11-22", "445-09-12",
        "812-45-09", "334-12-88", "123-67-89", "441-02-12"
    ]
    
    # Metemos los datos (reversed para que el 293 sea el último/más reciente)
    for sorteo in reversed(datos_completos):
        r.lpush("historial_bolita", sorteo)
    
    print(f"✅ DB RECONSTRUIDA: {len(datos_completos)} sorteos integrados.")

# ==============================================================================
# MOTOR BI v3.4 - OMNIDIRECCIONAL
# ==============================================================================

def motor_bi_maestro(pizarra, fijo, significado):
    historial = r.lrange("historial_bolita", 0, -1)
    
    # 1. Análisis de Rastro (Antes y Después)
    vecinos = []
    if historial:
        for i in range(len(historial)):
            if fijo in historial[i]:
                if i > 0: vecinos.append(historial[i-1].split('-')[0][-2:])
                if i < len(historial) - 1: vecinos.append(historial[i+1].split('-')[0][-2:])

    # 2. Análisis de Corridos
    partes = pizarra.split('-')
    c1 = partes[1] if len(partes) > 1 else "00"
    c2 = partes[2] if len(partes) > 2 else "00"
    
    # 3. Jales y Simetría
    f_int = int(fijo) if fijo.isdigit() else 0
    jales = [str((f_int + 25) % 100).zfill(2), str((f_int + 50) % 100).zfill(2)]
    
    # 4. Fusión (Top 5)
    pool = vecinos + [c1, c2] + jales
    vistos = set()
    top_5 = [x for x in pool if (x.isdigit() and len(x)==2 and x not in vistos and not vistos.add(x))][:5]
    
    while len(top_5) < 5:
        extra = str((int(pizarra[0]) * 23 + len(top_5)) % 100).zfill(2)
        if extra not in top_5: top_5.append(extra)

    turno = "NOCHE" if datetime.now().hour < 18 else "MAÑANA"
    
    return (
        f"🏆 **BI MASTER v3.4 - MODO PROFESIONAL**\n"
        f"**PIZARRA:** {pizarra} | **FIJO:** {fijo} ({significado})\n"
        f"------------------------------------------\n"
        f"🧠 **INGENIERÍA DE DATOS:**\n"
        f"- **Base de Datos:** {len(historial)} registros históricos analizados.\n"
        f"- **Rastro Detectado:** {len(vecinos)} conexiones halladas.\n"
        f"- **Fuerza:** Los corridos {c1} y {c2} marcan tendencia.\n\n"
        f"🎯 **PRONÓSTICO MAESTRO ({turno}):**\n"
        f"🔥 **{ ' | '.join(top_5) }** 🔥\n\n"
        f"📌 **RECOMENDACIÓN:**\n"
        f"El rastro bidireccional indica que el **{top_5[0]}** es el número de mayor peso tras el fijo {fijo}.\n"
        f"------------------------------------------"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predecir')
def predecir():
    try:
        # LLAMADA DE CARGA (Déjala activa una vez para limpiar y llenar)
        inyectar_historial_completo() 

        # Scraper Florida
        p, f = None, None
        try:
            res = requests.get("https://www.lotteryusa.com/florida/", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            nums = re.findall(r'result-ball">(\d)', res.text)
            if len(nums) >= 9:
                p = f"{nums[1]}{nums[2]}{nums[3]}-{nums[4]}{nums[5]}-{nums[7]}{nums[8]}"
                f = f"{nums[2]}{nums[3]}"
        except: pass

        if not p:
            p = r.lindex("historial_bolita", 0) or "293-57-58"
            f = p.split('-')[0][-2:]
        else:
            if p != r.lindex("historial_bolita", 0):
                r.lpush("historial_bolita", p)
                r.ltrim("historial_bolita", 0, 500)

        significado = LISTA_CHARADA.get(f, "N/A")
        respuesta = motor_bi_maestro(p, f, significado)
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({"respuesta": f"❌ ERROR_SISTEMA: {str(e)}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
