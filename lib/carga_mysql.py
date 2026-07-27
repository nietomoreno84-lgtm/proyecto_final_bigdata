"""
Paso 3 — Almacenamiento relacional (MySQL)
Proyecto de final de curso — Videojuego (seed42)

El alumno diseña un esquema mínimo (2 tablas), carga los datos limpios
desde Python con mysql-connector y valida con consultas SQL que los datos
son correctos. Aquí se almacena la versión limpia y estructurada
(salida del Paso 2).
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error

from lib.resumen import registrar


# Credenciales de conexión. Si cambias de máquina o de contraseña,
# solo hay que tocar este diccionario.
CONFIG_BD = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "videojuego_seed42",
}


# ---------------------------------------------------------------------------
# 1. Conexión
# ---------------------------------------------------------------------------

def obtener_conexion(config: dict = CONFIG_BD, incluir_bd: bool = True):
    """
    Abre una conexión a MySQL. Si incluir_bd=False, se conecta al servidor
    sin seleccionar ninguna base de datos (útil para crearla si no existe).
    """
    parametros = config.copy()
    if not incluir_bd:
        parametros.pop("database", None)
    return mysql.connector.connect(**parametros)


def crear_base_datos_si_no_existe(config: dict = CONFIG_BD) -> None:
    """Crea la base de datos indicada en config['database'] si todavía no existe."""
    conexion = obtener_conexion(config, incluir_bd=False)
    cursor = conexion.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
    cursor.close()
    conexion.close()
    registrar("Paso 3", f"Base de datos '{config['database']}' lista.")


# ---------------------------------------------------------------------------
# 2. Esquema (2 tablas: jugadores y partidas)
# ---------------------------------------------------------------------------

SQL_CREAR_TABLA_JUGADORES = """
CREATE TABLE IF NOT EXISTS jugadores (
    id_jugador       VARCHAR(6)   PRIMARY KEY,
    nick             VARCHAR(100),
    region           VARCHAR(20),
    nivel            INT,
    rango            VARCHAR(20),
    fecha_registro   DATE,
    antiguedad_dias  INT
)
"""

SQL_CREAR_TABLA_PARTIDAS = """
CREATE TABLE IF NOT EXISTS partidas (
    id_partida         INT PRIMARY KEY,
    fecha              DATE,
    hora               VARCHAR(10),
    id_jugador         VARCHAR(6),
    mapa               VARCHAR(50),
    modo               VARCHAR(20),
    personajes_usados  VARCHAR(255),
    duracion_min       INT,
    kills              INT,
    muertes            INT,
    asistencias        INT,
    resultado          VARCHAR(20),
    puntos             INT,
    anio               INT,
    mes                INT,
    dia_semana         VARCHAR(20),
    kd_ratio           INT,
    num_personajes     INT,
    FOREIGN KEY (id_jugador) REFERENCES jugadores(id_jugador)
)
"""


def crear_tablas(conexion) -> None:
    """Crea 'jugadores' y 'partidas' si no existen. Primero jugadores,
    porque partidas tiene una clave foránea hacia ella."""
    cursor = conexion.cursor()
    cursor.execute(SQL_CREAR_TABLA_JUGADORES)
    cursor.execute(SQL_CREAR_TABLA_PARTIDAS)
    conexion.commit()
    cursor.close()
    registrar("Paso 3", "Tablas 'jugadores' y 'partidas' listas.")


# ---------------------------------------------------------------------------
# 3. Carga de datos desde los DataFrames limpios
# ---------------------------------------------------------------------------

def _filas_para_sql(df: pd.DataFrame) -> list[tuple]:
    """
    Convierte un DataFrame en una lista de tuplas apta para executemany:
    - los NaN/NaT/<NA> de Pandas se convierten en None (NULL en SQL)
    - las fechas datetime64 se convierten a texto 'AAAA-MM-DD'
    """
    df = df.copy()
    for columna in df.select_dtypes(include=["datetime64[ns]"]).columns:
        df[columna] = df[columna].dt.strftime("%Y-%m-%d")
    df = df.astype(object).where(pd.notnull(df), None)
    return list(df.itertuples(index=False, name=None))


def cargar_jugadores(conexion, df_jugadores: pd.DataFrame) -> None:
    """Inserta los jugadores en MySQL. Si un id_jugador ya existe, actualiza sus datos."""
    columnas = ["id_jugador", "nick", "region", "nivel", "rango", "fecha_registro", "antiguedad_dias"]
    filas = _filas_para_sql(df_jugadores[columnas])

    sql = f"""
        INSERT INTO jugadores ({", ".join(columnas)})
        VALUES ({", ".join(["%s"] * len(columnas))})
        ON DUPLICATE KEY UPDATE
            nick = VALUES(nick),
            region = VALUES(region),
            nivel = VALUES(nivel),
            rango = VALUES(rango),
            fecha_registro = VALUES(fecha_registro),
            antiguedad_dias = VALUES(antiguedad_dias)
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, filas)
    conexion.commit()
    registrar("Paso 3", f"Jugadores cargados/actualizados: {cursor.rowcount}")
    cursor.close()


