import os, re, requests, redis
from flask import Flask, jsonify, render_template
from datetime import datetime
# Asumo que tienes tu archivo charada.py con el diccionario LISTA_CHARADA
try:
    from charada import LISTA_CHARADA
except ImportError:
    LISTA_CHARADA = {}

app = Flask(__name__)

# Conexión a Redis (Ajustada a tus 30MB)
r = redis.Redis.from_url(os.environ.get("loteria_db_REDIS_URL"), decode_responses=True)

# ==========================================
# BLOQUE DE CARGA INICIAL (SOLO PARA EL MÓVIL)
# ==========================================
def cargar_historial_inicial():
    """Carga los datos de marzo y abril que pasaste por WhatsApp"""
    datos_raw = """
    036-3292, 815-6322, 585-0971, 801-2125, 033-1733, 397-2212, 466-2305, 465-8842, 
    985-5693, 676-5551, 196-7559, 232-8271, 675-9521, 295-0615, 883-2721, 310-0185, 
    306-6593, 656-6050, 388-5774, 170-8088, 897-2851, 362-3475, 126-2559, 665-1275, 
    506-4275, 578-8668, 605-5799, 726-5787, 281-0744, 821-8737, 252-7512, 715-5043, 
    363-7382, 831-0020, 818-4263, 707-1231, 956-7966, 993-5803, 224-4233, 522-8725, 
    099-2183, 599-6332, 983-5557, 845-8821, 806-6712, 518-4390, 936-2689, 053-3027, 
    579-4371, 768-1452, 665-9025, 070-7413, 512-1843, 293-5758, 656-6123
    """
    try:
        pizarras = [p.strip() for p in datos_raw.split(',')]
        for p in pizarras:
            if p and p not in r.lrange("historial_bolita", 0, -1):
                # rpush para mantener el orden cronológico
                r.rpush("historial_bolita", p)
        print("✅ Historial inyectado correctamente.")
    except Exception as e:
        print(f"Error en carga: {e}")

# Ejecutar carga al arrancar
cargar_historial_inicial()

# ==========================================
# LÓGICA DE EXTRACCIÓN Y ANÁLISIS
# ==========================================

def obtener_pizarra_real():
    """Extrae Pick 4 y Pick 5 y arma la línea cubana"""
    try:
        r4 = requests.get("https://www.lotteryusa.com/florida/pick-4/", timeout=8)
        r5 = requests.get("https://www.lotteryusa.com/florida/pick-5/", timeout=8)
        b4 = re.findall(r'result-ball">(\d)', r4.text)[:4]
        b5 = re.findall(r'result-ball">(\d)', r5.text)[:5]
        
        if b4 and b5:
            # Formato: CentenaFijo - Corrido1 - Corrido2
            pizarra = f"{b4[1]}{b4[2]}{b4[3]}-{b5[0]}{b5[1]}-{b5[3]}{b5[4]}"
            fijo = f"{b4[2]}{b4[3]}"
            # Turno: M (Mediodía) antes de las 6PM, N (Noche) después
            turno = "M" if datetime.now().hour < 18 else "N"
            return {"p": pizarra, "f": fijo, "t": turno}
    except:
        return None

def buscar_rastro_profundo(pizarra_actual):
    """Busca coincidencias de Fijo o Corridos en el historial"""
    historial = r.lrange("historial_bolita", 0, -1)
    if not historial: return []
    
    fijo_hoy = pizarra_actual.split('-')[0][-2:]
    corridos_hoy = pizarra_actual.split('-')[1:]
    
    sugerencias = []
    # Buscamos en los 500 registros que permite tu Redis
    for i in range(len(historial) - 1, 0, -1):
        p_vieja = historial[i]
        # Si el fijo viejo coincide con el de hoy O los corridos coinciden
        if fijo_hoy in p_vieja or any(c in p_vieja for c in corridos_hoy):
            # Miramos qué salió en el sorteo de después (i-1)
            proximo_fijo = historial[i-1].split('-')[0][-2:]
            sugerencias.append(proximo_fijo)
            
    # Devolvemos los 3 más frecuentes sin repetir
    return list(set(sugerencias))[:3]

@app.route('/api/predecir')
def predecir():
    datos = obtener_pizarra_real()
    if not datos:
        return jsonify({"error": "No se pudo conectar con la fuente de datos."})

    # 1. Guardar con Sobrescritura (Usa la fecha y turno como llave)
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    r.hset(f"lot:{fecha_hoy}:{datos['t']}", mapping={
        "res": datos['p'], 
        "fijo": datos['f']
    })
    
    # 2. Actualizar Historial General (Solo si el número es nuevo)
    ultimo = r.lindex("historial_bolita", 0)
    if ultimo != datos['p']:
        r.lpush("historial_bolita", datos['p'])
        r.ltrim("historial_bolita", 0, 500) # Límite de seguridad para tus 30MB

    # 3. Análisis de Rastro y Turno
    rastro = buscar_rastro_profundo(datos['p'])
    objetivo = "NOCHE" if datos['t'] == "M" else "MEDIODÍA de mañana"
    significado = LISTA_CHARADA.get(datos['f'], "Sin dato")

    # 4. Prompt para la IA (Aquí integras tu llamada a Groq)
    prompt_ia = f"""
    Eres un experto en Business Intelligence aplicado a la Lotería de Florida.
    Pizarra actual ({datos['t']}): {datos['p']}
    Fijo: {datos['f']} ({significado})
    
    HISTORIAL DE RASTRO:
    En sorteos pasados similares, los números que salieron después fueron: {rastro}
    
    TAREA: Predice para el sorteo de la {objetivo}.
    Considera jales de charada, repetición de terminales y el rastro histórico.
    Dime los 3 prospectos más fuertes.
    """

    return jsonify({
        "pizarra": datos['p'],
        "turno_actual": datos['t'],
        "prediccion_para": objetivo,
        "rastro_detectado": rastro,
        "analisis_ia": "Aquí se envía el prompt a Groq..."
    })

if __name__ == "__main__":
    app.run(debug=True)
