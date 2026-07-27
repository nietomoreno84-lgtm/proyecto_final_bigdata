"""
Paso 2 — Limpieza y transformación (Python + Pandas + NumPy)
Proyecto de final de curso — Videojuego (seed42)

Funciones que limpian nulos, corrigen tipos, generan columnas derivadas
y producen estadísticas descriptivas básicas con NumPy. El resultado es
la versión limpia y estructurada de los datos.
"""

import re

import numpy as np
import pandas as pd

from lib.resumen import registrar


# ---------------------------------------------------------------------------
# Normalización del 'nick' (nombre+apellido concatenados, sin espacio)
# ---------------------------------------------------------------------------
# El nick no es un nombre "roto" al azar: es un nombre y un apellido pegados
# sin espacio (a veces en orden nombre+apellido, a veces apellido+nombre, y
# a veces solo la inicial de uno de los dos), tal como generan muchos
# sistemas de usuarios automáticos. Para separarlos de forma coherente hace
# falta un diccionario de nombres y apellidos españoles: sin él, el
# ordenador no puede saber dónde termina una palabra y empieza la otra.
#
# Este diccionario se ha construido a partir de las 200 filas reales de
# jugadores.csv, así que cubre el 100% de esos nicks. Si en el futuro
# aparecen jugadores nuevos con nombres que no estén aquí, la función no
# fallará: si no reconoce ninguna combinación, devuelve el nick tal cual
# (capitalizado), en vez de inventar una separación incorrecta.

NOMBRES = {
    "manuela", "dominga", "anton", "joan", "lilia", "elisabet", "marcos", "paula",
    "crescencia", "fermin", "herminia", "bibiana", "isidora", "paca", "salvador",
    "blas", "iban", "emiliano", "monica", "angel", "isabel", "trinidad", "angelita",
    "anunciacion", "prudencia", "calista", "amaya", "selena", "lupita", "eduardo",
    "leyre", "bernardo", "dionisia", "adrian", "borja", "calisto", "leon", "catalan",
    "genoveva", "benjamin", "gregorio", "brunilda", "telmo", "oscar", "angeles",
    "mariana", "baudelio", "bruno", "sancho", "cristina", "simon", "hilda", "alvaro",
    "brigida", "antonia", "paco", "rafael", "mate", "gracia", "manuelita", "lalo",
    "liliana", "jacinta", "arsenio", "febe", "griselda", "melisa", "angela",
    "nereida", "micaela", "feliciano", "ivan", "olga", "sabas", "felipa", "amaro",
    "tristan", "custodia", "debora", "rico", "dafne", "panfilo", "humberto",
    "caridad", "tito", "company", "estrella", "luciano", "adela", "ariadna",
    "aranzazu", "jafet", "eusebio", "isidoro", "yessica", "priscila", "joel",
    "teodora", "eutropio", "ricardo", "amarilis", "marc", "aureliano", "juan",
    "marisela", "heraclio", "jorge", "valentina", "esther", "urbano", "dolores",
    "hortensia", "rebeca", "domingo", "nydia", "ildefonso", "zequiel", "ezequiel",
    "vergara", "matilde", "jacobo", "aurelio", "cerda", "julia", "valeria",
    "genara", "fina", "fiona", "jimena", "fernando", "santiago", "pepita", "nilda",
}

# Nombres compuestos (con guion), tal como aparecen pegados en el nick
NOMBRES_COMPUESTOS = {
    "jose-ignacio", "juan-manuel", "juan-carlos", "juan-luis",
    "jose-manuel", "maria-jose", "maria-teresa",
}

