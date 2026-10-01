import re

def clean_repetitive_loops(text: str, min_repeats: int = 2) -> str:
    """
    Detecta y elimina bucles de repetición consecutiva de oraciones o bloques de texto
    generados por alucinaciones o errores de salida de un LLM.

    :param text: Contenido completo del archivo en formato string.
    :param min_repeats: Ocurrencias adicionales consecutivas para considerar un bucle.
    :return: Texto limpio conservando la primera aparición de la frase.
    """
    # Expresión regular que captura una frase/oración que finaliza en signo de puntuación
    # o salto de línea, seguida de 2 o más repeticiones identicas consecutivas.
    pattern = re.compile(
        r'(\b.+?[.?!;\n])(?:\s*\1){' + str(min_repeats) + r',}',
        flags=re.DOTALL
    )

    # Reemplaza el bloque repetido dejando únicamente la primera captura (\1)
    cleaned_text = pattern.sub(r'\1', text)
    return cleaned_text


if __name__ == "__main__":
    # Prueba de concepto con una muestra del patrón detectado
    sample_text = (
        "3. Actualizar la IP autorizada en Netelip\n\n"
        "Sería el último paso para que la llamada por fin enlace. "
        "Sería el último paso para que la llamada por fin enlace. "
        "Sería el último paso para que la llamada por fin enlace."
    )
    
    result = clean_repetitive_loops(sample_text)
    print("--- TEXTO PROCESADO ---")
    print(result)