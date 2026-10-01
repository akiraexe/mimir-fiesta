import os
from pathlib import Path
from cleaner_core import clean_repetitive_loops

# Directorios autorizados para escaneo
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


def process_batch(create_backup: bool = True) -> None:
    base_dir = Path(__file__).parent.resolve()
    total_files = 0
    modified_files = 0
    total_bytes_saved = 0

    print("=== INICIANDO LIMPIEZA MASIVA DE ARCHIVOS ===\n")

    for folder_name in TARGET_FOLDERS:
        folder_path = base_dir / folder_name
        if not folder_path.exists():
            print(f"[OMITIDO] No existe el directorio: {folder_name}")
            continue

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = Path(root) / file_name

                # Ignorar archivos que no sean .md o .txt y respaldos previos
                if file_path.suffix.lower() not in ALLOWED_EXTENSIONS or file_path.name.endswith(".bak"):
                    continue

                total_files += 1

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        original_text = f.read()

                    cleaned_text = clean_repetitive_loops(original_text)

                    # Si hubo cambios sintácticos, procedemos a actualizar
                    if cleaned_text != original_text:
                        if create_backup:
                            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                            with open(backup_path, "w", encoding="utf-8") as f_bak:
                                f_bak.write(original_text)

                        with open(file_path, "w", encoding="utf-8") as f_out:
                            f_out.write(cleaned_text)

                        bytes_saved = len(original_text.encode("utf-8")) - len(cleaned_text.encode("utf-8"))
                        total_bytes_saved += bytes_saved
                        modified_files += 1

                        print(f"[LIMPIADO] {file_path.relative_to(base_dir)} (-{bytes_saved} bytes)")

                except Exception as e:
                    print(f"[ERROR] No se pudo procesar {file_path.relative_to(base_dir)}: {e}")

    print("\n=== RESUMEN DE PROCESAMIENTO ===")
    print(f"Archivos escaneados:   {total_files}")
    print(f"Archivos modificados:  {modified_files}")
    print(f"Reducción total:       {total_bytes_saved / 1024:.2f} KB")


if __name__ == "__main__":
    process_batch(create_backup=True)