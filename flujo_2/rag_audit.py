import json
from pathlib import Path

def audit_chunks(jsonl_path: str = "rag_chunks.jsonl") -> None:
    path = Path(__file__).parent.resolve() / jsonl_path
    if not path.exists():
        print(f"[ERROR] No se encontró el archivo: {jsonl_path}")
        return

    sizes = []
    tokens = []
    headers_found = 0
    over_limit = 0   # Fragmentos > 4,000 caracteres (~1,000 tokens)
    under_limit = 0  # Fragmentos < 100 caracteres (~25 tokens)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            c_len = data.get("char_count", 0)
            t_est = data.get("estimated_tokens", 0)
            
            sizes.append(c_len)
            tokens.append(t_est)

            if data.get("section_header"):
                headers_found += 1
            if c_len > 4000:
                over_limit += 1
            if c_len < 100:
                under_limit += 1

    total = len(sizes)
    print("=== AUDITORÍA DE DISTRIBUCIÓN DE CHUNKS ===")
    print(f"Total de chunks analizados: {total}")
    print(f"Promedio de caracteres:     {sum(sizes) / total:.1f}")
    print(f"Promedio de tokens est.:    {sum(tokens) / total:.1f}")
    print(f"Rango de caracteres:        Mín {min(sizes)} | Máx {max(sizes)}")
    print(f"Chunks con encabezado:      {headers_found} ({headers_found / total * 100:.1f}%)")
    print(f"Alertas (> 4,000 chars):    {over_limit}")
    print(f"Alertas (< 100 chars):      {under_limit}")

if __name__ == "__main__":
    audit_chunks()