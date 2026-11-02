# CC5212 — Grupo 7
## Ejecución del módulo de proporción mensual por tipo de lugar

Este módulo corresponde a una parte del proyecto. Se utilizan los scripts disponibles en el servidor y los Parquet cargados en HDFS.

## 1. Conexión al servidor

`ssh` abre una sesión en el servidor del curso mediante el puerto 220.

```bash
ssh -p 220 uhadoop@cm.dcc.uchile.cl
```

`cd` selecciona la carpeta del proyecto y `screen` crea una sesión para mantener la ejecución ante desconexiones.

```bash
cd /data/2026/uhadoop/projects/grupo7
screen -S revision-propmensual
```

## 2. Ejecución sobre los datos completos

`spark-submit` ejecuta `PropMensual.py` en el clúster, leyendo los Parquet de HDFS y guardando allí las proporciones mensuales por año y tipo de lugar.

```bash
spark-submit --master spark://cluster-01:7077 \
  /data/2026/uhadoop/projects/grupo7/PropMensual.py \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/parquet/ \
  hdfs://cm:9000/uhadoop2026/projects/grupo7/resultados/revision-prop-mensual-v1/
```

La carpeta de salida no debe existir previamente. Si se cambia su nombre, actualizar también las rutas de los pasos siguientes.

## 3. Consulta de resultados

`hdfs dfs -ls` lista los archivos de salida, incluidas las partes del resultado y el indicador `_SUCCESS` cuando el trabajo termina correctamente.

```bash
hdfs dfs -ls \
  /uhadoop2026/projects/grupo7/resultados/revision-prop-mensual-v1/
```

`hdfs dfs -cat` muestra el contenido de todas las partes del resultado en la terminal.

```bash
hdfs dfs -cat \
  '/uhadoop2026/projects/grupo7/resultados/revision-prop-mensual-v1/part-*'
```

## 4. Consolidación de resultados en el servidor

`hdfs dfs -getmerge` reúne las partes de HDFS en un único archivo de texto en el disco local del servidor.

```bash
hdfs dfs -getmerge \
  /uhadoop2026/projects/grupo7/resultados/revision-prop-mensual-v1/ \
  /data/2026/uhadoop/projects/grupo7/revision-prop-mensual-v1.txt
```

## 5. Descarga de resultados

Desde una terminal local, `scp` descarga el archivo consolidado a la carpeta actual (`.`) de la computadora. `-P 220` indica el puerto SSH.

```bash
scp -P 220 \
  uhadoop@cm.dcc.uchile.cl:/data/2026/uhadoop/projects/grupo7/revision-prop-mensual-v1.txt \
  .
```