APELLIDOS = {
    "amaya", "bonet", "gil", "flor", "casanovas", "nieto", "navarro", "bru",
    "palomar", "cebrian", "lobo", "lasa", "donoso", "sevilla", "morata", "grande",
    "moles", "clavero", "jodar", "pujol", "vergara", "bou", "canals", "roca",
    "plaza", "carbo", "lago", "camino", "pereira", "abascal", "hernando", "boada",
    "bayon", "talavera", "alamo", "galan", "mesa", "perea", "carrillo", "neira",
    "grau", "belda", "granados", "murillo", "torralba", "catalan", "herrero",
    "ramirez", "caballero", "pablo", "solera", "cabello", "nicolau", "ibarra",
    "sanabria", "espanol", "cabanas", "bueno", "flavio", "teruel", "barral",
    "abril", "torrecilla", "manu", "gelabert", "barrera", "valverde", "verdejo",
    "estevez", "gutierrez", "hoz", "bilbao", "marin", "molina", "agusti",
    "beltran", "lara", "bayona", "lopez", "urbano", "mari", "canizares", "campo",
    "lalo", "lujan", "novoa", "laguna", "iglesias", "roda", "juarez", "sala",
    "company", "peiro", "castell", "mendez", "pallares", "calderon", "elorza",
    "amat", "segui", "ferrando", "camps", "ojeda", "arregui", "habellan",
    "abellan", "prudencio", "rosado", "marques", "rivero", "davila", "saenz",
    "blazquez", "arteaga", "ferreras", "zurrutia", "adan", "rodriguez",
    "villaverde", "ayllon", "carrion", "canellas", "molins", "vargas", "cuenca",
    "sandoval", "lluch", "haro", "berenguer", "corominas", "ribera", "muro",
    "ricart", "rivera", "aller", "tapia", "gimenez", "navarrete", "dalmau",
    "amores", "cerda", "moran", "morillo", "finiesta", "aliaga", "olmo", "arjona",
    "huertas", "guardia", "lerma", "ramos", "guzman", "sosa",
}


def _separar_digitos(nick: str) -> tuple[str, str]:
    """Separa el nick en su parte alfabética (y guiones) y el sufijo numérico final."""
    coincidencia = re.match(r"^([a-zA-Z\-]+)(\d*)$", nick)
    return coincidencia.group(1).lower(), coincidencia.group(2)


def _dividir_nombre_compuesto(alpha: str) -> tuple[str, str] | None:
    """Busca un nombre compuesto conocido (con guion) dentro del nick y
    devuelve (nombre_compuesto, resto) si lo encuentra."""
    for compuesto in NOMBRES_COMPUESTOS:
        indice = alpha.find(compuesto)
        if indice != -1:
            resto = alpha[:indice] + alpha[indice + len(compuesto):]
            return compuesto, resto
    return None


# Algunas palabras son válidas como nombre Y como apellido a la vez
# (p.ej. 'Custodia' y 'Lara' son ambos nombres de pila también usados como
# apellido), así que el algoritmo genérico no puede adivinar solo con el
# diccionario cuál va primero. Para esos nicks concretos se fija a mano
# el orden correcto (nombre, apellido).
EXCEPCIONES_ORDEN = {
    "custodialara": ("lara", "custodia"),
}


