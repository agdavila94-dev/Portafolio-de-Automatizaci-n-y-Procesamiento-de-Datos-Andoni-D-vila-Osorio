from pathlib import Path
import shutil

def organizar_descargas():
    # 1. DETECTAR LA RUTA DE DESCARGAS DE FORMA DINÁMICA
    # Path.home() encuentra automáticamente "C:\Users\tu_usuario"
    ruta_descargas = Path.home() / "Downloads"
    
    print(f"🔍 Escaneando la carpeta: {ruta_descargas}\n")

    # 2. RECORRER TODOS LOS ELEMENTOS DENTRO DE DESCARGAS
    for elemento in ruta_descargas.iterdir():
        
        # REGLA DE SEGURIDAD: Si es una carpeta, la ignoramos para no mover carpetas dentro de carpetas
        if elemento.is_dir():
            continue

        # 3. EXTRAER LA EXTENSIÓN Y PREPARAR EL NOMBRE (Instrucción 1 y 2)
        # .suffix extrae el punto y la extensión (ej: ".pdf"). Lo pasamos a minúsculas.
        extension = elemento.suffix.lower().replace(".", "")

        # Si el archivo no tiene extensión (raro, pero pasa), lo mandamos a una carpeta llamada 'OTROS'
        if not extension:
            extension = "OTROS"

        # El nombre de la carpeta será la extensión en mayúsculas (ej: "PDF", "XLSX", "PNG")
        nombre_carpeta = extension.upper()
        carpeta_destino = ruta_descargas / nombre_carpeta

        # 4. CREAR CARPETA SI NO EXISTE (Instrucción 3)
        # exist_ok=True hace que si la carpeta ya existe, Python no lance un error y continúe
        carpeta_destino.mkdir(exist_ok=True)

        # 5. GESTIÓN DE COLISIONES (¿Qué pasa si el archivo ya existe en el destino?)
        ruta_final_archivo = carpeta_destino / elemento.name
        
        contador = 1
        # Mientras exista un archivo con el mismo nombre en la carpeta de destino...
        while ruta_final_archivo.exists():
            # Renombramos el archivo temporalmente agregando un número (ej: reporte_1.pdf)
            nombre_sin_extension = elemento.stem
            ruta_final_archivo = carpeta_destino / f"{nombre_sin_extension}_{contador}.{extension}"
            contador += 1

        # 6. MOVER EL ARCHIVO A SU DESTINO FINAL
        try:
            shutil.move(str(elemento), str(ruta_final_archivo))
            print(f"📦 Movido: {elemento.name} ➔ {nombre_carpeta}/")
        except Exception as e:
            print(f"⚠️ No se pudo mover {elemento.name}. Error: {e}")

    print("\n✨ ¡Organización diaria completada con éxito!")

# Esto le dice a Python que ejecute la función al darle al botón de Play
if __name__ == "__main__":
    organizar_descargas()