import streamlit as st
import pandas as pd
import io
import re
import os
from google.cloud import vision
import cv2
import numpy as np

# 1. CONFIGURACIÓN DE SEGURIDAD (Google Cloud)
# Le decimos a Python dónde está el pasaporte de credenciales que descargaste
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

# 2. ALGORITMO DE ORDENAMIENTO (Tu Regla de Doble Llave)
def ordenar_nomenclatura(cota):
    partes = cota.split('-')
    if len(partes) != 2:
        return (99, cota)
    nomenclatura = partes[1]
    
    # Extraer letra pura y contar apóstrofos
    letra_match = re.search(r'[A-Z]', nomenclatura)
    letra = letra_match.group(0) if letra_match else ''
    cantidad_apostrofos = nomenclatura.count("'")
    
    return (cantidad_apostrofos, letra)

# 3. CONEXIÓN CON LOS OJOS DE GOOGLE VISION
def extraer_texto_google(contenido_imagen):
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=contenido_imagen)
        
        # Usamos DOCUMENT_TEXT_DETECTION porque es el más preciso para planos técnicos
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(response.error.message)
            
        return response.full_text_annotation.text
    except Exception as e:
        st.error(f"Error con la API de Google: {e}")
        return ""

# 4. FORMATEO MATEMÁTICO EN EXCEL (Regla Estricta de 13 Columnas)
def construir_matriz_excel(lista_cotas):
    filas_excel = []
    
    # Segmentamos la lista total de cotas en bloques de máximo 13 elementos
    for i in range(0, len(lista_cotas), 13):
        bloque = lista_cotas[i:i+13]
        
        # Desarmamos el bloque en dos listas: una de letras y otra de medidas
        letras_fila = [cota.split('-')[1].upper() for cota in bloque]
        medidas_fila = [cota.split('-')[0] for cota in bloque]
        
        # Si al último bloque le faltan datos para llegar a 13, rellenamos con vacíos
        while len(letras_fila) < 13:
            letras_fila.append("")
            medidas_fila.append("")
            
        # Añadimos la fila de letras y justo abajo la fila de medidas
        filas_excel.append(letras_fila)
        filas_excel.append(medidas_fila)
        
    # Creamos las cabeceras genéricas para las 13 columnas
    columnas = [f"Columna {j}" for j in range(1, 14)]
    df_resultado = pd.DataFrame(filas_excel, columns=columnas)
    return df_resultado

# 5. DISEÑO DE LA INTERFAZ WEB (Streamlit Frontend)
st.set_page_config(page_title="Extractor de Cotas CAD", page_icon="📐", layout="centered")

st.title("📐 Extractor Inteligente de Cotas")
st.write("Sube las capturas de AutoCAD de tu proyecto. El sistema extraerá, ordenará y consolidará las medidas en un único archivo Excel.")