def separar_nick(nick: str) -> str:
    """
    Convierte un nick pegado (p.ej. 'amayamanuela') en 'Nombre Apellido'
    (p.ej. 'Manuela Amaya'), usando los diccionarios NOMBRES/APELLIDOS.
    Cuando el nick original solo trae la mitad del dato (una inicial suelta,
    un nombre sin apellido, o un apellido sin nombre), la mitad que falta se
    rellena con una elección aleatoria del propio diccionario, para que el
    resultado final sea siempre un nombre y apellido completos.
    """
    alpha, _digitos = _separar_digitos(nick)

    if alpha in EXCEPCIONES_ORDEN:
        nombre, apellido = EXCEPCIONES_ORDEN[alpha]
        return f"{nombre.title()} {apellido.title()}"

    # nombre compuesto con guion (p.ej. 'juan-manuelalamo')
    if "-" in alpha:
        resultado = _dividir_nombre_compuesto(alpha)
        if resultado:
            nombre, resto = resultado
            nombre_fmt = " ".join(parte.title() for parte in nombre.split("-"))
            if resto:
                return f"{nombre_fmt} {resto.title()}"
            # nombre compuesto sin apellido (p.ej. 'jose-ignacio32'): se rellena
            apellido_aleatorio = np.random.choice(sorted(APELLIDOS))
            return f"{nombre_fmt} {apellido_aleatorio.title()}"

    # busca un punto de corte donde ambos lados sean palabras conocidas.
    # se prefieren los cortes nombre+apellido o apellido+nombre (permiten
    # reordenar con seguridad); si ambos lados son del mismo tipo (dos
    # nombres o dos apellidos, p.ej. 'marcos'+'paula'), se dejan en el
    # orden en que aparecen porque no hay forma de saber cuál va primero.
    candidatos_ordenables = []
    candidatos_mismo_tipo = []
    for i in range(1, len(alpha)):
        izquierda, derecha = alpha[:i], alpha[i:]
        if izquierda in NOMBRES and derecha in APELLIDOS:
            candidatos_ordenables.append((izquierda, derecha))
        elif izquierda in APELLIDOS and derecha in NOMBRES:
            candidatos_ordenables.append((derecha, izquierda))
        elif izquierda in NOMBRES and derecha in NOMBRES:
            candidatos_mismo_tipo.append((izquierda, derecha))
        elif izquierda in APELLIDOS and derecha in APELLIDOS:
            candidatos_mismo_tipo.append((izquierda, derecha))

    if candidatos_ordenables:
        nombre, apellido = candidatos_ordenables[0]
        return f"{nombre.title()} {apellido.title()}"
    if candidatos_mismo_tipo:
        primero, segundo = candidatos_mismo_tipo[0]
        return f"{primero.title()} {segundo.title()}"

    # solo inicial + apellido, o inicial + nombre completo: en vez de dejar la
    # inicial suelta ('C. Gimenez', 'Anton B.'), se sustituye por un nombre o
    # apellido elegido al azar de nuestro propio diccionario
    if len(alpha) >= 2 and alpha[1:] in APELLIDOS:
        nombre_aleatorio = np.random.choice(sorted(NOMBRES))
        return f"{nombre_aleatorio.title()} {alpha[1:].title()}"
    if len(alpha) >= 2 and alpha[1:] in NOMBRES:
        apellido_aleatorio = np.random.choice(sorted(APELLIDOS))
        return f"{alpha[1:].title()} {apellido_aleatorio.title()}"

    # palabra suelta (todo el nick es una sola palabra, sin segunda mitad):
    # se identifica si es un nombre o un apellido, y se rellena lo que falta
    if alpha in NOMBRES:
        apellido_aleatorio = np.random.choice(sorted(APELLIDOS))
        return f"{alpha.title()} {apellido_aleatorio.title()}"
    if alpha in APELLIDOS:
        nombre_aleatorio = np.random.choice(sorted(NOMBRES))
        return f"{nombre_aleatorio.title()} {alpha.title()}"

    # no se reconoce ninguna palabra: se trata como apellido y se le
    # antepone un nombre al azar, en vez de dejarlo suelto sin completar
    nombre_aleatorio = np.random.choice(sorted(NOMBRES))
    return f"{nombre_aleatorio.title()} {alpha.title()}"


def normalizar_nick(df: pd.DataFrame, columna: str = "nick") -> pd.DataFrame:
    """Aplica separar_nick a toda la columna 'nick', de forma vectorizada
    con .apply() (la lógica de separación no es vectorizable con .str)."""
    df = df.copy()
    df[columna] = df[columna].apply(separar_nick)
    return df


# ---------------------------------------------------------------------------
# Normalización de texto (categorías, multivalor)
# ---------------------------------------------------------------------------

def normalizar_texto(serie: pd.Series, capitalizar: bool = True) -> pd.Series:
    """
    Limpia una columna de texto de forma vectorizada: quita espacios
    sobrantes al principio/final, colapsa espacios dobles internos y
    unifica mayúsculas/minúsculas en formato Title Case.
    """
    limpio = serie.astype("string").str.strip()
    limpio = limpio.str.replace(r"\s+", " ", regex=True)
    if capitalizar:
        limpio = limpio.str.title()
    return limpio


