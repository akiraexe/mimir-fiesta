import json
import re
from pathlib import Path

# Parámetros del Chunker
MANIFEST_FILE = "rag_manifest.json"
OUTPUT_FILE = "rag_chunks.jsonl"
TARGET_CHUNK_SIZE = 2500  # Caracteres aprox (~600 tokens)
OVERLAP_SIZE = 300       # Caracteres de solapamiento (~75 tokens)


def split_markdown_by_headers(content: str) -> list:
    """
    Divide el contenido Markdown preservando la jerarquía de encabezados (#, ##, ###).
    """
    header_pattern = re.compile(r'^(#{1,6}\s+.*)$', re.MULTILINE)
    matches = list(header_pattern.finditer(content))

    if not matches:
        return [{"header": "General", "content": content}]

    sections = []
    if matches[0].start() > 0:
        pre_text = content[:matches[0].start()].strip()
        if pre_text:
            sections.append({"header": "Encabezado General", "content": pre_text})

    for i, match in enumerate(matches):
        header = match.group(1).strip()
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start_pos:end_pos].strip()

        if section_content:
            sections.append({"header": header, "content": section_content})

    return sections


def recursive_chunk_text(text: str, max_chars: int = TARGET_CHUNK_SIZE, overlap: int = OVERLAP_SIZE) -> list:
    """
    Subdivide secciones extensas respetando párrafos y aplicando solapamiento.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
            else:
                lines = para.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 <= max_chars:
                        current_chunk += ("\n" if current_chunk else "") + line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def process_rag_chunking(manifest_path: str = MANIFEST_FILE, output_path: str = OUTPUT_FILE) -> None:
    base_dir = Path(__file__).parent.resolve()
    manifest_file = base_dir / manifest_path

    if not manifest_file.exists():
        print(f"[ERROR] No se encontró el manifiesto: {manifest_path}")
        return

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    total_chunks = 0
    total_files = 0
    out_file_path = base_dir / output_path

    print("=== INICIANDO PROCESO DE CHUNKING CONSCIENTE DE MARKDOWN ===\n")

    with open(out_file_path, "w", encoding="utf-8") as f_out:
        for file_info in manifest_data.get("files", []):
            rel_path = file_info.get("file_path")
            full_path = base_dir / rel_path

            if not full_path.exists():
                continue

            total_files += 1

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f_in:
                    content = f_in.read()

                sections = split_markdown_by_headers(content)
                file_chunk_index = 0

                for sec in sections:
                    header = sec["header"]
                    sec_content = sec["content"]
                    sub_chunks = recursive_chunk_text(sec_content)

                    for sub_chunk in sub_chunks:
                        file_chunk_index += 1
                        total_chunks += 1

                        chunk_data = {
                            "chunk_id": f"{rel_path}#chunk-{file_chunk_index}",
                            "file_path": rel_path,
                            "folder": file_info.get("folder"),
                            "section_header": header,
                            "content": sub_chunk,
                            "char_count": len(sub_chunk),
                            "estimated_tokens": len(sub_chunk) // 4,
                        }

                        f_out.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")

            except Exception as e:
                print(f"[ERROR] Error procesando {rel_path}: {e}")

    print("\n=== RESUMEN DE CHUNKING ===")
    print(f"Archivos procesados:    {total_files}")
    print(f"Total chunks generados: {total_chunks}")
    print(f"Archivo de salida:      {output_path}")


if __name__ == "__main__":
    process_rag_chunking()