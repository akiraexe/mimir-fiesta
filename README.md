# 🚀 Orquestador de ETL en Python

Este repositorio contiene un conjunto de herramientas y scripts organizados por flujos de ejecución secuenciales e independientes. Cada directorio representa una etapa del proceso que se ejecuta y finaliza antes de dar paso a la siguiente.

---

## 📂 Estructura del Proyecto

*   **`flujo_1/`**:  Extrae la información del JSON e inserta en la base de datos. Desde la fase 3 genera los archivos en txt.
* **`flujo_2/`**: Se ejecuta para eliminar caracteres duplicados y los generados por las alucinaciones.

---

## ⚙️ Descripción de los Flujos

### 🔹 Flujo 1: Ingesta y Limpieza
Este bloque se encarga de procesar los datos de entrada.
*   **Requisitos:** Requiere que el archivo MyActivity.json esté en /datos_crudos, carpeta ubicada en la raíz del entorno de ejecución.
*   **Ejecución:**
    ```bash
    python flujo_1/fase1_etl_sqlite.py
    ```
*   **Resultado:** Escribe en la base de datos memoria_rag.db en /base_datos, carpeta ubicada en la raíz del entorno de ejecución.

Este bloque se encarga de categorizar los datos volcados en la base de datos.
*   **Requisitos:** Que la base de datos memoria_rag.db en /base_datos tenga la información previa volcada del paso anterior.
*   **Ejecución:**
    ```bash
    python flujo_1/fase2_inferencia_gemini31_v1.py
    ```
*   **Resultado:** El script actualiza en memoria_rag.db insertando la etiqueta de la conversación de acuerdo a los criterios.

Este bloque se encarga de volcar los archivos con el Frontmatter.
*   **Requisitos:** Que la base de datos memoria_rag.db en /base_datos tenga la información actualizada del paso anterior.
*   **Ejecución:**
    ```bash
    python flujo_1/fase3_markdown_export.py
    ```
*   **Resultado:** El script crea las carpetas de categoría si no existen, luego escribe los archivos en su destino correspondiente.

### 🔹 Flujo 2: Procesamiento y Salida
Este bloque lee los archivos Frontmatter generados por el Flujo 1 para realizar la limpieza.
*   **Ejecución:**
    ```bash
    python flujo_2/batch_cleaner.py
    ```
*   **Resultado:** El script crea un backup, luego escribe los archivos limpiados en su destino correspondiente.

Este bloque lee los archivos Frontmatter generados por el Flujo 1 para realizar la limpieza.
*   **Ejecución:**
    ```bash
    python flujo_2/batch_cleaner.py
    ```
*   **Resultado:** El script crea un backup, luego escribe los archivos limpiados en su destino correspondiente.

Este bloque lee los archivos generados por el script previo para evaluar problemas o truncados en el Frontmatter.
*   **Ejecución:**
    ```bash
    python flujo_2/rag_validator_reporter.py
    ```
*   **Resultado:** El script escribe el volcado en un archivo rag_manifest.json previo a la creacion del chunk.

Este bloque lee el archivo volcado por el script listo para ser leído y procesado.
*   **Ejecución:**
    ```bash
    python flujo_2/fix_warnings.py
    ```
*   **Resultado:** Usa el archivo rag_manifest.json previo a la creacion del chunk para aplicar las correcciones.

Este bloque lee el archivo rag_manifest.json listo para generar el JSON.
*   **Ejecución:**
    ```bash
    python flujo_2/rag_chunker.py
    ```
*   **Resultado:** Usa el archivo rag_manifest.json previo y hace el volcado en el archivo rag_chunks.jsonl listo para la ingesta.

### 🔹 Flujo 3: Generación e ingesta en Dify
Se modifica el flujo anterior, únicamente llegando a la etapa de limpieza del Paso 1 en el Flujo 2. Rehidratar fechas.
*   **Ejecución:**
    ```bash
    python flujo_1/fase3.5_rehidratar_fechas.py
    ```
*   **Resultado:** Usa los archivos volcados omitiendo o borrando manualmente los .bak actualizando las fechas de la base de datos.

Se modifica el bloque rag_chunker.py del último paso de la Fase 2, para generar el mismo JSONL.
*   **Ejecución:**
    ```bash
    python flujo_1/fase3.5_rag_chunker_v2.py
    ```
*   **Resultado:** Genera un archivo JSONL nuevamente en la raíz de donde están corriendo estos bloques.

Se crea un bloque para dividir el chunk debido a la compatibilidad de carga en Dify.
*   **Ejecución:**
    ```bash
    python flujo_1/fase3.5_split_dify_fast.py
    ```
*   **Resultado:** Usa el archivo JSONL generado para dividirlo en archivos de texto plano para ser vectorizados de forma eficiente.
---

## 🛠️ Requisitos del Sistema

Para ejecutar estos scripts de manera local, asegúrate de contar con:
*   **Python 3.10+**

