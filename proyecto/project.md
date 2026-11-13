# CC5212 — Grupo 7
## Crímenes en Chicago: dónde, cuándo y de qué tipo

El proyecto analiza los ~8,5 millones de crímenes registrados en Chicago desde 2001 (dataset *Crimes – 2001 to Present* del portal de datos de la ciudad). Responde tres preguntas con Spark sobre el clúster del curso:

- **Cuándo:** cómo se reparten los crímenes entre los meses de cada año, según el tipo de lugar.
- **Dónde:** qué zonas de la ciudad concentran más crímenes, en mapas de hexágonos de 500 m.
- **De qué tipo:** cómo cambia esa distribución por tipo de crimen, mes y año.

Todo el cálculo pesado corre en el clúster. En la computadora local se dibujan los gráficos y mapas a partir de resultados ya agregados.

## Flujo del proyecto

| Etapa | Script | Dónde corre | Entrada | Salida |
|---|---|---|---|---|
| 1. Datos | `descargar_chicago_parquet.py` | Fuera del clúster | API del portal de datos | Parquet, cargado en HDFS en `parquet/` |
| 2. Estacionalidad | [EstacionalidadMensual.py](EstacionalidadMensual.py) | Clúster (Spark) | Parquet | `resultados/estacionalidad/` |
| 3. Coropletas | `Coropletas.py` | Clúster (Spark) | Parquet | `resultados/coropletas/` |
| 4. Gráficos de estacionalidad | [VisualizarEstacionalidad.py](VisualizarEstacionalidad.py) | Local | `indices-mensuales.txt` y `cv-anual.txt` | Figuras de índices y CV por lugar |
| 5. Mapas | `VisualizarCoropletas.py` | Local | CSV de la etapa 3 | PNG en `coropletas-png/` |

Las etapas 2 y 3 son independientes: ambas leen el mismo Parquet y se ejecutan igual. Solo usan Spark, sin APIs ni librerías externas, porque el clúster puede no permitir instalarlas.

Rutas usadas en todo el documento:

| | Ruta |
|---|---|
| Carpeta del grupo en el servidor | `/data/2026/uhadoop/projects/grupo7` |
| Carpeta del grupo en HDFS | `/uhadoop2026/projects/grupo7` (`hdfs://cm:9000/...` en `spark-submit`) |
| Datos de entrada | `<HDFS>/parquet/` |
| Resultados | `<HDFS>/resultados/<nombre-salida>/` |

## Qué calcula cada análisis

### Estacionalidad mensual por tipo de lugar

`EstacionalidadMensual.py` calcula el índice mensual ajustado por días y el CV
anual por lugar. Excluye 2026. Las fórmulas y columnas se describen en la sección 5.

### Coropletas hexagonales (`Coropletas.py`)

Asigna cada crimen a una celda hexagonal (`n_pleta`, de la forma `"q_r"`) calculada con funciones nativas de Spark, sin `h3`. Luego cuenta los crímenes por celda y calcula la escala de color de cada fila. Escribe un CSV con encabezado por dataset:

| Subcarpeta | Columnas | Una fila por |
|---|---|---|
| `coropletas_total_clas` | `n_pleta, freq, nivel, vmin, q3, vmax` | celda (toda la historia) |
| `coropletas_secuencia_clas` | `date, n_pleta, freq, nivel, vmin, q3, vmax` | mes y celda |
| `coropletas_secuencia_tipo_clas` | `date, primary_type, n_pleta, freq, nivel, vmin, q3, vmax` | mes, tipo de crimen y celda |
| `coropletas_anual_clas` | `anio, n_pleta, freq, nivel, vmin, q3, vmax` | año y celda |

