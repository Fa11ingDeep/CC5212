from __future__ import print_function

import math
import os
import sys

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

# Datasets para coropletas hexagonales sobre Chicago, calculados solo con Spark
# (sin h3 ni APIs externas).
#
# Salidas (un CSV con encabezado por carpeta, dentro de <dirout>):
#   coropletas_total_clas           {n_pleta, freq, nivel, vmin, q3, vmax}
#   coropletas_secuencia_clas       {date, n_pleta, freq, nivel, vmin, q3, vmax}
#   coropletas_secuencia_tipo_clas  {date, primary_type, n_pleta, freq, nivel, vmin, q3, vmax}
#   coropletas_anual_clas           {anio, n_pleta, freq, nivel, vmin, q3, vmax}
#
# n_pleta = "q_r", celda hexagonal de radio hex_m metros.
# date    = "YYYY-MM"; anio = "YYYY". Se excluye 2026: el anio en curso esta a medias
#           y sus meses y su total se verian bajos.
# freq    = crimenes de la celda (en toda la historia / ese mes / ese mes y tipo).
# vmin, q3, vmax = minimo, tercer cuartil y maximo de freq en todo el dataset
#                  (en el de tipos, por tipo): la escala es fija entre meses.
# nivel   = color en escala log: 0 = vmin (azul, seguro), 0.5 = q3, 1 = vmax (rojo,
#           peligroso). Si q3 == vmin no hay mitad azul y esos valores quedan en 0.5.

# Proyeccion local centrada en Chicago (VisualizarCoropletas.py usa la misma) y caja
# que descarta coordenadas nulas o erroneas (p. ej. lat 36.6).
LAT0, LON0 = 41.84, -87.68
LAT_MIN, LAT_MAX = 41.60, 42.05
LON_MIN, LON_MAX = -87.95, -87.50
M_POR_GRADO_LAT = 6371008.8 * math.pi / 180.0
M_POR_GRADO_LON = M_POR_GRADO_LAT * math.cos(math.radians(LAT0))
SQRT3 = math.sqrt(3.0)

if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: Coropletas.py <filein> <dirout> [hex_m=500]", file=sys.stderr)
        sys.exit(-1)

    filein = sys.argv[1]
    dirout = sys.argv[2]
    hex_m = float(sys.argv[3]) if len(sys.argv) == 4 else 500.0

    spark = SparkSession.builder.appName("Coropletas") \
        .config("spark.sql.optimizer.canChangeCachedPlanOutputPartitioning", "true") \
        .getOrCreate()

    # (fecha YYYY-MM valida, sin 2026, con tipo de lugar),
    # exigen ademas coordenadas dentro de Chicago y tipo de crimen.
    crimenes = spark.read.parquet(filein).select(
            F.substring("date", 1, 7).alias("date"),
            F.trim("primary_type").alias("primary_type"),
            F.trim("location_description").alias("lugar"),
            F.col("latitude").cast("double").alias("lat"),
            F.col("longitude").cast("double").alias("lon")) \
        .where(F.col("date").rlike("^[0-9]{4}-(0[1-9]|1[0-2])$")
               & (F.substring("date", 1, 4) != "2026")
               & (F.col("lugar") != "")
               & F.col("lat").between(LAT_MIN, LAT_MAX)
               & F.col("lon").between(LON_MIN, LON_MAX)
               & (F.col("primary_type") != ""))

    # >>>   Nota este es un calculo conocido, pero ante la inseretidumbre de
    #       poder usar la libreria externa preferi usar el formato canonico

    # Celda hexagonal (pointy-top): (lat, lon) -> metros -> coordenadas axiales
    # fraccionarias (qf, rf, sf), redondeadas con "cube rounding" (se corrige la
    # coordenada con mayor error de redondeo para que q + r + s = 0).

    x = (F.col("lon") - LON0) * M_POR_GRADO_LON
    y = (F.col("lat") - LAT0) * M_POR_GRADO_LAT
    qf = (SQRT3 / 3 * x - y / 3) / hex_m
    rf = (2.0 / 3 * y) / hex_m
    sf = -qf - rf
    q, r, s = F.round(qf), F.round(rf), F.round(sf)
    dq, dr, ds = F.abs(q - qf), F.abs(r - rf), F.abs(s - sf)
    q = F.when((dq > dr) & (dq > ds), -r - s).otherwise(q)
    r = F.when((dq > dr) & (dq > ds), r).when(dr > ds, -q - s).otherwise(r)
    crimenes = crimenes.select("date", "primary_type",
                               F.concat_ws("_", q.cast("int"), r.cast("int")).alias("n_pleta"))

    # Los crimenes se recorren una sola vez, en el conteo mas detallado (mes, tipo y
    # celda). Los demas conteos suman sobre el anterior, cada vez mas pequeno.
    por_tipo = crimenes.groupBy("date", "primary_type", "n_pleta") \
        .agg(F.count("*").alias("freq")).cache()
    por_mes = por_tipo.groupBy("date", "n_pleta").agg(F.sum("freq").alias("freq")).cache()
    total = por_mes.groupBy("n_pleta").agg(F.sum("freq").alias("freq"))

    por_anio = por_mes.withColumn("anio", F.substring("date", 1, 4)) \
        .groupBy("anio", "n_pleta").agg(F.sum("freq").alias("freq"))

    # (carpeta de salida, conteo, columnas que definen cada fila, grupo con escala propia)
    salidas = [
        ("coropletas_total_clas", total, ["n_pleta"], []),
        ("coropletas_secuencia_clas", por_mes, ["date", "n_pleta"], []),
        ("coropletas_secuencia_tipo_clas", por_tipo, ["date", "primary_type", "n_pleta"],
         ["primary_type"]),
        ("coropletas_anual_clas", por_anio, ["anio", "n_pleta"], []),
    ]
    for nombre, conteo, claves, grupo in salidas:
        escala = Window.partitionBy(*grupo)
        conteo = conteo \
            .withColumn("vmin", F.min("freq").over(escala)) \
            .withColumn("q3", F.expr("percentile(freq, 0.75)").over(escala)) \
            .withColumn("vmax", F.max("freq").over(escala))

        l, lmin, lq3, lmax = F.log10("freq"), F.log10("vmin"), F.log10("q3"), F.log10("vmax")
        nivel = F.when(F.col("freq") > F.col("q3"), 0.5 + 0.5 * (l - lq3) / (lmax - lq3)) \
                 .when(F.col("q3") > F.col("vmin"), 0.5 * (l - lmin) / (lq3 - lmin)) \
                 .otherwise(0.5)

        conteo.select(claves + ["freq", F.round(nivel, 4).alias("nivel"), "vmin", "q3", "vmax"]) \
            .coalesce(1).write.option("header", True).csv(os.path.join(dirout, nombre))

    spark.stop()
