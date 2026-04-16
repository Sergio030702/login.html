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

def obtener_pizarra_real():
    """Busca los números con un tiempo de espera (timeout) más largo para evitar el error de conexión"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # Aumentamos el timeout a 15 segundos por si Render está lento
        r4 = requests.get("https://www.lotteryusa.com/florida/pick-4/", timeout=15, headers=headers)
        r5 = requests.get("https://www.lotteryusa.com/florida/pick-5/", timeout=15, headers=headers)
        
        b4 = re.findall(r'result-ball">(\d)', r4.text)[:4]
        b5 = re.findall(r'result-ball">(\d)', r5.text)[:5]
        
        if len(b4) >= 4 and len(b5) >= 5:
            p = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            f = f"{b4[2]}{b4[3]}"
            t = "M" if datetime.now().hour < 18 else "N"
            return {"p": p, "f": f, "t": t}
    except Exception as e:
        print(f"Error de conexión con Florida: {e}")
    return None

def buscar_rastro_limpio(pizarra_actual):
    if not pizarra_actual or len(pizarra_actual) < 5: return "Sin datos"
    historial = r.lrange("historial_bolita", 0, -1)
    fijo_hoy = pizarra_actual.split('-')[0][-2:]
    hits = []
    for i in range(len(historial) - 1):
        p_vieja = historial[i+1]
        if len(p_vieja) > 5 and fijo_hoy in p_vieja:
            fijo_despues = historial[i].split('-')[0][-2:]
            hits.append(fijo_despues)
    res = sorted(list(set(hits)), key=hits.count, reverse=True)[:3]
    return ", ".join(res) if res else "Analizando..."

@app.route('/')
def index():
    # 1. Limpieza automática del "01" y basura
    while r.lindex("historial_bolita", 0) and len(r.lindex("historial_bolita", 0)) < 5:
        r.lpop("historial_bolita")

    datos = obtener_pizarra_real()
    
    # Si falla la web, sacamos lo último del historial para que NO dé error de conexión
    if not datos:
        p = r.lindex("historial_bolita", 0) or "000-00-00"
        f = p.split('-')[0][-2:] if '-' in p else "00"
        objetivo = "Pendiente"
    else:
        p = datos['p']
        f = datos['f']
        objetivo = "NOCHE" if datos['t'] == "M" else "MAÑANA"
        if p != r.lindex("historial_bolita", 0):
            r.rpush("historial_bolita", p) # Usamos rpush para que no choque con la limpieza

    rastro_final = buscar_rastro_limpio(p)
    significado = LISTA_CHARADA.get(f, "N/A")

    # AQUÍ ESTÁ EL TRUCO: Pasamos las variables con los nombres que probablemente usa tu HTML
    return render_template('index.html', 
                           pizarra=p, 
                           fijo=f, 
                           significado=significado, 
                           rastro=rastro_final, 
                           objetivo=objetivo)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
