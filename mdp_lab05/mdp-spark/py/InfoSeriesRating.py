from __future__ import print_function

import sys
from pyspark.sql import SparkSession

# Outputs:
# ('The Simpsons#1989', "Homer's Enemy (#8.23)", 9.3, 7.143438320209973)
# ('Earth 2#1994', 'First Contact (#1.1)|Redemption (#1.10)|The Enemy Within (#1.9)', 7.2, 6.757142857142857)
# ('Have I Got News for You#1990', 'Episode #35.3 (#35.3)', 9.5, 6.782425742574257)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: InfoSeriesRating.py <filein> <fileout>", file=sys.stderr)
        sys.exit(-1)

    filein = sys.argv[1]
    fileout = sys.argv[2]
    
    # in pyspark shell start with:
    #   filein = "hdfs://cm:9000/uhadoop/shared/imdb/imdb-ratings-two.tsv"
    #   fileout = "hdfs://cm:9000/uhadoop2025/<user>/series-avg-two-py/"
    # and continue line-by-line from here

    spark = SparkSession.builder.appName("InfoSeriesRating").getOrCreate()

    input = spark.read.text(filein).rdd.map(lambda r: r[0])
    # to dump an RDD like input to the pyspark shell, use
    #   input.collect()
    # make sure not to do this for a large RDD

    lines = input.map(lambda line: line.split("\t"))

    tvSeries = lines.filter(lambda line: ("tvSeries" == line[4]) and not ('null' == line[5]) and not (line[5] == ""))

    seriesEpisodeRating = tvSeries.map(lambda line: (line[2]+ "#" + line[3], line[5], float(line[1]))).cache()

    seriesToEpisodeRating = seriesEpisodeRating.map(lambda tup: (tup[0], tup[2])).cache()

    seriesToSumCountRating = seriesToEpisodeRating.aggregateByKey((0.0, 0), \
        lambda sumCount, rating: (sumCount[0] + rating, sumCount[1] + 1), \
        lambda sumCountA, sumCountB: (sumCountA[0] + sumCountB[0], sumCountA[1] + sumCountB[1]))

    seriesToAvgRating = seriesToSumCountRating.mapValues(lambda tup2n: tup2n[0]/tup2n[1])
    
    seriesToMaxRating = seriesToEpisodeRating.aggregateByKey(- float('inf'), \
        lambda maxRating, rating: max(maxRating, rating), \
        lambda maxRatingA, maxRatingB: max(maxRatingA, maxRatingB))

    seriesToMaxRatingToName = seriesEpisodeRating.map(
        lambda tup: (tup[0], (tup[1], tup[2]))).join(
        seriesToMaxRating).filter(
        lambda tup: tup[1][0][1] == tup[1][1]).map(
        lambda tup: (tup[0], tup[1][0])).reduceByKey(
        lambda episodeA, episodeB: (episodeA[0] + "|" + episodeB[0], episodeA[1]))
        
    seriesInformation = seriesToMaxRatingToName.join(seriesToAvgRating)
    
    finalOutput = seriesInformation.map(
        lambda tup: (tup[0], tup[1][0][0], tup[1][0][1], tup[1][1]))
    
    finalOutput.saveAsTextFile(fileout)
    
    spark.stop()