def cargar_partidas(conexion, df_partidas: pd.DataFrame) -> None:
    """Inserta las partidas en MySQL. Si un id_partida ya existe, lo actualiza."""
    columnas = [
        "id_partida", "fecha", "hora", "id_jugador", "mapa", "modo", "personajes_usados",
        "duracion_min", "kills", "muertes", "asistencias", "resultado", "puntos",
        "anio", "mes", "dia_semana", "kd_ratio", "num_personajes",
    ]
    filas = _filas_para_sql(df_partidas[columnas])

    sql = f"""
        INSERT INTO partidas ({", ".join(columnas)})
        VALUES ({", ".join(["%s"] * len(columnas))})
        ON DUPLICATE KEY UPDATE
            fecha = VALUES(fecha),
            resultado = VALUES(resultado),
            puntos = VALUES(puntos),
            kills = VALUES(kills),
            kd_ratio = VALUES(kd_ratio)
    """
    cursor = conexion.cursor()
    cursor.executemany(sql, filas)
    conexion.commit()
    registrar("Paso 3", f"Partidas cargadas/actualizadas: {cursor.rowcount}")
    cursor.close()


# ---------------------------------------------------------------------------
# 4. Validación con consultas SQL propias
# ---------------------------------------------------------------------------

def validar_carga(conexion) -> None:
    """
    Ejecuta consultas de sanidad tras la carga:
    - recuento de filas en cada tabla
    - comprobación de que no hay id_jugador "huérfanos" en partidas
      (partidas cuyo jugador no existe en la tabla jugadores)
    """
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM jugadores")
    total_jugadores = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM partidas")
    total_partidas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM partidas p
        LEFT JOIN jugadores j ON p.id_jugador = j.id_jugador
        WHERE j.id_jugador IS NULL
    """)
    huerfanas = cursor.fetchone()[0]

    cursor.close()
    registrar("Paso 3", f"Validación -> jugadores: {total_jugadores} | partidas: {total_partidas} | "
              f"partidas sin jugador asociado: {huerfanas}")


# ---------------------------------------------------------------------------
# 5. Tabla de resumen / agregación
# ---------------------------------------------------------------------------

SQL_CREAR_TABLA_RESUMEN = """
CREATE TABLE IF NOT EXISTS resumen_mapa (
    mapa                VARCHAR(50) PRIMARY KEY,
    total_partidas      INT,
    media_puntos        FLOAT,
    media_kd_ratio      FLOAT,
    media_duracion_min  FLOAT
)
"""

SQL_POBLAR_TABLA_RESUMEN = """
REPLACE INTO resumen_mapa (mapa, total_partidas, media_puntos, media_kd_ratio, media_duracion_min)
SELECT
    mapa,
    COUNT(*)             AS total_partidas,
    AVG(puntos)          AS media_puntos,
    AVG(kd_ratio)        AS media_kd_ratio,
    AVG(duracion_min)    AS media_duracion_min
FROM partidas
GROUP BY mapa
"""


def crear_tabla_resumen(conexion) -> None:
    """Crea (si no existe) y puebla la tabla de resumen por mapa."""
    cursor = conexion.cursor()
    cursor.execute(SQL_CREAR_TABLA_RESUMEN)
    cursor.execute(SQL_POBLAR_TABLA_RESUMEN)
    conexion.commit()
    cursor.execute("SELECT COUNT(*) FROM resumen_mapa")
    total = cursor.fetchone()[0]
    cursor.close()
    registrar("Paso 3", f"Tabla 'resumen_mapa' generada con {total} mapas.")


# ---------------------------------------------------------------------------
# Pipeline principal del Paso 3
# ---------------------------------------------------------------------------

def cargar_datos_en_mysql(df_partidas: pd.DataFrame, df_jugadores: pd.DataFrame,
                          config: dict = CONFIG_BD) -> None:
    """
    Orquesta el Paso 3 completo: crea la base de datos y las tablas si hace
    falta, carga jugadores y partidas, valida la carga y genera la tabla resumen.
    """
    try:
        crear_base_datos_si_no_existe(config)
        conexion = obtener_conexion(config)
        crear_tablas(conexion)

        # jugadores primero: partidas tiene clave foránea hacia jugadores
        cargar_jugadores(conexion, df_jugadores)
        cargar_partidas(conexion, df_partidas)

        validar_carga(conexion)
        crear_tabla_resumen(conexion)

        conexion.close()
    except Error as error:
        registrar("Paso 3", f"Error de MySQL: {error}")
        raise
