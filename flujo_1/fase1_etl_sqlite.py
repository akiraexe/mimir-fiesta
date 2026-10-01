import json
import sqlite3
import hashlib
import re
from datetime import datetime
import tiktoken
from markdownify import markdownify as md

# ==========================================
# CONFIGURACIÓN DEL ENTORNO
# ==========================================
JSON_PATH = r".\datos_crudos\MyActivity.json"
DB_PATH = r".\base_datos\memoria_rag.db"
MAX_MINUTES_INACTIVITY = 60
MAX_TOKENS = 8000

# Inicializar tokenizador (usamos cl100k_base que es estándar y rápido)
enc = tiktoken.get_encoding("cl100k_base")

def inicializar_base_datos():
    """Crea la base de datos y la tabla de staging con codificación UTF-8."""
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversaciones_staging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash_hilo TEXT UNIQUE,
            fecha_inicio TEXT,
            texto_limpio TEXT,
            cantidad_tokens INTEGER,
            llm_categoria TEXT,
            llm_titulo TEXT,
            llm_resumen TEXT,
            estado TEXT DEFAULT 'pendiente'
        )
    ''')
    conexion.commit()
    return conexion

def parsear_fecha(fecha_str):
    """Convierte el string ISO 8601 de Google a un objeto datetime manejable."""
    # Ejemplo: "2026-04-28T08:06:50.211Z"
    fecha_limpia = fecha_str.replace('Z', '+00:00')
    return datetime.fromisoformat(fecha_limpia)

def limpiar_input_usuario(texto_crudo):
    """Elimina las marcas de telemetría de Google ('Prompted', 'Branched')."""
    if not texto_crudo:
        return ""
    # Quita "Prompted " o "Branched " al inicio del string
    texto_limpio = re.sub(r'^(Prompted\s+|Branched\s+)', '', texto_crudo, flags=re.IGNORECASE)
    return texto_limpio.strip()

def generar_hash(texto):
    """Genera un SHA-256 del contenido para evitar duplicados en la BD."""
    # Quitamos espacios extra para que variaciones mínimas de formateo no rompan el hash
    texto_normalizado = re.sub(r'\s+', '', texto)
    return hashlib.sha256(texto_normalizado.encode('utf-8')).hexdigest()

def procesar_takeout():
    print("[*] Iniciando ETL Fase 1: JSON a SQLite...")
    conexion = inicializar_base_datos()
    cursor = conexion.cursor()

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    # Google Takeout a veces viene en orden inverso, aseguramos orden cronológico
    print("[*] Ordenando eventos cronológicamente...")
    datos.sort(key=lambda x: x.get('time', ''))

    hilo_actual_texto = ""
    hilo_actual_tokens = 0
    hilo_inicio_fecha = None
    ultima_fecha_evento = None
    hilos_guardados = 0
    hilos_duplicados = 0

    print("[*] Procesando eventos...")
    for evento in datos:
        # 1. Ignorar adjuntos y eventos vacíos: Solo nos interesa si hay HTML de respuesta
        if 'safeHtmlItem' not in evento or not evento['safeHtmlItem']:
            continue
        
        # 2. Extracción y Limpieza
        fecha_evento = parsear_fecha(evento['time'])
        input_usuario = limpiar_input_usuario(evento.get('title', ''))
        html_respuesta = evento['safeHtmlItem'][0].get('html', '')
        
        # Transpilación de HTML a Markdown (Preserva YAML, código, tablas)
        respuesta_md = md(html_respuesta, heading_style="ATX").strip()

        # Ensamblar el bloque de este turno
        bloque_turno = f"**Usuario:**\n{input_usuario}\n\n**Gemini:**\n{respuesta_md}\n\n---\n\n"
        tokens_turno = len(enc.encode(bloque_turno))

        # 3. Lógica de Segmentación (Corte)
        cortar_hilo = False
        
        if hilo_inicio_fecha is None:
            hilo_inicio_fecha = fecha_evento
            ultima_fecha_evento = fecha_evento

        # Evaluar inactividad (Regla 1)
        minutos_inactividad = (fecha_evento - ultima_fecha_evento).total_seconds() / 60
        if minutos_inactividad > MAX_MINUTES_INACTIVITY and hilo_actual_texto:
            cortar_hilo = True

        # Evaluar saturación de tokens (Regla 2)
        if (hilo_actual_tokens + tokens_turno) > MAX_TOKENS and hilo_actual_texto:
            cortar_hilo = True

        # 4. Guardar en Base de Datos
        if cortar_hilo:
            hash_unico = generar_hash(hilo_actual_texto)
            try:
                cursor.execute('''
                    INSERT INTO conversaciones_staging 
                    (hash_hilo, fecha_inicio, texto_limpio, cantidad_tokens)
                    VALUES (?, ?, ?, ?)
                ''', (hash_unico, hilo_inicio_fecha.strftime("%Y-%m-%d %H:%M:%S"), hilo_actual_texto, hilo_actual_tokens))
                conexion.commit()
                hilos_guardados += 1
            except sqlite3.IntegrityError:
                hilos_duplicados += 1 # El hash ya existe (ej. un 'Branched' regenerado)

            # Reiniciar variables para el siguiente hilo
            hilo_actual_texto = ""
            hilo_actual_tokens = 0
            hilo_inicio_fecha = fecha_evento

        # Acumular el turno actual al hilo
        hilo_actual_texto += bloque_turno
        hilo_actual_tokens += tokens_turno
        ultima_fecha_evento = fecha_evento

    # Guardar el último remanente si el JSON terminó y quedó texto en memoria
    if hilo_actual_texto:
        hash_unico = generar_hash(hilo_actual_texto)
        try:
            cursor.execute('''
                INSERT INTO conversaciones_staging 
                (hash_hilo, fecha_inicio, texto_limpio, cantidad_tokens)
                VALUES (?, ?, ?, ?)
            ''', (hash_unico, hilo_inicio_fecha.strftime("%Y-%m-%d %H:%M:%S"), hilo_actual_texto, hilo_actual_tokens))
            conexion.commit()
            hilos_guardados += 1
        except sqlite3.IntegrityError:
            hilos_duplicados += 1

    conexion.close()
    print("==================================================")
    print("REPORTE DE EXTRACCIÓN (FASE 1)")
    print("==================================================")
    print(f"Hilos limpios guardados en SQLite: {hilos_guardados}")
    print(f"Hilos duplicados omitidos (Branched/Regenerate): {hilos_duplicados}")
    print("[*] Proceso completado exitosamente.")

if __name__ == "__main__":
    procesar_takeout()