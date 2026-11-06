from __future__ import print_function

import math
import sys

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

# Datasets para coropletas hexagonales sobre Chicago.
#
# La grilla hexagonal se calcula aqui mismo (sin h3 ni APIs externas):
#   1. (lat, lon) se proyecta a metros con una proyeccion equirectangular
#      local centrada en Chicago (error despreciable a escala de ciudad).
#   2. (x, y) se convierte a coordenadas axiales (q, r) de un hexagono
#      "pointy-top" de radio HEX_M metros y se redondea con cube rounding.
#   3. n_pleta = "q_r" identifica la celda.
# Todo se hace con funciones nativas de Spark (sin UDF de Python).
#
# Salidas (CSV con encabezado, una carpeta por dataset dentro de <dirout>):
#   coropletas_total_clas           {unique_key, n_pleta, freq}
#   coropletas_secuencia_clas       {unique_key, date, n_pleta, freq}
#   coropletas_secuencia_tipo_clas  {unique_key, date, primary_type, n_pleta, freq}
#
# date = "YYYY-MM" (mensual, igual que PropMensual.py).
# freq = cantidad de crimenes de la celda (en esa fecha / fecha y tipo).

# Centro de referencia de la proyeccion y caja que contiene Chicago
# (descarta coordenadas nulas o erroneas, p. ej. lat 36.6).
LAT0 = 41.84
LON0 = -87.68
LAT_MIN, LAT_MAX = 41.60, 42.05
LON_MIN, LON_MAX = -87.95, -87.50

R_TIERRA = 6371008.8
SQRT3 = math.sqrt(3.0)
M_POR_GRADO_LAT = R_TIERRA * math.pi / 180.0
M_POR_GRADO_LON = M_POR_GRADO_LAT * math.cos(math.radians(LAT0))


def hex_axial(lat, lon, hex_m):
    """Columnas (q, r) enteras de la celda hexagonal que contiene (lat, lon)."""
    x = (lon - LON0) * M_POR_GRADO_LON
    y = (lat - LAT0) * M_POR_GRADO_LAT
    qf = (SQRT3 / 3.0 * x - 1.0 / 3.0 * y) / hex_m
    rf = (2.0 / 3.0 * y) / hex_m
    sf = -qf - rf

    qr, rr, sr = F.round(qf), F.round(rf), F.round(sf)
    dq, dr, ds = F.abs(qr - qf), F.abs(rr - rf), F.abs(sr - sf)

    # Cube rounding: se corrige la coordenada con mayor error de redondeo.
    q = F.when((dq > dr) & (dq > ds), -rr - sr).otherwise(qr)
    r = F.when((dq > dr) & (dq > ds), rr) \
         .when(dr > ds, -qr - sr) \
         .otherwise(rr)
    return q.cast("int"), r.cast("int")


def con_freq(df, claves):
    """Agrega freq = cantidad de filas que comparten las columnas `claves`."""
    return df.withColumn("freq", F.count(F.lit(1)).over(Window.partitionBy(*claves)))


def escribir(df, dirout, nombre):
    # escape '"' = CSV estandar (lo que esperan pandas, QGIS, etc.).
    df.write.option("header", "true").option("escape", '"').csv(dirout.rstrip("/") + "/" + nombre)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: Coropletas.py <filein> <dirout> [hex_m=500]", file=sys.stderr)
        sys.exit(-1)

    filein = sys.argv[1]
    dirout = sys.argv[2]
    hex_m = float(sys.argv[3]) if len(sys.argv) == 4 else 500.0

    spark = SparkSession.builder.appName("Coropletas").getOrCreate()

    raw = spark.read.parquet(filein)

    # Base georreferenciada: un registro por crimen con fecha y celda.
    lat = F.col("latitude").cast("double")
    lon = F.col("longitude").cast("double")
    base = raw.select(
            F.col("id").alias("unique_key"),
            F.substring(F.col("date"), 1, 7).alias("date"),
            F.trim(F.col("primary_type")).alias("primary_type"),
            lat.alias("latitude"),
            lon.alias("longitude")) \
        .where(F.col("latitude").between(LAT_MIN, LAT_MAX)
               & F.col("longitude").between(LON_MIN, LON_MAX)
               & (F.length("date") == 7)
               & F.col("primary_type").isNotNull() & (F.col("primary_type") != ""))

    q, r = hex_axial(F.col("latitude"), F.col("longitude"), hex_m)
    base = base.withColumn("n_pleta", F.concat_ws("_", q, r)).cache()

    # Totales (toda la historia).
    escribir(con_freq(base.select("unique_key", "n_pleta"), ["n_pleta"]),
             dirout, "coropletas_total_clas")

    # Secuencia mensual.
    escribir(con_freq(base.select("unique_key", "date", "n_pleta"),
                      ["date", "n_pleta"]),
             dirout, "coropletas_secuencia_clas")

    # Secuencia mensual por tipo de crimen.
    escribir(con_freq(base.select("unique_key", "date", "primary_type", "n_pleta"),
                      ["date", "primary_type", "n_pleta"]),
             dirout, "coropletas_secuencia_tipo_clas")

    spark.stop()
