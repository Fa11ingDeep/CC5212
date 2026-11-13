from __future__ import print_function

import sys
from pyspark.sql import SparkSession
import calendar
import math

# Indice mensual ajustado por dias y CV dentro de cada anio y tipo de lugar.
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: EstacionalidadMensual.py <filein> <fileout>", file=sys.stderr)
        sys.exit(-1)

    filein = sys.argv[1]
    fileout = sys.argv[2]

    spark = SparkSession.builder.appName("EstacionalidadMensual").getOrCreate()

    input = spark.read.parquet(filein)

    lines = input.select("id", "date", "primary_type", "location_description").rdd

    # Excluye 2026 antes de calcular ambos conteos.
    cleanLines = lines.filter(
        lambda x: x is not None and x[1] is not None and len(x[1]) >= 7
        and x[3] is not None and x[3].strip() != ""
        and x[1][:4].isdigit() and x[1][5:7].isdigit()
        and x[1][:4] != "2026"
        and 1 <= int(x[1][:4]) <= 9999 and 1 <= int(x[1][5:7]) <= 12).cache()

    # ((anio, mes, tipo de lugar), 1).
    crimesToSumByYearAndMonth = cleanLines.map(
        lambda x: ((x[1][:4], x[1][5:7], x[3].strip()), 1))

    crimesSumByYearAndMonth = crimesToSumByYearAndMonth.reduceByKey(
        lambda sumCountA, sumCountB: sumCountA + sumCountB).cache()

    # ((anio, lugar), conteo mensual) -> ((anio, lugar), total anual).
    crimesToSumByYear = crimesSumByYearAndMonth.map(lambda x: ((x[0][0], x[0][2]), x[1]))

    crimesSumByYear = crimesToSumByYear.reduceByKey(
        lambda sumCountA, sumCountB: sumCountA + sumCountB)

    # Genera los 12 meses para cada (anio, lugar) con reportes en el anio.
    allMonths = crimesSumByYear.flatMap(
        lambda x: [((x[0][0], "%02d" % mes, x[0][1]), x[1]) for mes in range(1, 13)])

    # ((anio, mes, lugar), (total anual, conteo mensual o None)).
    crimesYearToMonthDistribution = allMonths.leftOuterJoin(crimesSumByYearAndMonth)

    # (anio, mes, lugar, reportes_mes, dias_mes, reportes_anio, dias_anio).
    monthlyCalendar = crimesYearToMonthDistribution.map(
        lambda x: (x[0][0], x[0][1], x[0][2],
                   x[1][1] if x[1][1] is not None else 0,
                   calendar.monthrange(int(x[0][0]), int(x[0][1]))[1],
                   x[1][0], 366 if calendar.isleap(int(x[0][0])) else 365))

    # Agrega tasa diaria del mes y tasa diaria del anio.
    monthlyRates = monthlyCalendar.map(
        lambda x: x + (float(x[3]) / x[4], float(x[5]) / x[6]))

    # I_m = 100 * (reportes_mes / dias_mes) / (reportes_anio / dias_anio).
    # (anio, mes, lugar, reportes_mes, dias_mes, reportes_anio, dias_anio,
    #  tasa_diaria_mes, tasa_diaria_anio, indice).
    finalOutput = monthlyRates.map(lambda x: x + (100.0 * x[7] / x[8],)).cache()

    # ((anio, lugar), (conteo mensual, tasa diaria mensual)).
    yearToMonthlyValues = finalOutput.map(lambda x: ((x[0], x[2]), (x[3], x[7])))

    # (n_meses, suma_conteos, suma_conteos_cuadrados, suma_tasas, suma_tasas_cuadradas).
    yearToStatistics = yearToMonthlyValues.aggregateByKey(
        (0, 0, 0, 0.0, 0.0),
        lambda a, x: (a[0] + 1, a[1] + x[0], a[2] + x[0] * x[0],
                      a[3] + x[1], a[4] + x[1] * x[1]),
        lambda a, b: (a[0] + b[0], a[1] + b[1], a[2] + b[2],
                      a[3] + b[3], a[4] + b[4]))

    # Desviacion poblacional: sigma = sqrt(suma(x^2)/n - media^2), n = 12.
    # max(0, ...) evita varianzas negativas por redondeo numerico.
    # Valor: (n_meses, total, media_conteos, sigma_conteos, media_tasas, sigma_tasas).
    yearToMeanAndSigma = yearToStatistics.mapValues(
        lambda x: (x[0], x[1], float(x[1]) / x[0],
                   math.sqrt(max(0.0, float(x[2]) / x[0] - (float(x[1]) / x[0]) ** 2)),
                   x[3] / x[0],
                   math.sqrt(max(0.0, x[4] / x[0] - (x[3] / x[0]) ** 2))))

    # CV = 100 * sigma / media. Se entrega para conteos y para tasas diarias.
    # (anio, lugar, meses, reportes_anio, media_reportes_mes, sigma_reportes_mes,
    #  cv_reportes_pct, media_tasas_diarias, sigma_tasas_diarias, cv_tasas_pct).
    finalCV = yearToMeanAndSigma.map(
        lambda x: (x[0][0], x[0][1], x[1][0], x[1][1], x[1][2], x[1][3],
                   100.0 * x[1][3] / x[1][2], x[1][4], x[1][5],
                   100.0 * x[1][5] / x[1][4]))

    finalOutput.sortBy(lambda x: (x[0], x[2], x[1])).saveAsTextFile(
        fileout.rstrip("/") + "/indices_mensuales")
    finalCV.sortBy(lambda x: (x[0], x[1])).saveAsTextFile(
        fileout.rstrip("/") + "/cv_anual")

    spark.stop()
