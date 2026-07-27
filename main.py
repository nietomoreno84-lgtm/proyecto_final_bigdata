"""
main.py — Punto de entrada del proyecto de final de curso (Videojuego, seed42)

Ejecuta el Paso 1 (Excel + diccionario de datos), el Paso 2 (limpieza con
Pandas/NumPy), el Paso 3 (carga en MySQL) y el Paso 4 (gráficos Plotly
consultando MySQL), y genera los CSV limpios en data/.

Ejecutar desde la raíz del proyecto:
    python main.py
"""

from lib.cargar_datos import cargar_datos, generar_excel_bruto
from lib.limpieza_datos import limpiar_partidas, limpiar_jugadores, estadisticas_descriptivas
from lib.carga_mysql import cargar_datos_en_mysql, CONFIG_BD
from lib.visualizacion import generar_visualizaciones
from lib.notificar_n8n import enviar_reporte
from lib.resumen import registrar, mostrar_resumen

# CSV en bruto (Paso 1)
RUTA_PARTIDAS = "data/videojuego_seed42.csv"
RUTA_JUGADORES = "data/videojuego_seed42_jugadores.csv"

# Salidas
RUTA_EXCEL_BRUTO = "data/videojuego_datos_brutos.xlsx"
RUTA_PARTIDAS_LIMPIO = "data/partidas_limpio.csv"
RUTA_JUGADORES_LIMPIO = "data/jugadores_limpio.csv"
CARPETA_GRAFICOS = "graficos"

# Columnas numéricas sobre las que calcular estadísticas descriptivas
COLUMNAS_NUMERICAS = ["duracion_min", "kills", "muertes", "asistencias", "puntos", "kd_ratio"]


def main():
    # --- Paso 1: leer los CSV en bruto y documentar/exportar a Excel ---
    df_partidas, df_jugadores = cargar_datos(RUTA_PARTIDAS, RUTA_JUGADORES)
    generar_excel_bruto(df_partidas, df_jugadores, RUTA_EXCEL_BRUTO)

    # --- Paso 2: limpieza y transformación con Pandas/NumPy ---
    df_partidas_limpio = limpiar_partidas(df_partidas)
    df_jugadores_limpio = limpiar_jugadores(df_jugadores)

    df_partidas_limpio.to_csv(RUTA_PARTIDAS_LIMPIO, index=False)
    df_jugadores_limpio.to_csv(RUTA_JUGADORES_LIMPIO, index=False)
    registrar("Paso 2", f"CSV limpios generados: {RUTA_PARTIDAS_LIMPIO}, {RUTA_JUGADORES_LIMPIO}")

    print("\nEstadísticas descriptivas — partidas:")
    print(estadisticas_descriptivas(df_partidas_limpio, COLUMNAS_NUMERICAS))

    # --- Paso 3: esquema, carga y validación en MySQL ---
    print("\nCargando datos en MySQL...")
    cargar_datos_en_mysql(df_partidas_limpio, df_jugadores_limpio, CONFIG_BD)

    # --- Paso 4: gráficos interactivos con Plotly, consultando MySQL ---
    print("\nGenerando gráficos...")
    generar_visualizaciones(CONFIG_BD, CARPETA_GRAFICOS)

    # --- Paso 5: no lo ejecuta este script, se anota en el resumen ---
    registrar("Paso 5", "Dashboard Power BI: dashboard_videojuego_seed42.pbix "
              "(se edita a mano en Power BI Desktop, no lo genera este script)")

    # --- Paso 6: consulta MySQL y envía el resumen a n8n (que lo reenvía a Telegram) ---
    print("\nEnviando resumen a n8n...")
    enviar_reporte(CONFIG_BD)

    # --- Resumen final de todo lo realizado en esta ejecución ---
    mostrar_resumen()


if __name__ == "__main__":
    main()