- `date` es `YYYY-MM`. `anio` es `YYYY` e incluye solo años con los 12 meses, porque el año en curso está incompleto.
- `freq` es la cantidad de crímenes de la celda en ese grupo.
- `nivel` es el color, entre 0 (pocos crímenes, azul) y 1 (muchos, rojo), con 0,5 en el tercer cuartil. Se calcula en escala logarítmica a partir de `vmin`, `q3` y `vmax`: el mínimo, el tercer cuartil y el máximo de `freq` en todo el dataset (en `coropletas_secuencia_tipo_clas`, por tipo de crimen). Como la escala es fija, el mismo `nivel` significa la misma cantidad de crímenes en cualquier mes o año.

## 1. Conexión al servidor

`ssh` abre una sesión en el servidor del curso mediante el puerto 220.

```bash
ssh -p 220 uhadoop@cm.dcc.uchile.cl
```

`cd` selecciona la carpeta del grupo y `screen` crea una sesión para que los trabajos sigan corriendo ante desconexiones.

```bash
cd /data/2026/uhadoop/projects/grupo7
screen -S estacionalidad
```

## 2. Ejecución de los análisis

`spark-submit` ejecuta cada script en el clúster: lee el Parquet de HDFS y escribe el resultado en HDFS. La carpeta de salida no debe existir previamente. Si se cambia su nombre, hay que actualizarlo también en los pasos siguientes.

Estacionalidad mensual:

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/EstacionalidadMensual.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/estacionalidad/
```

Coropletas. El tercer argumento es el radio del hexágono en metros (por defecto 500):

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/Coropletas.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/coropletas/ \
  500
```

## 3. Revisión de resultados en HDFS

`hdfs dfs -ls -R` lista los archivos de salida. Cada carpeta debe tener el indicador `_SUCCESS` si el trabajo terminó bien.

```bash
hdfs dfs -ls -R /uhadoop2026/projects/grupo7/resultados/
```

`hdfs dfs -cat` muestra el comienzo de un resultado en la terminal. Por ejemplo, los índices mensuales y las coropletas totales:

```bash
hdfs dfs -cat '/uhadoop2026/projects/grupo7/resultados/estacionalidad/indices_mensuales/part-*' | head
hdfs dfs -cat '/uhadoop2026/projects/grupo7/resultados/coropletas/coropletas_total_clas/part-*' | head
```

## 4. Descarga de resultados

La descarga tiene dos pasos: primero se copian los resultados de HDFS al disco del servidor y luego se bajan con `scp` a la computadora local.

### 4.1 De HDFS al disco del servidor

Los índices y el CV se escriben en varias partes. Se reúne cada salida en un archivo:

```bash
hdfs dfs -getmerge \
  /uhadoop2026/projects/grupo7/resultados/estacionalidad/indices_mensuales/ \
  /data/2026/uhadoop/projects/grupo7/indices-mensuales.txt
hdfs dfs -getmerge \
  /uhadoop2026/projects/grupo7/resultados/estacionalidad/cv_anual/ \
  /data/2026/uhadoop/projects/grupo7/cv-anual.txt
```

Cada dataset de coropletas ya es un único `part-*.csv` con encabezado, así que basta con `hdfs dfs -get`. El ciclo `for` copia los cuatro con su nombre final:

```bash
cd /data/2026/uhadoop/projects/grupo7
mkdir -p coropletas

for d in coropletas_total_clas coropletas_secuencia_clas coropletas_secuencia_tipo_clas coropletas_anual_clas; do
  hdfs dfs -get \
    "/uhadoop2026/projects/grupo7/resultados/coropletas/$d/part-*.csv" \
    coropletas/$d.csv
done

ls -lh coropletas/
```

Con los datos completos pesan aproximadamente 35 KB (total), 9 MB (mensual), 93 MB (mensual por tipo) y 0,8 MB (anual).

### 4.2 Del servidor a la computadora local

Desde una terminal local, `scp` descarga los resultados a la carpeta actual (`.`). `-P 220` (mayúscula) indica el puerto SSH, y `-r` copia carpetas completas.

