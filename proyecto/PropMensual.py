from __future__ import print_function

import sys
from pyspark.sql import SparkSession

# Proporcion mensual de reportes dentro de cada anio y tipo de lugar.
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: PropMensual.py <filein> <fileout>", file=sys.stderr)
        sys.exit(-1)

    filein = sys.argv[1]
    fileout = sys.argv[2]
    
    spark = SparkSession.builder.appName("PropMensual").getOrCreate()
    
    input = spark.read.parquet(filein)
    
    lines = input.select("id", "date", "primary_type", "location_description").rdd
    
    cleanLines = lines.filter(
        lambda x: x is not None and x[1] is not None and len(x[1]) >= 7
        and x[3] is not None and x[3].strip() != "").cache()
    
    # ((anio, mes, tipo de lugar), 1).
    crimesToSumByYearAndMonth = cleanLines.map(lambda x: ((x[1][:4], x[1][5:7], x[3].strip()), 1))
    
    crimesSumByYearAndMonth = crimesToSumByYearAndMonth.reduceByKey(lambda sumCountA, sumCountB: sumCountA + sumCountB)
    
    # El denominador es el total anual del MISMO tipo de lugar.
    crimesToSumByYear = cleanLines.map(lambda x: ((x[1][:4], x[3].strip()), 1))
    
    crimesSumByYear = crimesToSumByYear.reduceByKey(lambda sumCountA, sumCountB: sumCountA + sumCountB)
    
    # ((anio, mes, lugar), conteo) -> ((anio, lugar), (mes, conteo)).
    reorganizedCrimesSumByYearAndMonth = crimesSumByYearAndMonth.map(lambda x: ((x[0][0], x[0][2]), (x[0][1], x[1])))

    crimesYearToMonthDistribution = reorganizedCrimesSumByYearAndMonth.join(crimesSumByYear)
    

    # (anio, mes, lugar, conteo mensual, total anual del lugar, proporcion).
    finalOutput = crimesYearToMonthDistribution.map(
        lambda x: (x[0][0], x[1][0][0], x[0][1], x[1][0][1],
        x[1][1], float(x[1][0][1]) / x[1][1]))
    
    finalOutput.saveAsTextFile(fileout)
        
    spark.stop()
    
    
