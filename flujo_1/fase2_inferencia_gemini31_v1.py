import sqlite3
import json
import time
import requests

# ==========================================
# CONFIGURACIÓN COMPROBADA - MODO TORTUGA
# ==========================================
GEMINI_API_KEY = "API_ANONIMIZADA"
DB_PATH = r".\base_datos\memoria_rag.db"

# CAMBIO DE MODELO: Apuntamos a la versión estable para balancear la cuota
URL_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"

PROMPT_SISTEMA = """You are an expert data router. Your only task is to analyze the provided chat log, including any source code snippets, and classify it into one of the allowed categories, generating a short title and a 2-line maximum summary.

ALLOWED CATEGORIES:
1. 01_NetNAVI_Infraestructura_Sistemas
2. 02_NetNAVI_Desarrollo_Automatizacion
3. 03_Fiscal_Administrativo_CDMX
4. 04_Proyectos_Creativos_y_Narrativa
5. 05_Filosofia_y_Cuidado_Personal
6. 06_Logistica_y_Gestion_Familiar
7. 07_Cultura_General_y_Consumo
8. 99_Archivo_Muerto_No_Clasificado

STRICT RULES:
- Respond ONLY with a valid JSON object containing exactly these keys: "categoria", "titulo", "resumen".
- Do not add markdown blocks like ```json or any conversational text.
"""

def limpiar_json_llm(respuesta_texto):
    try:
        inicio = respuesta_texto.find('{')
        fin = respuesta_texto.rfind('}')
        if inicio != -1 and fin != -1:
            bloque_json = respuesta_texto[inicio:fin+1]
            return json.loads(bloque_json)
        return None
    except json.JSONDecodeError:
        return None

def procesar_pendientes():
    print("[*] Iniciando ETL Fase 2: Modo Tortuga Constante (Gemini 3.1 Flash Lite)...")
    
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    cursor.execute("SELECT id, texto_limpio FROM conversaciones_staging WHERE estado = 'pendiente'")
    registros = cursor.fetchall()
    total_pendientes = len(registros)

    if total_pendientes == 0:
        print("[+] Base de datos al día.")
        conexion.close()
        return

    print(f"[*] Despachando {total_pendientes} registros con control estricto de TPM...")
    procesados = 0
    errores = 0

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    for registro in registros:
        id_registro, texto_conversacion = registro
        
        cuerpo_mensaje = (
            f"{PROMPT_SISTEMA}\n\n"
            f"TEXT TO ANALYZE:\n"
            f"--- START OF LOG ---\n{texto_conversacion}\n--- END OF LOG ---"
        )
        
        # =====================================================================
        # AQUÍ VA EL NUEVO PAYLOAD CON LA CONFIGURACIÓN NATIVA DE SCHEMAS DE GEMINI
        # =====================================================================
        payload = {
            "contents": [{
                "parts": [{"text": cuerpo_mensaje}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "categoria": {"type": "STRING"},
                        "titulo": {"type": "STRING"},
                        "resumen": {"type": "STRING"}
                    },
                    "required": ["categoria", "titulo", "resumen"]
                }
            }
        }
        # =====================================================================
        
        intentos = 0
        max_intentos = 5
        tiempo_espera = 6  # Respiro inicial más alto para enfriar el TPM
        exito_registro = False

        while intentos < max_intentos and not exito_registro:
            try:
                response = requests.post(URL_API, json=payload, headers=headers)
                
                if response.status_code == 200:
                    respuesta_json = response.json()
                    respuesta_texto = respuesta_json['candidates'][0]['content']['parts'][0]['text']
                    datos_json = limpiar_json_llm(respuesta_texto)

                    if datos_json and all(k in datos_json for k in ("categoria", "titulo", "resumen")):
                        cursor.execute('''
                            UPDATE conversaciones_staging 
                            SET llm_categoria = ?, llm_titulo = ?, llm_resumen = ?, estado = 'procesado'
                            WHERE id = ?
                        ''', (datos_json['categoria'], datos_json['titulo'], datos_json['resumen'], id_registro))
                        print(f" -> ID {id_registro}... ✓ [PROCESADO]")
                        procesados += 1
                    else:
                        cursor.execute("UPDATE conversaciones_staging SET estado = 'error_llm' WHERE id = ?", (id_registro,))
                        print(f" -> ID {id_registro}... ✗ [JSON Inválido]")
                        errores += 1
                    
                    exito_registro = True
                    
                    # PASO DE TORTUGA: Si la conversación es muy larga, aumentamos dinámicamente la pausa
                    # para proteger el TPM de la siguiente vuelta.
                    pausa_dinamica = 5.0 if len(texto_conversacion) < 5000 else 12.0
                    time.sleep(pausa_dinamica)

                elif response.status_code in (429, 503):
                    intentos += 1
                    print(f"\n[!] Límite de Tokens/Peticiones alcanzado. Esperando {tiempo_espera}s para enfriar API...", flush=True)
                    time.sleep(tiempo_espera)
                    tiempo_espera *= 2  

                else:
                    cursor.execute("UPDATE conversaciones_staging SET estado = 'error_llm' WHERE id = ?", (id_registro,))
                    print(f" -> ID {id_registro}... ✗ [ERROR API {response.status_code}]")
                    errores += 1
                    exito_registro = True

            except Exception as e:
                cursor.execute("UPDATE conversaciones_staging SET estado = 'error_llm' WHERE id = ?", (id_registro,))
                print(f" -> ID {id_registro}... ✗ [FALLO: {str(e)}]")
                errores += 1
                exito_registro = True

        if not exito_registro:
            cursor.execute("UPDATE conversaciones_staging SET estado = 'error_llm' WHERE id = ?", (id_registro,))
            print(f" -> ID {id_registro}... ✗ [SALTADO POR RATELIMIT]")
            errores += 1

        conexion.commit()

    conexion.close()
    print(f"\n[+] Ráfaga concluida. Exitosos: {procesados} | Errores: {errores}")

if __name__ == "__main__":
    procesar_pendientes()