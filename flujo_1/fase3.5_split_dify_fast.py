import json
from pathlib import Path

INPUT_FILE = Path(r".\rag_chunks_final.jsonl")
OUTPUT_PREFIX = "memoria_kodama_fast"
MAX_BYTES = 500 * 1024  # 500 KB por archivo para garantizar ingesta atómica ultrarrápida
SEPARATOR = "\n\n===DIFY_CHUNK_BOUNDARY===\n\n"

def preparar_archivos_ultrarrapidos():
    if not INPUT_FILE.exists():
        print(f"[ERROR] No se encontró el archivo: {INPUT_FILE}")
        return

    print("=== OPTIMIZANDO ARCHIVOS PARA LECTURA Y VECTORIZACIÓN RÁPIDA ===\n")
    
    file_index = 1
    current_size = 0
    total_chunks = 0
    
    out_file = open(f"{OUTPUT_PREFIX}_{file_index}.txt", 'w', encoding='utf-8')
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            data = json.loads(line)
            texto = data['text'] + SEPARATOR
            texto_bytes = texto.encode('utf-8')
            
            if current_size + len(texto_bytes) > MAX_BYTES:
                out_file.close()
                print(f"[+] Archivo {OUTPUT_PREFIX}_{file_index}.txt generado ({current_size / 1024:.1f} KB)")
                
                file_index += 1
                out_file = open(f"{OUTPUT_PREFIX}_{file_index}.txt", 'w', encoding='utf-8')
                current_size = 0
                
            out_file.write(texto)
            current_size += len(texto_bytes)
            total_chunks += 1
            
    out_file.close()
    print(f"[+] Archivo {OUTPUT_PREFIX}_{file_index}.txt generado ({current_size / 1024:.1f} KB)")
    
    print("\n=== RESUMEN DE OPTIMIZACIÓN ===")
    print(f"Total de fragmentos: {total_chunks}")
    print(f"Archivos pequeños listos: {file_index}")

if __name__ == "__main__":
    preparar_archivos_ultrarrapidos()