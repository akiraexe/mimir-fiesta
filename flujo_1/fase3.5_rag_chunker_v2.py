import os
import json
import re
from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================
EXPORT_DIR = Path(r".\drive_export")
OUTPUT_FILE = Path(r".\rag_chunks_final.jsonl")

# PASO 2: Categorías de exclusión estricta
EXCLUDED_CATEGORIES = {
    "07_Cultura_General_y_Consumo",
    "99_Archivo_Muerto_No_Clasificado"
}

TARGET_CHUNK_CHARS = 3000
OVERLAP_LINES = 8

def extract_metadata(content):
    """Extrae metadatos YAML, Título, Resumen y Contenido del Markdown."""
    metadata = {"id": "", "categoria": "", "fecha": ""}
    
    # YAML Frontmatter
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.MULTILINE | re.DOTALL)
    if yaml_match:
        for line in yaml_match.group(1).split('\n'):
            if line.startswith('id:'): metadata['id'] = line.split(':', 1)[1].strip()
            if line.startswith('categoria:'): metadata['categoria'] = line.split(':', 1)[1].strip()
            if line.startswith('fecha:'): metadata['fecha'] = line.split(':', 1)[1].strip()
    
    # Título (# Título)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    titulo = title_match.group(1).strip() if title_match else "Sin Título"
    
    # Resumen (**Resumen:** ...)
    resumen_match = re.search(r'\*\*Resumen:\*\*\s*(.+?)(?=\n##|\n\n)', content, re.DOTALL)
    resumen = resumen_match.group(1).strip() if resumen_match else "Sin resumen."
    
    # Contenido Principal
    content_match = re.search(r'## Contenido Original\n(.*)', content, re.DOTALL)
    texto_principal = content_match.group(1).strip() if content_match else content

    return metadata, titulo, resumen, texto_principal

def chunk_code_aware(text, max_chars, overlap_lines):
    """PASO 3: Divide el texto respetando los bloques de código y logs."""
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_len = 0
    in_code_block = False

    for line in lines:
        # Detectar apertura/cierre de bloques de código
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        current_chunk.append(line)
        current_len += len(line) + 1 # +1 por el salto de línea

        # Solo cortamos si superamos el tamaño Y NO estamos dentro de un bloque de código
        if current_len >= max_chars and not in_code_block:
            chunks.append('\n'.join(current_chunk))
            # Crear solapamiento (overlap)
            overlap = current_chunk[-overlap_lines:] if len(current_chunk) > overlap_lines else current_chunk
            current_chunk = overlap
            current_len = sum(len(l) + 1 for l in current_chunk)

    # Añadir el remanente final
    if current_chunk and len('\n'.join(current_chunk).strip()) > 50:
        chunks.append('\n'.join(current_chunk))

    return chunks

def build_rag_dataset():
    print("=== INICIANDO CHUNKING CODE-AWARE Y FILTRADO ===\n")
    
    total_archivos = 0
    archivos_ignorados = 0
    total_chunks = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for root, _, files in os.walk(EXPORT_DIR):
            for file_name in files:
                if not file_name.endswith(".md"):
                    continue
                    
                file_path = Path(root) / file_name
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    contenido = f.read()
                    
                meta, titulo, resumen, texto_principal = extract_metadata(contenido)
                
                # Exclusión categórica (Paso 2)
                if meta['categoria'] in EXCLUDED_CATEGORIES:
                    archivos_ignorados += 1
                    continue
                    
                total_archivos += 1
                
                # Fragmentación segura (Paso 3)
                fragmentos = chunk_code_aware(texto_principal, TARGET_CHUNK_CHARS, OVERLAP_LINES)
                
                for i, frag in enumerate(fragmentos):
                    # Inyección de Contexto en el vector
                    texto_enriquecido = f"Contexto: {titulo} ({meta['fecha']})\nResumen: {resumen}\n\n{frag}"
                    
                    chunk_data = {
                        "chunk_id": f"{meta['id']}_part_{i+1}",
                        "file_name": file_name,
                        "categoria": meta['categoria'],
                        "fecha": meta['fecha'],
                        "text": texto_enriquecido # Dify leerá este campo
                    }
                    f_out.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
                    total_chunks += 1
                    
    print("=== RESUMEN DE PROCESAMIENTO ===")
    print(f"Archivos válidos procesados: {total_archivos}")
    print(f"Archivos ignorados (Filtro): {archivos_ignorados}")
    print(f"Total de chunks generados:   {total_chunks}")
    print(f"Archivo JSONL listo:         {OUTPUT_FILE.name}")

if __name__ == "__main__":
    build_rag_dataset()