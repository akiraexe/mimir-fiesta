import os
import sqlite3
import re
from pathlib import Path

# ==========================================
# CONFIGURACIÓN DE RUTAS
# ==========================================
DB_PATH = Path(r".\base_datos\memoria_rag.db")
EXPORT_DIR = Path(r".\drive_export")

def rehidratar_fechas():
    print("=== INICIANDO REHIDRATACIÓN DE FECHAS EN MARKDOWN ===\n")
    
    if not DB_PATH.exists():
        print(f"[ERROR] No se encontró la base de datos en: {DB_PATH}")
        return
    if not EXPORT_DIR.exists():
        print(f"[ERROR] No se encontró el directorio de exportación en: {EXPORT_DIR}")
        return

    # Conectar a SQLite y cargar fechas en memoria para acceso rápido
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT id, fecha_inicio FROM conversaciones_staging")
    mapa_fechas = {str(row[0]): row[1] for row in cursor.fetchall()}
    conexion.close()

    print(f"[*] Se cargaron {len(mapa_fechas)} fechas de la base de datos.")

    archivos_modificados = 0
    archivos_ignorados = 0

    # Expresiones regulares para leer el ID y verificar si ya existe la fecha
    regex_id = re.compile(r'^id:\s*(\d+)$', re.MULTILINE)
    regex_fecha = re.compile(r'^fecha:\s*.*$', re.MULTILINE)

    for root, _, files in os.walk(EXPORT_DIR):
        for file_name in files:
            if not file_name.endswith(".md"):
                continue

            file_path = Path(root) / file_name
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()

            # Evitar procesar si ya tiene fecha
            if regex_fecha.search(contenido):
                archivos_ignorados += 1
                continue

            match_id = regex_id.search(contenido)
            if not match_id:
                archivos_ignorados += 1
                continue

            id_str = match_id.group(1)
            fecha_original = mapa_fechas.get(id_str)

            if fecha_original:
                # Inyectar la fecha justo debajo del ID en el bloque YAML
                nuevo_contenido = contenido.replace(
                    f"id: {id_str}\n",
                    f"id: {id_str}\nfecha: {fecha_original}\n"
                )
                
                with open(file_path, "w", encoding="utf-8") as f_out:
                    f_out.write(nuevo_contenido)
                
                archivos_modificados += 1

    print("\n=== RESUMEN DE REHIDRATACIÓN ===")
    print(f"Archivos modificados exitosamente: {archivos_modificados}")
    print(f"Archivos ignorados (ya tenían fecha o sin ID): {archivos_ignorados}")

if __name__ == "__main__":
    rehidratar_fechas()