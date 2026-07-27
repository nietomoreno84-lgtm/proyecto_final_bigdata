"""
enviar_resumen_n8n.py — Paso 6: envía el resumen diario a n8n por webhook

Ejecutar manualmente:
    python enviar_resumen_n8n.py

Para que se lance solo (sin intervención manual), prográmalo con el
Programador de tareas de Windows:
  1. Abre "Programador de tareas" (busca "Task Scheduler" en el menú inicio)
  2. Crear tarea básica -> nombre "Resumen diario videojuego"
  3. Desencadenador: Diariamente, a la hora que quieras
  4. Acción: Iniciar un programa
       Programa: la ruta a python.exe de tu entorno virtual
                 (algo así: C:\\curso_big_data\\proyecto_final\\.venv\\Scripts\\python.exe)
       Argumentos: enviar_resumen_n8n.py
       Iniciar en: C:\\curso_big_data\\proyecto_final   (la carpeta raíz del proyecto)
"""

from lib.notificar_n8n import enviar_reporte
from lib.resumen import mostrar_resumen

if __name__ == "__main__":
    enviar_reporte()
    mostrar_resumen()