```bash
scp -P 220 \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/indices-mensuales.txt \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/cv-anual.txt \
  .
scp -P 220 -r \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/coropletas \
  .
```

Los `*.csv` están en `.gitignore`, así que no se suben al repositorio aunque queden dentro de `proyecto/`.

## 5. Índice mensual y coeficiente de variación

[EstacionalidadMensual.py](EstacionalidadMensual.py) conserva el estilo de
los ejemplos del laboratorio 5: lee el Parquet, trabaja con RDDs usando
`map`, `filter`, `reduceByKey`, `flatMap`, `leftOuterJoin` y `aggregateByKey`,
y escribe tuplas con `saveAsTextFile`. Toda la lógica está dentro de
`if __name__ == "__main__"`, sin funciones auxiliares, con transformaciones
mediante lambdas y exactamente dos argumentos: `<filein> <fileout>`.
Solo requiere PySpark y la biblioteca estándar de Python. Es independiente
del script de visualización.

Para cada año y tipo de lugar, calcula:

\[
I_m = 100\frac{N_m/d_m}{N_a/d_a}
\]

Aquí, `N_m` y `N_a` son los reportes del mes y del año del mismo lugar;
`d_m` y `d_a` son sus días calendario. Se consideran los años bisiestos.
Un índice de 120 significa una tasa diaria 20 % superior a la media diaria
anual; 80 significa 20 % inferior. La referencia es 100, no 0.

El resumen anual entrega dos versiones del CV:

\[
\mu = \frac{1}{12}\sum_{m=1}^{12}x_m,\qquad
\sigma = \sqrt{\frac{1}{12}\sum_{m=1}^{12}(x_m-\mu)^2},\qquad
CV = 100\frac{\sigma}{\mu}.
\]

| Indicador | Valores mensuales `x_m` | Interpretación |
|---|---|---|
| `cv_reportes_pct` | Conteo `N_m` | Variación de los conteos; incluye el efecto de la duración del mes |
| `cv_tasas_pct` | Tasa diaria `N_m / d_m` | Variación mensual ajustada por la duración del mes |

Se usa desviación **poblacional**, dividiendo por 12, porque se describen los
doce meses del año. La media de tasas del CV da igual peso a cada mes; no es
necesariamente igual a la tasa anual `N_a / d_a`, que pondera por días.
Dentro de un mismo año y lugar, el CV de las tasas también equivale al CV
de los índices, porque estos multiplican todas las tasas por la misma constante.

El script completa con cero los meses sin reportes de un lugar y excluye
únicamente 2026 directamente en `cleanLines`, antes de calcular
los conteos mensuales y anuales. El filtro es fijo:
no depende de la fecha de ejecución ni verifica automáticamente la cobertura
de los demás años. Se supone que los años restantes están completos. Los
cambios de nombre de las categorías tampoco se unifican automáticamente.

