import os
import json
import re
from pathlib import Path


def repair_flagged_files(manifest_path: str = "rag_manifest.json") -> None:
    base_dir = Path(__file__).parent.resolve()
    manifest_file = base_dir / manifest_path

    if not manifest_file.exists():
        print(f"[ERROR] No se encontró el manifiesto: {manifest_path}")
        return

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    repaired_count = 0

    for file_info in data.get("files", []):
        if file_info.get("status") == "WARNING":
            rel_path = file_info.get("file_path")
            full_path = base_dir / rel_path
            warnings = file_info.get("warnings", [])

            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f_in:
                    content = f_in.read()

                modified = False

                # 1. Reparar bloques de código sin cerrar añadiendo triple backtick al final
                if "Bloque de código Markdown sin cerrar (```)" in warnings:
                    if content.count("```") % 2 != 0:
                        content = content.rstrip() + "\n```\n"
                        modified = True

                # 2. Reparar remanente de bucle repetitivo con un regex de coincidencia amplia
                if "Posible remanente de bucle repetitivo detectado" in warnings:
                    pattern = re.compile(r'(\b.+?[.?!;\n])(?:\s*\1)+', flags=re.DOTALL)
                    cleaned_content = pattern.sub(r'\1', content)
                    if cleaned_content != content:
                        content = cleaned_content
                        modified = True

                if modified:
                    with open(full_path, "w", encoding="utf-8") as f_out:
                        f_out.write(content)
                    repaired_count += 1
                    print(f"[REPARADO] {rel_path}")

            except Exception as e:
                print(f"[ERROR] No se pudo reparar {rel_path}: {e}")

    print(f"\n=== PROCESO DE REPARACIÓN CONCLUIDO ===")
    print(f"Archivos modificados: {repaired_count}")


if __name__ == "__main__":
    repair_flagged_files()