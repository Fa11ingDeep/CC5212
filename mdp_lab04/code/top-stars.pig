--------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------
-- This Pig script finds the actors with the highest number of good and bad movies

-- Load data with actor-movie relation
-- raw_roles = LOAD 'hdfs://cm:9000/uhadoop/shared/imdb/imdb-stars-test.tsv' USING PigStorage('\t') AS (star:chararray, title:chararray, year:int, type:chararray, char:chararray, gender:chararray);
-- Al ejecutar sobre el dataset completo, cambiar la l�nea anterior por:
raw_roles = LOAD 'hdfs://cm:9000/uhadoop/shared/imdb/imdb-stars.tsv' USING PigStorage('\t') AS (star:chararray, title:chararray, year:int, type:chararray, char:chararray, gender:chararray);

-- Load data with movie ratings
-- raw_ratings = LOAD 'hdfs://cm:9000/uhadoop/shared/imdb/imdb-ratings-test.tsv' USING PigStorage('\t') AS (votes:int, score:double, title:chararray, year:int, type:chararray, episode:chararray);
-- Al ejecutar sobre el dataset completo, cambiar la l�nea anterior por:
raw_ratings = LOAD 'hdfs://cm:9000/uhadoop/shared/imdb/imdb-ratings.tsv' USING PigStorage('\t') AS (votes:int, score:double, title:chararray, year:int, type:chararray, episode:chararray);

-- Add your commands here to complete the script

-- filtro de las condiciones
movies = FILTER raw_ratings BY votes >= 1000 AND type == 'movie';
movie_roles = FILTER raw_roles BY type == 'movie';

good_movies = FILTER movies BY score >= 8.0;

bad_movies = FILTER movies BY score <= 3.0;

stars_in_good_movies = JOIN movie_roles BY (title, year), good_movies BY (title, year);

stars_in_bad_movies = JOIN movie_roles BY (title, year), bad_movies BY (title, year);

good_stars_movies = FOREACH stars_in_good_movies GENERATE 
movie_roles::star AS star, 
movie_roles::title AS title, 
movie_roles::year AS year;

bad_stars_movies = FOREACH stars_in_bad_movies GENERATE 
movie_roles::star AS star,
movie_roles::title AS title,
movie_roles::year AS year;

good_stars_movies_unique = DISTINCT good_stars_movies;

bad_stars_movies_unique = DISTINCT bad_stars_movies;

-- construccion del conteo para los mejores actores
all_stars_raw = FOREACH movie_roles GENERATE star AS star;

all_stars = DISTINCT all_stars_raw;

zero_counts = FOREACH all_stars GENERATE star AS star, 0 AS count;

good_ones = FOREACH good_stars_movies_unique GENERATE star AS star, 1 AS count;

good_with_zeros = UNION zero_counts, good_ones;

good_groups = GROUP good_with_zeros BY star;

good_counts = FOREACH good_groups GENERATE group AS star,
SUM(good_with_zeros.count) AS count;

ordered_good_counts = ORDER good_counts BY count DESC, star ASC;

-- construccion del conteo para los peores actores
bad_ones = FOREACH bad_stars_movies_unique GENERATE star AS star, 1 AS count;

bad_with_zeros = UNION zero_counts, bad_ones;

bad_groups = GROUP bad_with_zeros BY star;

bad_counts = FOREACH bad_groups GENERATE group AS star,
SUM(bad_with_zeros.count) AS count;

ordered_bad_counts = ORDER bad_counts BY count DESC, star ASC;

-- STORE ordered_good_counts INTO 'hdfs://cm:9000/uhadoop2026/npc/top-stars-good-test/' USING PigStorage('\t');

-- STORE ordered_bad_counts INTO 'hdfs://cm:9000/uhadoop2026/npc/top-stars-bad-test/' USING PigStorage('\t');

STORE ordered_good_counts INTO 'hdfs://cm:9000/uhadoop2026/npc/top-stars-good/' USING PigStorage('\t');

STORE ordered_bad_counts INTO 'hdfs://cm:9000/uhadoop2026/npc/top-stars-bad/' USING PigStorage('\t');