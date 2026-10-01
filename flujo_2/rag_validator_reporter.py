import os
import json
import re
from pathlib import Path

TARGET_FOLDERS = [
    "01_NetNAVI_Infraestructura_Sistemas",
    "02_NetNAVI_Desarrollo_Automatizacion",
    "03_Fiscal_Administrativo_CDMX",
    "04_Proyectos_Creativos_y_Narrativa",
    "05_Filosofia_y_Cuidado_Personal",
    "06_Logistica_y_Gestion_Familiar",
    "07_Cultura_General_y_Consumo",
    "99_Archivo_Muerto_No_Clasificado",
]

ALLOWED_EXTENSIONS = {".md", ".txt"}


def validate_markdown_integrity(content: str) -> list:
    """
    Realiza pruebas de sintaxis Markdown y detecta remanentes de bucles o bloques corruptos.
    """
    warnings = []

    # 1. Verificar delimitadores de código sin cerrar (```)
    if content.count("```") % 2 != 0:
        warnings.append("Bloque de código Markdown sin cerrar (```)")

    # 2. Verificar posible persistencia de bucles no capturados
    if re.search(r'(\b.+?[.?!;\n])(?:\s*\1){2,}', content, re.DOTALL):
        warnings.append("Posible remanente de bucle repetitivo detectado")

    # 3. Archivo vacío tras la limpieza
    if not content.strip():
        warnings.append("El archivo está vacío")

    return warnings


def generate_rag_report_and_clean(cleanup_bak: bool = False, report_file: str = "rag_manifest.json") -> None:
    base_dir = Path(__file__).parent.resolve()
    manifest = []
    valid_files = 0
    warning_files = 0
    bak_deleted = 0

    print("=== INICIANDO VALIDACIÓN Y GENERACIÓN DE MANIFIESTO RAG ===\n")

    for folder_name in TARGET_FOLDERS:
        folder_path = base_dir / folder_name
        if not folder_path.exists():
            continue

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = Path(root) / file_name

                # Purgar respaldos si se activa la bandera
                if file_path.suffix == ".bak":
                    if cleanup_bak:
                        file_path.unlink()
                        bak_deleted += 1
                    continue

                if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    warnings = validate_markdown_integrity(content)
                    char_count = len(content)
                    # Estimación promedio: 1 token ≈ 4 caracteres en modelos estándar
                    est_tokens = char_count // 4

                    file_entry = {
                        "file_path": str(file_path.relative_to(base_dir)),
                        "folder": folder_name,
                        "extension": file_path.suffix,
                        "character_count": char_count,
                        "estimated_tokens": est_tokens,
                        "status": "READY" if not warnings else "WARNING",
                        "warnings": warnings,
                    }

                    manifest.append(file_entry)

                    if warnings:
                        warning_files += 1
                        print(f"[ADVERTENCIA] {file_entry['file_path']}: {', '.join(warnings)}")
                    else:
                        valid_files += 1

                except Exception as e:
                    print(f"[ERROR] No se pudo validar {file_path.relative_to(base_dir)}: {e}")

    # Guardar manifiesto JSON estructurado para el pipeline RAG
    report_path = base_dir / report_file
    report_data = {
        "summary": {
            "total_files_processed": len(manifest),
            "ready_files": valid_files,
            "warning_files": warning_files,
            "bak_files_purged": bak_deleted,
        },
        "files": manifest,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print("\n=== RESUMEN DE VALIDACIÓN RAG ===")
    print(f"Archivos inspeccionados:   {len(manifest)}")
    print(f"Listos para ingesta (OK):  {valid_files}")
    print(f"Con advertencias:          {warning_files}")
    if cleanup_bak:
        print(f"Archivos .bak eliminados:  {bak_deleted}")
    print(f"Manifiesto guardado en:    {report_path.name}")


if __name__ == "__main__":
    # Cambiar cleanup_bak=True cuando desees eliminar los archivos .bak automáticamente
    generate_rag_report_and_clean(cleanup_bak=False)