import os, re, requests, redis
from flask import Flask, render_template
from datetime import datetime

# Intentamos importar tu charada
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a tu Redis de 30MB
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# ==========================================
# MOTOR DE BÚSQUEDA Y LIMPIEZA
# ==========================================

def obtener_pizarra_real():
    """Busca los números en Florida con headers para evitar bloqueos"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r4 = requests.get("https://www.lotteryusa.com/florida/pick-4/", timeout=10, headers=headers)
        r5 = requests.get("https://www.lotteryusa.com/florida/pick-5/", timeout=10, headers=headers)
        b4 = re.findall(r'result-ball">(\d)', r4.text)[:4]
        b5 = re.findall(r'result-ball">(\d)', r5.text)[:5]
        
        if len(b4) >= 4 and len(b5) >= 5:
            p = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            f = f"{b4[2]}{b4[3]}"
            t = "M" if datetime.now().hour < 18 else "N"
            return {"p": p, "f": f, "t": t}
    except:
        return None

def buscar_rastro_limpio(pizarra_actual):
    """Analiza el historial ignorando datos basura como el '01'"""
    if not pizarra_actual or len(pizarra_actual) < 5: return []
    
    historial = r.lrange("historial_bolita", 0, -1)
    fijo_hoy = pizarra_actual.split('-')[0][-2:]
    
    hits = []
    for i in range(len(historial) - 1):
        p_vieja = historial[i+1]
        # Solo analizamos si la pizarra vieja es válida (formato 000-00-00)
        if len(p_vieja) > 5 and fijo_hoy in p_vieja:
            fijo_despues = historial[i].split('-')[0][-2:]
            if len(fijo_despues) == 2: # Solo fijos válidos
                hits.append(fijo_despues)
                
    return sorted(list(set(hits)), key=hits.count, reverse=True)[:3]

# ==========================================
# RUTA PRINCIPAL (CONECTA CON TU HTML)
# ==========================================

@app.route('/')
def home():
    # 1. Limpieza de emergencia de datos basura en Redis (el famoso "01")
    while r.lindex("historial_bolita", 0) and len(r.lindex("historial_bolita", 0)) < 5:
        r.lpop("historial_bolita")

    # 2. Intentar obtener pizarra nueva
    datos = obtener_pizarra_real()
    
    if not datos:
        # Si falla la web, usamos lo último bueno que tengamos
        p = r.lindex("historial_bolita", 0) or "Esperando..."
        f = p.split('-')[0][-2:] if '-' in p else "--"
        turno = "Pendiente"
    else:
        p = datos['p']
        f = datos['f']
        turno = "NOCHE" if datos['t'] == "M" else "MAÑANA"
        
        # Guardar en historial si es nuevo y válido
        if p != r.lindex("historial_bolita", 0):
            r.lpush("historial_bolita", p)
            r.ltrim("historial_bolita", 0, 200)

    # 3. Preparar variables para TU HTML
    rastro = buscar_rastro_limpio(p)
    significado = LISTA_CHARADA.get(f, "N/A")

    # Renderizamos TU archivo templates/index.html (o como se llame)
    return render_template('index.html', 
                           pizarra=p, 
                           fijo=f, 
                           significado=significado,
                           rastro=", ".join(rastro),
                           objetivo=turno)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
