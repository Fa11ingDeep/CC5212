#!/usr/bin/env python3
"""Descarga Chicago Crime por paginas y guarda un dataset Parquet para Spark.
Ruta predeterminada: /home/bot/CC5212/proyecto
Uso: python3 descargar_chicago_parquet.py
"""
import json
import os
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DESTINO = Path('/home/bot/CC5212/proyecto')
PARTES = DESTINO / 'chicago_crime_parquet'
ESTADO = DESTINO / 'estado_descarga.json'
URL = 'https://data.cityofchicago.org/resource/ijzp-q8t2.json'
METADATA = 'https://data.cityofchicago.org/api/views/ijzp-q8t2.json'
TAMANO_LOTE = 300000


def sesion_http():
    s = requests.Session()
    retry = Retry(total=8, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=['GET'], respect_retry_after_header=True)
    s.mount('https://', HTTPAdapter(max_retries=retry))
    s.headers.update({'User-Agent': 'ChicagoCrime-CC5212/1.0'})
    token = os.environ.get('SOCRATA_APP_TOKEN')
    if token:
        s.headers['X-App-Token'] = token
    return s


def pedir(s, url, params=None):
    for intento in range(1, 6):
        try:
            r = s.get(url, params=params, timeout=(20, 180))
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if intento == 5:
                raise RuntimeError(f'Error consultando {url}: {e}') from e
            espera = min(60, 3 * intento)
            print(f'  Error temporal: {e}. Reintento en {espera}s...', flush=True)
            time.sleep(espera)


def guardar_estado(info):
    temp = ESTADO.with_suffix('.json.tmp')
    temp.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(ESTADO)


def convertir_valor(v):
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return str(v)


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    PARTES.mkdir(parents=True, exist_ok=True)
    s = sesion_http()

    if ESTADO.exists():
        info = json.loads(ESTADO.read_text(encoding='utf-8'))
        print('Reanudando descarga existente.', flush=True)
    else:
        meta = pedir(s, METADATA)
        columnas = [c['fieldName'] for c in meta['columns']
                    if c.get('fieldName') and not c['fieldName'].startswith(':')]
        if 'id' not in columnas:
            raise RuntimeError('La API no incluye la columna id.')
        maximo = pedir(s, URL, {'$select': 'max(id) as max_id'})
        tope = int(maximo[0]['max_id'])
        info = {'ultimo_id': 0, 'max_id_inicial': tope, 'lotes': 0,
                'registros': 0, 'columnas': columnas, 'finalizado': False}
        guardar_estado(info)
        print(f'ID máximo capturado para esta descarga: {tope}', flush=True)

    if info.get('finalizado'):
        print(f"Descarga terminada previamente: {info['registros']:,} registros.")
        return

    cols = info['columnas']
    schema = pa.schema([pa.field(c, pa.string()) for c in cols])
    while True:
        params = {
            '$where': f"id > {int(info['ultimo_id'])} AND id <= {int(info['max_id_inicial'])}",
            '$order': 'id ASC',
            '$limit': TAMANO_LOTE,
        }
        filas = pedir(s, URL, params)
        if not filas:
            info['finalizado'] = True
            guardar_estado(info)
            print(f"COMPLETADO: {info['registros']:,} registros en {info['lotes']} archivos Parquet.")
            print(f'Ubicación: {PARTES}')
            break

        ids = [int(f['id']) for f in filas]
        if ids != sorted(ids) or ids[0] <= info['ultimo_id']:
            raise RuntimeError('La paginación devolvió IDs desordenados o repetidos.')

        datos = {c: [convertir_valor(f.get(c)) for f in filas] for c in cols}
        tabla = pa.Table.from_pydict(datos, schema=schema)
        numero = info['lotes'] + 1
        archivo = PARTES / f'parte_{numero:05d}.parquet'
        temporal = PARTES / f'parte_{numero:05d}.parquet.tmp'
        pq.write_table(tabla, temporal, compression='zstd')
        temporal.replace(archivo)

        info['ultimo_id'] = ids[-1]
        info['lotes'] = numero
        info['registros'] += len(filas)
        guardar_estado(info)
        print(f"Lote {numero:05d}: +{len(filas):,}; total {info['registros']:,}; último ID {ids[-1]}", flush=True)


if __name__ == '__main__':
    main()