Ejemplo de ejecución; copiar primero el script al servidor
en `/data/2026/uhadoop/projects/grupo7/`:

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/EstacionalidadMensual.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/estacionalidad/
```

Las carpetas de salida no deben existir previamente. Produce dos resultados
sin encabezado:

| Subcarpeta | Campos de cada tupla, en orden |
|---|---|
| `indices_mensuales` | `(anio, mes, lugar, reportes_mes, dias_mes, reportes_anio, dias_anio, tasa_diaria_mes, tasa_diaria_anio, indice)` |
| `cv_anual` | `(anio, lugar, meses, reportes_anio, media_reportes_mes, sigma_reportes_mes, cv_reportes_pct, media_tasas_diarias, sigma_tasas_diarias, cv_tasas_pct)` |

Para revisar y reunir las partes en el servidor:

```bash
hdfs dfs -cat '/uhadoop2026/projects/grupo7/resultados/estacionalidad/cv_anual/part-*' | head
hdfs dfs -getmerge /uhadoop2026/projects/grupo7/resultados/estacionalidad/indices_mensuales/ /data/2026/uhadoop/projects/grupo7/indices-mensuales.txt
hdfs dfs -getmerge /uhadoop2026/projects/grupo7/resultados/estacionalidad/cv_anual/ /data/2026/uhadoop/projects/grupo7/cv-anual.txt
```

Para contrastar observaciones del gráfico, revisar si los meses señalados
mantienen índices por encima o por debajo de 100 en varios años y comparar
`cv_tasas_pct` entre lugares y años junto con sus volúmenes de reportes.
Un CV mayor indica más dispersión, pero no identifica los meses del máximo
ni demuestra por sí solo una estacionalidad recurrente o significancia
estadística. Los lugares con pocos reportes pueden tener CV altos por
fluctuaciones de conteos pequeños. No se usa un umbral universal de CV.

### Visualizar los indicadores localmente

`VisualizarEstacionalidad.py` lee `indices-mensuales.txt` y `cv-anual.txt`
desde la carpeta del script. Requiere únicamente `matplotlib` y la biblioteca
estándar de Python. No requiere Spark ni otros scripts de visualización.

```bash
python -m pip install matplotlib
python proyecto/VisualizarEstacionalidad.py --top 4 --columnas 2
python proyecto/VisualizarEstacionalidad.py --anios 2020 2023 2025 --lugares STREET RESIDENCE
```

Genera dos imágenes, cada una con un panel por lugar:

- `estacionalidad-indices_...png`: meses en X, índice en Y y líneas por año.
  La línea negra en 100 representa la tasa diaria anual del lugar.
- `estacionalidad-cv_...png`: años en X y CV en Y, con una línea para tasas
  diarias y otra para conteos mensuales. Cada punto resume los doce meses.

`--top N` selecciona por reportes acumulados en los años elegidos y lo indica
en el subtítulo. Sin `--top` ni `--lugares`, se incluyen todos los lugares.
`--columnas` controla la cuadrícula; `--salida` indica una **carpeta** para ambas
imágenes; `--mostrar` también abre las figuras. Los nombres automáticos incluyen
la selección, los años y las columnas, sin sufijos de versión.
Para otros archivos se utilizan `--indices RUTA` y `--cv RUTA`.
Los archivos deben tener los mismos años, lugares y totales, con doce índices
mensuales por grupo. Un año sin datos para un lugar se omite, no se trata como cero.

## 6. Mapas

`VisualizarCoropletas.py` corre en la computadora local, lee la carpeta `coropletas/` y guarda los PNG en `coropletas-png/`. No calcula nada: los colores ya vienen en la columna `nivel`. Las dependencias están en `requirements.txt`. `contextily` dibuja el mapa de la ciudad bajo los hexágonos y necesita conexión a internet; sin él, los mapas se generan sin fondo.

```bash
pip install -r requirements.txt
python VisualizarCoropletas.py coropletas coropletas-png
```

| Archivo | Contenido | Opción |
|---|---|---|
| `coropleta_total.png` | Toda la historia | — |
| `coropleta_anios.png` | Un mapa por año (por defecto, cada 2 años hasta el último completo) | `--anios 2015,2020,2025` |
| `coropleta_meses_<año>.png` | Un mapa por mes de un año | `--anio YYYY` |
| `coropleta_mes.png` | Un mes (por defecto, el penúltimo, porque el último suele estar incompleto) | `--mes YYYY-MM` |
| `coropleta_tipos_<mes>.png` | Los 12 tipos de crimen más frecuentes del mes | `--mes YYYY-MM` |
| `mes_tipo_<mes>/<TIPO>.png` | Un mapa por cada uno de esos 12 tipos, o solo uno | `--tipo PRIMARY_TYPE` |

En los mapas, azul son pocos crímenes, gris claro es el tercer cuartil y rojo son muchos. Si `Coropletas.py` se ejecutó con otro radio, hay que pasar el mismo valor con `--hex_m`.