# Componente para arrastrar y soltar múltiples imágenes a la vez
imagenes_cargadas = st.file_uploader(
    "Selecciona una o varias imágenes (PNG, JPG)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if imagenes_cargadas:
    st.info(f"📁 Imágenes en cola de espera: {len(imagenes_cargadas)}")
    
    # El botón que activa el procesamiento por lotes acumulativo
    if st.button("🚀 Iniciar Análisis Masivo"):
        cotas_totales_proyecto = []
        
        # Barra de progreso visual para el usuario
        progreso = st.progress(0)
        
        for index, archivo_imagen in enumerate(imagenes_cargadas):
            st.write(f"🔍 Analizando imagen {index + 1}: *{archivo_imagen.name}*...")
            
            # Leer los bytes originales
            bytes_imagen = archivo_imagen.read()
            
            # --- FASE B: OPENCV (Dilatación Morfológica y Binarización) ---
            nparr = np.frombuffer(bytes_imagen, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            img_ampliada = cv2.resize(img_cv, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_ampliada, cv2.COLOR_BGR2GRAY)
            
            # Binarización y Dilatación para engrosar apóstrofos
            _, binaria = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            kernel = np.ones((2,2), np.uint8)
            img_invertida = cv2.bitwise_not(binaria)
            img_dilatada = cv2.dilate(img_invertida, kernel, iterations=1)
            img_final = cv2.bitwise_not(img_dilatada)
            
            _, buffer = cv2.imencode('.png', img_final)
            bytes_mejorados = buffer.tobytes()
            # ----------------------------------------------
            
            # Llamar a Google Vision API con la imagen modificada
            texto_extraido = extraer_texto_google(bytes_mejorados)
            
            # --- INICIO DE ZONA DE DEBUG (FASE A) ---
            st.warning("🕵️‍♂️ MODO DIAGNÓSTICO: Texto crudo detectado por Google Vision")
            st.text(texto_extraido)
            # --- FIN DE ZONA DE DEBUG ---
            
            # --- FILTRO INTELIGENTE UNIFICADO ---
            # Busca: Formato normal tolerante a espacios OR formato vertical invertido (S9 / 9S)
            patron_cota = r'(\d+(?:\.\d+)?)\s*-\s*([A-Z01])\s*([\'"´`’]*)|([A-Z])(9|6)|(9|6)([A-Z])'
            
            matches = re.finditer(patron_cota, texto_extraido)
            
            for match in matches:
                # Si cumple con el formato normal (Grupos 1, 2, 3)
                if match.group(1):
                    numero = match.group(1)
                    letra = match.group(2)
                    simbolos = match.group(3) if match.group(3) else ""
                # Si cumple con el formato vertical "S9" (Grupos 4, 5)
                elif match.group(4):
                    letra = match.group(4)
                    numero = match.group(5)
                    simbolos = ""
                # Si cumple con el formato vertical "9S" (Grupos 6, 7)
                elif match.group(6):
                    numero = match.group(6)
                    letra = match.group(7)
                    simbolos = ""
                else:
                    continue

                # 1. Corrección del Síndrome del OCR (O y I)
                if letra == '0':
                    letra = 'O'
                elif letra == '1':
                    letra = 'I'
                    
                # 2. Limpieza de apóstrofos confusos
                simbolos_limpios = simbolos.replace('"', "''").replace('´', "'").replace('`', "'").replace('’', "'")
                
                # 3. Ensamblaje final de la cota matemática
                cota_limpia = f"{numero}-{letra}{simbolos_limpios}"
                cotas_totales_proyecto.append(cota_limpia)
            # ------------------------------------
                
            # Actualizar la barra de progreso paso a paso
            progreso.progress((index + 1) / len(imagenes_cargadas))
            
        # Al terminar el ciclo, eliminamos duplicados generales del proyecto
        cotas_unicas_proyecto = list(set(cotas_totales_proyecto))
        
        if cotas_unicas_proyecto:
            # Aplicamos el ordenamiento alfabético perfecto con la doble llave de control
            cotas_ordenadas = sorted(cotas_unicas_proyecto, key=ordenar_nomenclatura)
            
            # Construimos la cuadrícula estructurada de doble fila y 13 columnas como máximo
            df_final = construir_matriz_excel(cotas_ordenadas)
            
            st.success(f"✨ ¡Procesamiento terminado con éxito! Se detectaron {len(cotas_ordenadas)} cotas únicas.")
            
            # Mostramos una vista previa estructural de los datos en la pantalla
            st.write("📊 Vista previa del formato Excel:")
            st.dataframe(df_final)
            
            # Convertimos el DataFrame a bytes de Excel en la memoria RAM
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, header=False)
            datos_excel = output.getvalue()
            
            # Botón para descargar el reporte unificado
            st.download_button(
                label="📥 Descargar Reporte Excel Consolidado",
                data=datos_excel,
                file_name="reporte_cotas_consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ No se detectó ninguna cota que cumpla con la nomenclatura en las imágenes proporcionadas.")