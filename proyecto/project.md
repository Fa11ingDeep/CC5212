# CC5212 — Grupo 7
## Crímenes en Chicago: dónde, cuándo y de qué tipo

El proyecto analiza los ~8,5 millones de crímenes registrados en Chicago desde 2001 (dataset *Crimes – 2001 to Present* del portal de datos de la ciudad). Responde tres preguntas con Spark sobre el clúster del curso:

- **Cuándo:** cómo se reparten los crímenes entre los meses de cada año, según el tipo de lugar.
- **Dónde:** qué zonas de la ciudad concentran más crímenes, en mapas de hexágonos de 500 m.
- **De qué tipo:** cómo cambia esa distribución por tipo de crimen, mes y año.

Todo el cálculo pesado corre en el clúster. En la computadora local solo se dibujan los mapas a partir de resultados ya agregados.

## Flujo del proyecto

| Etapa | Script | Dónde corre | Entrada | Salida |
|---|---|---|---|---|
| 1. Datos | `descargar_chicago_parquet.py` | Fuera del clúster | API del portal de datos | Parquet, cargado en HDFS en `parquet/` |
| 2. Proporción mensual | `PropMensual.py` | Clúster (Spark) | Parquet | `resultados/prop-mensual-v1/` |
| 3. Coropletas | `Coropletas.py` | Clúster (Spark) | Parquet | `resultados/coropletas-v1/` |
| 4. Mapas | `VisualizarCoropletas.py` | Local | CSV de la etapa 3 | PNG en `coropletas-png/` |

Las etapas 2 y 3 son independientes: ambas leen el mismo Parquet y se ejecutan igual. Solo usan Spark, sin APIs ni librerías externas, porque el clúster puede no permitir instalarlas.

Rutas usadas en todo el documento:

| | Ruta |
|---|---|
| Carpeta del grupo en el servidor | `/data/2026/uhadoop/projects/grupo7` |
| Carpeta del grupo en HDFS | `/uhadoop2026/projects/grupo7` (`hdfs://cm:9000/...` en `spark-submit`) |
| Datos de entrada | `<HDFS>/parquet/` |
| Resultados | `<HDFS>/resultados/<nombre-salida>/` |

## Qué calcula cada análisis

### Proporción mensual por tipo de lugar (`PropMensual.py`)

Para cada año, mes y tipo de lugar (`location_description`) cuenta los crímenes del mes y los divide por el total anual de ese mismo tipo de lugar. La salida es un texto con tuplas `(año, mes, lugar, conteo mensual, total anual del lugar, proporción)`.

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
screen -S grupo7
```

## 2. Ejecución de los análisis

`spark-submit` ejecuta cada script en el clúster: lee el Parquet de HDFS y escribe el resultado en HDFS. La carpeta de salida no debe existir previamente. Si se cambia su nombre, hay que actualizarlo también en los pasos siguientes.

Proporción mensual:

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/PropMensual.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/prop-mensual-v1/
```

Coropletas. El tercer argumento es el radio del hexágono en metros (por defecto 500):

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/Coropletas.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/coropletas-v1/ \
  500
```

## 3. Revisión de resultados en HDFS

`hdfs dfs -ls -R` lista los archivos de salida. Cada carpeta debe tener el indicador `_SUCCESS` si el trabajo terminó bien.

```bash
hdfs dfs -ls -R /uhadoop2026/projects/grupo7/resultados/
```

`hdfs dfs -cat` muestra el comienzo de un resultado en la terminal. Por ejemplo, la proporción mensual y las coropletas totales:

```bash
hdfs dfs -cat '/uhadoop2026/projects/grupo7/resultados/prop-mensual-v1/part-*' | head
hdfs dfs -cat '/uhadoop2026/projects/grupo7/resultados/coropletas-v1/coropletas_total_clas/part-*' | head
```

## 4. Descarga de resultados

La descarga tiene dos pasos: primero se copian los resultados de HDFS al disco del servidor y luego se bajan con `scp` a la computadora local.

### 4.1 De HDFS al disco del servidor

La proporción mensual se escribe en varias partes, así que `hdfs dfs -getmerge` las une en un solo archivo de texto:

```bash
hdfs dfs -getmerge \
  /uhadoop2026/projects/grupo7/resultados/prop-mensual-v1/ \
  /data/2026/uhadoop/projects/grupo7/prop-mensual-v1.txt
```

Cada dataset de coropletas ya es un único `part-*.csv` con encabezado, así que basta con `hdfs dfs -get`. El ciclo `for` copia los cuatro con su nombre final:

```bash
cd /data/2026/uhadoop/projects/grupo7
mkdir -p coropletas-v1

for d in coropletas_total_clas coropletas_secuencia_clas coropletas_secuencia_tipo_clas coropletas_anual_clas; do
  hdfs dfs -get \
    "/uhadoop2026/projects/grupo7/resultados/coropletas-v1/$d/part-*.csv" \
    coropletas-v1/$d.csv
done

ls -lh coropletas-v1/
```

Con los datos completos pesan aproximadamente 35 KB (total), 9 MB (mensual), 93 MB (mensual por tipo) y 0,8 MB (anual).

### 4.2 Del servidor a la computadora local

Desde una terminal local, `scp` descarga los resultados a la carpeta actual (`.`). `-P 220` (mayúscula) indica el puerto SSH, y `-r` copia carpetas completas.

```bash
scp -P 220 \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/prop-mensual-v1.txt \
  .
scp -P 220 -r \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/coropletas-v1 \
  .
```

Los `*.csv` están en `.gitignore`, así que no se suben al repositorio aunque queden dentro de `proyecto/`.

## 5. Mapas

`VisualizarCoropletas.py` corre en la computadora local, lee la carpeta `coropletas-v1/` y guarda los PNG en `coropletas-png/`. No calcula nada: los colores ya vienen en la columna `nivel`. Las dependencias están en `requirements.txt`. `contextily` dibuja el mapa de la ciudad bajo los hexágonos y necesita conexión a internet; sin él, los mapas se generan sin fondo.

```bash
pip install -r requirements.txt
python VisualizarCoropletas.py coropletas-v1 coropletas-png
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
