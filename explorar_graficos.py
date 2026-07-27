# %% [markdown]
# # Explorar gráficos (Paso 4) dentro de VS Code
#
# Este archivo usa "celdas" (los separadores `# %%`) del Jupyter Interactive
# Window de VS Code. Cada celda se ejecuta con el botón "Run Cell" que
# aparece encima de ella (o Ctrl+Enter con el cursor dentro), y el resultado
# —incluidos los gráficos de Plotly— se muestra en un panel a la derecha,
# sin salir del editor ni abrir el navegador.
#
# Requisitos: extensión "Jupyter" instalada en VS Code, y el paquete
# ipykernel en tu entorno virtual (pip install ipykernel).

# %%
from lib.carga_mysql import obtener_conexion, CONFIG_BD
from lib.visualizacion import (
    consultar_partidas_completas,
    grafico_evolucion_temporal,
    grafico_comparativa_mapas,
    grafico_distribucion_kd,
)

conexion = obtener_conexion(CONFIG_BD)
df = consultar_partidas_completas(conexion)
conexion.close()
df.head()

# %%
# Gráfico 1 — evolución temporal
fig1 = grafico_evolucion_temporal(df, "graficos/evolucion_partidas.html")
fig1.show()

# %%
# Gráfico 2 — comparativa entre mapas
fig2 = grafico_comparativa_mapas(df, "graficos/comparativa_mapas.html")
fig2.show()

# %%
# Gráfico 3 — distribución del kd_ratio por modo
fig3 = grafico_distribucion_kd(df, "graficos/distribucion_kd.html")
fig3.show()