def normalizar_resultado(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza 'resultado' (Victoria/Derrota), que trae mayúsculas y espacios
    inconsistentes ('VICTORIA', '  derrota ', etc.). Los nulos se dejan como
    están: significan que la partida no registró resultado."""
    df = df.copy()
    df["resultado"] = normalizar_texto(df["resultado"])
    return df


def limpiar_hora(df: pd.DataFrame, columna: str = "hora") -> pd.DataFrame:
    """Quita espacios sobrantes de 'hora' (p.ej. '  07:52 ' -> '07:52'),
    que si no se cuelan tal cual en el CSV limpio y en MySQL."""
    df = df.copy()
    df[columna] = df[columna].astype("string").str.strip()
    return df


def normalizar_personajes_usados(df: pd.DataFrame, columna: str = "personajes_usados") -> pd.DataFrame:
    """
    'personajes_usados' es multivalor, separado por ';' (p.ej. 'magnus;tesla;vex'),
    con mayúsculas inconsistentes por personaje. Se normaliza cada personaje por
    separado y se vuelven a unir con ';'. Los nulos se convierten en cadena vacía
    (significa que no se registró qué personajes se usaron).
    """
    df = df.copy()
    personajes = df[columna].fillna("")
    # split(";") -> lista de personajes por fila; se recorta y capitaliza cada uno
    listas = personajes.str.split(";").apply(
        lambda lista: [p.strip().title() for p in lista if p.strip() != ""]
    )
    df[columna] = listas.apply(lambda lista: ";".join(lista))
    return df


# ---------------------------------------------------------------------------
# Fecha y hora
# ---------------------------------------------------------------------------

def limpiar_columna_fecha(df: pd.DataFrame, columna: str = "fecha") -> pd.DataFrame:
    """
    La columna trae 3 formatos de fecha mezclados: AAAA-MM-DD, DD/MM/AAAA
    y DD-MM-AA. Se prueba cada formato sobre toda la columna (vectorizado)
    y se combinan los resultados: cada fecha solo encaja con uno de ellos.
    """
    df = df.copy()
    serie = df[columna].astype(str).str.strip()
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%y"]

    fechas = pd.to_datetime(serie, format=formatos[0], errors="coerce")
    for formato in formatos[1:]:
        fechas = fechas.combine_first(pd.to_datetime(serie, format=formato, errors="coerce"))

    df[columna] = fechas
    return df


# ---------------------------------------------------------------------------
# Columna 'puntos': coma decimal + sufijo " pts" + valores atípicos
# ---------------------------------------------------------------------------

def limpiar_puntos(df: pd.DataFrame, columna: str = "puntos") -> pd.DataFrame:
    """Quita el sufijo ' pts' y convierte la coma decimal en punto, antes de
    pasar la columna a numérico."""
    df = df.copy()
    df[columna] = (
        df[columna]
        .astype("string")
        .str.replace(r"\s*pts\s*$", "", regex=True)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    df[columna] = pd.to_numeric(df[columna], errors="coerce")
    return df


def detectar_atipicos_iqr(serie: pd.Series, factor: float = 1.5) -> pd.Series:
    """Detecta valores atípicos con el método de Tukey (rango intercuartílico)."""
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return (serie < q1 - factor * iqr) | (serie > q3 + factor * iqr)


def corregir_puntos_anomalos(df: pd.DataFrame, columna: str = "puntos", paso: str = "Paso 2") -> pd.DataFrame:
    """
    Corrige valores de 'puntos' anormalmente altos (p.ej. 134000 en vez de
    1340), típicos de un '00' añadido por error: si un valor es atípico y al
    dividirlo entre 100 cae en un rango plausible (0-2000 puntos), se corrige
    dividiendo entre 100. Si no encaja, se deja como NaN.
    """
    df = df.copy()
    atipicos = detectar_atipicos_iqr(df[columna])
    corregibles = atipicos & (df[columna] / 100 >= 0) & (df[columna] / 100 <= 2000)

    df.loc[corregibles, columna] = df.loc[corregibles, columna] / 100
    df.loc[atipicos & ~corregibles, columna] = np.nan

    registrar(paso, f"'{columna}': {corregibles.sum()} corregidos (÷100), "
              f"{(atipicos & ~corregibles).sum()} pasados a NaN")
    return df


# ---------------------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------------------

def eliminar_duplicados(df: pd.DataFrame, subset: list[str], paso: str = "Paso 2") -> pd.DataFrame:
    """Elimina duplicados según 'subset', quedándose con la primera aparición."""
    antes = len(df)
    df = df.drop_duplicates(subset=subset, keep="first")
    registrar(paso, f"Duplicados eliminados: {antes - len(df)}")
    return df


# ---------------------------------------------------------------------------
# Valores nulos
# ---------------------------------------------------------------------------

def tratar_nulos_partidas(df: pd.DataFrame) -> pd.DataFrame:
    """
    - kills: se imputa con la mediana (poco sesgo por outliers)
    - resultado: el nulo tiene significado propio (no se registró el
      desenlace) -> se deja como NaN, no se inventa un resultado
    """
    df = df.copy()
    df["kills"] = df["kills"].fillna(df["kills"].median())
    return df


def tratar_nulos_jugadores(df: pd.DataFrame) -> pd.DataFrame:
    """'region' nula se rellena con una región elegida al azar entre las
    que ya existen en el propio CSV (respetando sus proporciones reales),
    para no perder la fila al agrupar por región más adelante."""
    df = df.copy()
    valores_existentes = df["region"].dropna()
    nulos = df["region"].isna()
    relleno = np.random.choice(valores_existentes, size=nulos.sum())
    df.loc[nulos, "region"] = relleno
    return df


# ---------------------------------------------------------------------------
# Columnas derivadas
# ---------------------------------------------------------------------------

def generar_columnas_derivadas_partidas(df: pd.DataFrame) -> pd.DataFrame:
    """Añade año, mes, día de la semana, ratio kills/muertes y nº de
    personajes usados en la partida."""
    df = df.copy()
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["dia_semana"] = df["fecha"].dt.day_name()

    # ratio K/D: se protege la división por 0 muertes con NaN en vez de infinito
    df["kd_ratio"] = np.where(df["muertes"] > 0, df["kills"] / df["muertes"], np.nan)

    personajes = df["personajes_usados"].fillna("")
    df["num_personajes"] = np.where(personajes == "", 0, personajes.str.count(";") + 1)
    return df


def generar_columnas_derivadas_jugadores(df: pd.DataFrame) -> pd.DataFrame:
    """Añade la antigüedad del jugador en días, calculada desde fecha_registro."""
    df = df.copy()
    df["fecha_registro"] = pd.to_datetime(df["fecha_registro"], format="%Y-%m-%d", errors="coerce")
    df["antiguedad_dias"] = (pd.Timestamp.today().normalize() - df["fecha_registro"]).dt.days
    return df


# ---------------------------------------------------------------------------
# Redondeo: columnas numéricas sin decimales
# ---------------------------------------------------------------------------

def redondear_sin_decimales(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """
    Redondea las columnas indicadas a 0 decimales (p.ej. kd_ratio
    0.8571428571428571 -> 1). Se usa el tipo 'Int64' (con mayúscula) de
    pandas, que admite nulos, para que no queden con un '.0' final al
    guardarlas en CSV.
    """
    df = df.copy()
    for columna in columnas:
        df[columna] = df[columna].round(0).astype("Int64")
    return df


# ---------------------------------------------------------------------------
# Estadísticas descriptivas con NumPy
# ---------------------------------------------------------------------------

def estadisticas_descriptivas(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Media, mediana, desviación típica, mínimo y máximo con NumPy (ignora nulos),
    para varias columnas a la vez, sin bucles."""
    datos = df[columnas].to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "media": np.nanmean(datos, axis=0),
            "mediana": np.nanmedian(datos, axis=0),
            "desviacion_tipica": np.nanstd(datos, axis=0),
            "minimo": np.nanmin(datos, axis=0),
            "maximo": np.nanmax(datos, axis=0),
        },
        index=columnas,
    )


