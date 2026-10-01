import sqlite3
import os
import re

DB_PATH = r"X:\Proyectos\RAG_Takeout\base_datos\memoria_rag.db"
OUTPUT_DIR = r"X:\Proyectos\RAG_Takeout\drive_export"

CATEGORIAS_OFICIALES = [
    "01_NetNAVI_Infraestructura_Sistemas",
    "02_NetNAVI_Desarrollo_Automatizacion",
    "03_Fiscal_Administrativo_CDMX",
    "04_Proyectos_Creativos_y_Narrativa",
    "05_Filosofia_y_Cuidado_Personal",
    "06_Logistica_y_Gestion_Familiar",
    "07_Cultura_General_y_Consumo",
    "99_Archivo_Muerto_No_Clasificado"
]

def inicializar_carpetas():
    if not os.path.exists(OUTPUT_DIR): 
        os.makedirs(OUTPUT_DIR)
    for cat in CATEGORIAS_OFICIALES:
        ruta_cat = os.path.join(OUTPUT_DIR, cat)
        if not os.path.exists(ruta_cat): 
            os.makedirs(ruta_cat)

def sanitizar_nombre(titulo):
    """Limpia el título para que sea un nombre de archivo válido en Windows."""
    if not titulo:
        return "Sin_Titulo"
    return re.sub(r'[\\/*?:"<>|]', "", str(titulo)).replace(" ", "_")

def exportar_a_markdown():
    print("[*] Iniciando exportación masiva a Markdown...")
    inicializar_carpetas()
    
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    
    # Apuntamos a la tabla correcta y traemos los metadatos generados por Gemini/Gemma
    cursor.execute("""
        SELECT id, llm_categoria, llm_titulo, texto_limpio, llm_resumen 
        FROM conversaciones_staging 
        WHERE estado = 'procesado'
    """)
    registros = cursor.fetchall()
    
    count = 0
    for id_reg, categoria, titulo, texto, resumen in registros:
        # Validar que la categoría exista, si no, al archivo muerto
        cat_final = categoria if categoria in CATEGORIAS_OFICIALES else "99_Archivo_Muerto_No_Clasificado"
        
        nombre_limpio = sanitizar_nombre(titulo)
        nombre_archivo = f"ID_{id_reg}_{nombre_limpio}.md"
        ruta_completa = os.path.join(OUTPUT_DIR, cat_final, nombre_archivo)
        
        # Construir el contenido del Markdown con un Frontmatter limpio
        contenido_md = f"""---
id: {id_reg}
categoria: {cat_final}
---

# {titulo or f'Registro {id_reg}'}

**Resumen:** {resumen or 'Sin resumen generado.'}

## Contenido Original
{texto or 'Sin contenido.'}
"""
        with open(ruta_completa, "w", encoding="utf-8") as archivo_md:
            archivo_md.write(contenido_md)
            
        count += 1
            
    conexion.close()
    print(f"[+] Proceso terminado exitosamente. Se exportaron {count} archivos a {OUTPUT_DIR}.")
    print("[*] Siguiente paso: Puedes ejecutar tu script 'sync_rclone.bat' para subir todo a Google Drive.")

if __name__ == "__main__":
    exportar_a_markdown()