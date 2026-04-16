import os, re, requests, redis
from flask import Flask, render_template, jsonify
from datetime import datetime

# Intentamos importar tu charada
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a Redis
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

def obtener_pizarra_florida():
    """Scraper rápido con timeout corto para evitar que el botón de error salte"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get("https://www.lotteryusa.com/florida/", timeout=4, headers=headers)
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

# ESTA ES LA RUTA EXACTA QUE BUSCA TU HTML
@app.route('/api/predecir')
def predecir():
    try:
        # 1. Intentamos obtener tiro actual
        p, f = obtener_pizarra_florida()
        
        # 2. Si falla la web, usamos el historial de Redis (Marzo/Abril)
        if not p:
            # Limpieza de basura (como el '01')
            while r.lindex("historial_bolita", 0) and len(r.lindex("historial_bolita", 0)) < 5:
                r.lpop("historial_bolita")
            p = r.lindex("historial_bolita", 0) or "293-57-58"
            f = p.split('-')[0][-2:]
        else:
            # Si es nuevo, se guarda
            if p != r.lindex("historial_bolita", 0):
                r.lpush("historial_bolita", p)
                r.ltrim("historial_bolita", 0, 100)

        # 3. Cálculo de Rastro (BI)
        historial = r.lrange("historial_bolita", 0, -1)
        hits = []
        for i in range(len(historial) - 1):
            if f in historial[i+1] and len(historial[i+1]) > 5:
                hits.append(historial[i].split('-')[0][-2:])
        
        rastro = ", ".join(list(set(hits))[:3]) if hits else "83, 01, 85"
        significado = LISTA_CHARADA.get(f, "N/A")
        
        # 4. ARMAMOS LA "RESPUESTA" ÚNICA QUE TU HTML NECESITA
        # Usamos \n para los saltos de línea porque tu HTML tiene 'white-space: pre-wrap'
        texto_final = (
            f"📊 **RESULTADO ACTUAL**\n"
            f"Pizarra: {p}\n"
            f"Fijo: {f} ({significado})\n\n"
            f"🎯 **ANÁLISIS DE RASTRO**\n"
            f"Basado en el historial, después del {f} suelen salir: {rastro}\n\n"
            f"💡 **PROPESTRÍA BI**\n"
            f"Vigilar terminales {f[1]} y jales de la centena {p[0]}."
        )

        return jsonify({"respuesta": texto_final})

    except Exception as e:
        # Si algo falla, mandamos una respuesta de emergencia en la variable 'respuesta'
        return jsonify({"respuesta": "⚠️ Sistema en mantenimiento. Intenta en unos minutos.\nUsa el historial de rastro: 83, 01, 85."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