# ---------------------------------------------------------------------------
# Pipeline: encadena todas las funciones anteriores
# ---------------------------------------------------------------------------

def limpiar_partidas(df_partidas: pd.DataFrame) -> pd.DataFrame:
    """Aplica todo el pipeline de limpieza a partidas, en orden."""
    paso = "Paso 2 — partidas"
    registrar(paso, "Limpiando partidas...")
    df = normalizar_resultado(df_partidas)
    df = limpiar_hora(df)
    df = normalizar_personajes_usados(df)
    df = limpiar_columna_fecha(df)
    df = limpiar_puntos(df)
    df = corregir_puntos_anomalos(df, paso=paso)
    df = eliminar_duplicados(df, subset=["id_partida"], paso=paso)
    df = tratar_nulos_partidas(df)
    df = generar_columnas_derivadas_partidas(df)
    df = redondear_sin_decimales(df, ["kills", "puntos", "kd_ratio"])
    return df


def limpiar_jugadores(df_jugadores: pd.DataFrame) -> pd.DataFrame:
    """Aplica el pipeline de limpieza a jugadores, en orden."""
    paso = "Paso 2 — jugadores"
    registrar(paso, "Limpiando jugadores...")
    # semilla fija: separar_nick() y tratar_nulos_jugadores() usan números
    # aleatorios (nombre/apellido de relleno, región de relleno). Con la
    # semilla fija, cada ejecución de main.py da siempre el mismo resultado.
    np.random.seed(42)
    df = df_jugadores.copy()
    df = normalizar_nick(df)
    df = eliminar_duplicados(df, subset=["id_jugador"], paso=paso)
    df = tratar_nulos_jugadores(df)
    df = generar_columnas_derivadas_jugadores(df)
    return df
