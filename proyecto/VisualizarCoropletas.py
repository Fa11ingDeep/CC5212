"""Coropletas hexagonales a partir de las salidas *_clas de Coropletas.py.

Solo dibuja: la escala de color (nivel, vmin, q3, vmax) ya viene calculada por
Coropletas.py, con nivel 0 = muy seguro (azul), 0.5 = Q3 (gris), 1 = muy peligroso (rojo).

Uso:
  python VisualizarCoropletas.py <dir_resultados> <dir_png> [--hex_m 500]
                                 [--mes YYYY-MM] [--tipo PRIMARY_TYPE]

<dir_resultados> puede tener la salida de Spark (una carpeta por dataset) o los
CSV ya descargados (coropletas_total_clas.csv, etc.).

Genera en <dir_png>:
  coropleta_total.png       crimenes por hexagono en toda la historia
  coropleta_mes.png         crimenes por hexagono en --mes
  mes_tipo_<mes>/<TIPO>.png un mapa por cada uno de los 12 tipos mas frecuentes en
                            --mes (o solo --tipo)
  coropleta_meses_<anio>.png  un mapa por mes de --anio, con escala comun
  coropleta_tipos_<mes>.png   los 12 tipos mas frecuentes en --mes, uno por mapa
  coropleta_anios.png         un mapa por anio (cada 2 anios, o --anios), escala comun

--hex_m debe ser el mismo radio usado al correr Coropletas.py.
Requiere pandas y matplotlib (solo para uso local, no en el cluster).
Con contextily instalado y conexion a internet se dibuja el mapa de la ciudad
(teselas Esri World Gray Canvas) bajo los hexagonos; sin el, se omite.
"""
import argparse
import glob
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize

NIVEL = Normalize(vmin=0.0, vmax=1.0)  # nivel ya viene en [0, 1] desde Spark

try:
    import contextily as ctx
except ImportError:
    ctx = None

# Misma proyeccion que Coropletas.py: si se cambia alla, cambiar aqui.
LAT0 = 41.84
LON0 = -87.68
R_TIERRA = 6371008.8
SQRT3 = math.sqrt(3.0)
M_POR_GRADO_LAT = R_TIERRA * math.pi / 180.0
M_POR_GRADO_LON = M_POR_GRADO_LAT * math.cos(math.radians(LAT0))

# Escala divergente: azul intenso = muy seguro (pocos crimenes), gris claro en el
# tercer cuartil (Q3) y rojo intenso = muy peligroso (muchos crimenes).
AZULES = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
NEUTRO = "#f4f2ee"
ROJOS = ["#f7c9c4", "#f0a39b", "#e57a70", "#d65046", "#b8322b", "#8f2420", "#6b1414"]
CMAP = LinearSegmentedColormap.from_list("seguro_peligroso", AZULES + [NEUTRO] + ROJOS)
SIN_DATOS = "#9a9a96"  # borde de las celdas sin crimenes
OPACIDAD = 0.85        # deja ver las calles bajo los hexagonos
R_MERCATOR = 6378137.0
TINTA = "#3a3a38"


def a_mercator(lon, lat):
    """(lon, lat) -> Web Mercator (EPSG:3857), la proyeccion de las teselas."""
    x = R_MERCATOR * math.radians(lon)
    y = R_MERCATOR * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
    return x, y


def hexagono(n_pleta, hex_m):
    """Vertices en Web Mercator del hexagono 'q_r' (pointy-top, radio hex_m)."""
    q, r = (int(v) for v in n_pleta.split("_"))
    cx = hex_m * (SQRT3 * q + SQRT3 / 2.0 * r)
    cy = hex_m * 1.5 * r
    vertices = []
    for i in range(6):
        ang = math.radians(60.0 * i - 30.0)
        x = cx + hex_m * math.cos(ang)
        y = cy + hex_m * math.sin(ang)
        vertices.append(a_mercator(LON0 + x / M_POR_GRADO_LON, LAT0 + y / M_POR_GRADO_LAT))
    return vertices


def leer(dir_resultados, nombre, filtro=None):
    """Lee un dataset (ya trae una fila por grupo). Acepta la carpeta que deja
    Spark (<nombre>/part-*.csv) o un CSV suelto (<nombre>.csv)."""
    partes = sorted(glob.glob(os.path.join(dir_resultados, nombre, "part-*.csv")))
    if not partes and os.path.isfile(os.path.join(dir_resultados, nombre + ".csv")):
        partes = [os.path.join(dir_resultados, nombre + ".csv")]
    if not partes:
        raise SystemExit("No se encontro %s/part-*.csv ni %s.csv en %s"
                         % (nombre, nombre, dir_resultados))
    trozos = []
    for p in partes:
        df = pd.read_csv(p, dtype={"date": str, "n_pleta": str, "primary_type": str})
        if filtro is not None:
            df = filtro(df)
        trozos.append(df)
    return pd.concat(trozos)


def fondo(ax):
    """Mapa de la ciudad bajo los hexagonos (si se puede)."""
    if ctx is None:
        print("  contextily no instalado: sin mapa de fondo")
        return False
    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldGrayCanvas, crs="EPSG:3857",
                        attribution_size=6, zorder=0)
        return True
    except Exception as e:  # sin internet, servidor de teselas caido, etc.
        print("  No se pudo descargar el mapa de fondo:", e)
        return False


def barra(fig, col, df, etiqueta, marcas=None, **kw):
    """Barra de color en `nivel`, con marcas en vmin (0), Q3 (0.5) y vmax (1).
    Si Q3 == vmin la escala no tiene mitad azul: la barra va de gris a rojo.
    Con `marcas` ({nivel: texto}) se usan esas en vez de las de `df`."""
    t0 = 0.0
    if marcas is None:
        vmin, q3, vmax = (float(df[c].iloc[0]) for c in ("vmin", "q3", "vmax"))
        t0 = 0.5 if q3 <= vmin else 0.0
        marcas = {1.0: "%d" % vmax, 0.5: "Q3 = %g" % q3}
        if t0 == 0.0:
            marcas[0.0] = "%d" % vmin
    cb = fig.colorbar(col, boundaries=np.linspace(t0, 1.0, 257), **kw)
    cb.set_ticks(sorted(marcas))
    cb.set_ticklabels([marcas[m] for m in sorted(marcas)])
    cb.set_label(etiqueta, color=TINTA)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=TINTA)
    return cb


def hexagonos_en(ax, nivel, todas, hex_m, borde=0.4):
    """Dibuja en `ax` las celdas `todas`: coloreadas segun `nivel` (dict n_pleta ->
    nivel) o sin relleno si no aparecen. Devuelve la coleccion coloreada."""
    vacias = [hexagono(c, hex_m) for c in todas if c not in nivel]
    llenas = [c for c in todas if c in nivel]
    ax.set_facecolor("white")
    if vacias:
        ax.add_collection(PolyCollection(vacias, facecolors="none", edgecolors=SIN_DATOS,
                                         linewidths=borde, zorder=1))
    col = PolyCollection([hexagono(c, hex_m) for c in llenas], array=[nivel[c] for c in llenas],
                         cmap=CMAP, norm=NIVEL, alpha=OPACIDAD,
                         edgecolors="white", linewidths=borde, zorder=2)
    ax.add_collection(col)
    ax.autoscale_view()
    ax.set_aspect("equal")
    fondo(ax)
    ax.set_axis_off()
    return col


def etiqueta_escala(referencia):
    return ("Crimenes por hexagono (log; azul = seguro, rojo = peligroso)\n"
            "Escala fija: Q3 y maximo de " + referencia)


def dibujar(df, todas, hex_m, titulo, salida, referencia):
    """df: filas de un mapa {n_pleta, freq, nivel, vmin, q3, vmax}."""
    nivel = dict(zip(df["n_pleta"], df["nivel"]))
    vacias = [c for c in todas if c not in nivel]

    fig, ax = plt.subplots(figsize=(8, 10), facecolor="white")
    col = hexagonos_en(ax, nivel, todas, hex_m)
    ax.set_title(titulo, color=TINTA, fontsize=13, loc="left")
    barra(fig, col, df, etiqueta_escala(referencia), ax=ax, shrink=0.6, pad=0.02)
    ax.text(0, -0.02, "{:,} crimenes en {:,} hexagonos de {:g} m de radio".format(
                int(df["freq"].sum()), len(nivel), hex_m).replace(",", ".")
            + ("  |  sin relleno = 0" if vacias else ""),
            transform=ax.transAxes, color=TINTA, fontsize=9)

    fig.savefig(salida, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Guardado", salida)


MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def dibujar_grilla(paneles, titulo, todas, hex_m, salida, etiqueta, pie, marcas=None):
    """Grilla 3x4 de mapas. paneles: lista de hasta 12 (titulo, df); un df vacio
    deja el panel como "sin datos". La barra usa las marcas del primer panel con
    datos, o `marcas` si se entrega (cuando cada panel tiene su propia escala)."""
    fig, axes = plt.subplots(3, 4, figsize=(16, 15), facecolor="white")
    col, ref = None, None
    for ax, (titulo_panel, d) in zip(axes.flat, paneles + [("", None)] * 12):
        if d is None:  # sobran paneles
            ax.set_axis_off()
            continue
        if d.empty:
            ax.set_axis_off()
            ax.set_title(titulo_panel + ": sin datos", color=TINTA, fontsize=11, loc="left")
            continue
        col = hexagonos_en(ax, dict(zip(d["n_pleta"], d["nivel"])), todas, hex_m, borde=0.2)
        ref = d if ref is None else ref
        ax.set_title(titulo_panel, color=TINTA, fontsize=11, loc="left")

    fig.suptitle(titulo, color=TINTA, fontsize=16, x=0.02, ha="left")
    fig.subplots_adjust(left=0.01, right=0.87, top=0.94, bottom=0.03, wspace=0.02, hspace=0.1)
    cax = fig.add_axes([0.89, 0.3, 0.012, 0.4])
    barra(fig, col, ref, etiqueta, marcas=marcas, cax=cax)
    fig.text(0.01, 0.01, "Hexagonos de {:g} m de radio  |  sin relleno = 0  |  ".format(hex_m)
             + pie, color=TINTA, fontsize=9)

    fig.savefig(salida, dpi=120)
    plt.close(fig)
    print("Guardado", salida)


def miles(n):
    return "{:,}".format(int(n)).replace(",", ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir_resultados")
    ap.add_argument("dir_png")
    ap.add_argument("--hex_m", type=float, default=500.0)
    ap.add_argument("--mes", help="YYYY-MM (por defecto, el ultimo mes con datos)")
    ap.add_argument("--tipo", help="un solo PRIMARY_TYPE (por defecto, los 12 mas frecuentes del mes)")
    ap.add_argument("--anio", help="YYYY para la grilla mensual (por defecto, el ultimo "
                                   "anio con los 12 meses)")
    ap.add_argument("--anios", help="hasta 12 anios separados por coma para la grilla anual "
                                    "(por defecto, cada 2 anios hasta el ultimo completo)")
    a = ap.parse_args()
    os.makedirs(a.dir_png, exist_ok=True)

    total = leer(a.dir_resultados, "coropletas_total_clas")
    todas = sorted(total["n_pleta"])
    dibujar(total, todas, a.hex_m, "Crimenes en Chicago, toda la historia",
            os.path.join(a.dir_png, "coropleta_total.png"), "toda la historia")

    sec = leer(a.dir_resultados, "coropletas_secuencia_clas")
    meses = sorted(sec["date"].unique())
    ref_mes = "todos los meses (%s a %s)" % (meses[0], meses[-1])

    anio = a.anio
    if anio is None:
        # Ultimo anio con los 12 meses (Coropletas.py ya descarta el anio en curso).
        completos = [y for y in sorted({m[:4] for m in meses})
                     if sum(m.startswith(y) for m in meses) == 12]
        anio = completos[-1]
    sec_anio = sec[sec["date"].str.startswith(anio + "-")]
    if sec_anio.empty:
        raise SystemExit("No hay datos para el anio " + anio)
    paneles = []
    for i, nombre_mes in enumerate(MESES):
        d = sec_anio[sec_anio["date"] == "%s-%02d" % (anio, i + 1)]
        paneles.append(("%s  (%s)" % (nombre_mes, miles(d["freq"].sum())), d))
    dibujar_grilla(paneles, "Crimenes en Chicago por mes, %s" % anio, todas, a.hex_m,
                   os.path.join(a.dir_png, "coropleta_meses_%s.png" % anio),
                   etiqueta_escala(ref_mes), "entre parentesis: total del mes")

    # Grilla anual (solo si la salida de Coropletas.py la incluye).
    try:
        anual = leer(a.dir_resultados, "coropletas_anual_clas")
    except SystemExit:
        anual = None
        print("Sin coropletas_anual_clas: no se dibuja la grilla por anio")
    if anual is not None:
        anual["anio"] = anual["anio"].astype(str)
        disponibles = sorted(anual["anio"].unique())
        elegidos = a.anios.split(",") if a.anios else disponibles[::-2][:12][::-1]
        paneles = [("%s  (%s)" % (y, miles(anual[anual["anio"] == y]["freq"].sum())),
                    anual[anual["anio"] == y]) for y in elegidos[:12]]
        dibujar_grilla(paneles, "Crimenes en Chicago por anio", todas, a.hex_m,
                       os.path.join(a.dir_png, "coropleta_anios.png"),
                       etiqueta_escala("todos los anios completos (%s a %s)"
                                       % (disponibles[0], disponibles[-1])),
                       "entre parentesis: total del anio")

    mes = a.mes
    if mes is None:
        # Coropletas.py solo deja meses completos (sin 2026).
        mes = meses[-1]
    sec_mes = sec[sec["date"] == mes]
    if sec_mes.empty:
        raise SystemExit("No hay datos para el mes " + mes)
    dibujar(sec_mes, todas, a.hex_m, "Crimenes en Chicago, " + mes,
            os.path.join(a.dir_png, "coropleta_mes.png"), ref_mes)

    # Los 12 tipos con mas crimenes en el mes: se usan en la grilla y en los mapas
    # individuales. La escala de cada tipo viene de Spark.
    st = leer(a.dir_resultados, "coropletas_secuencia_tipo_clas")
    por_tipo = st[st["date"] == mes].groupby("primary_type")
    top = list(por_tipo["freq"].sum().sort_values(ascending=False).index[:12])

    paneles = [("%s  (%s, Q3 = %g)" % (t.title(), miles(por_tipo.get_group(t)["freq"].sum()),
                                       por_tipo.get_group(t)["q3"].iloc[0]),
                por_tipo.get_group(t)) for t in top]
    dibujar_grilla(paneles, "Tipos de crimen en Chicago, %s (los 12 mas frecuentes)" % mes,
                   todas, a.hex_m, os.path.join(a.dir_png, "coropleta_tipos_%s.png" % mes),
                   "Crimenes por hexagono, relativo a cada tipo (log)\n"
                   "Escala fija de cada tipo: Q3 y maximo de todos sus meses",
                   "entre parentesis: total del mes y Q3 del tipo",
                   marcas={0.0: "minimo\ndel tipo", 0.5: "Q3\ndel tipo", 1.0: "maximo\ndel tipo"})

    # Un mapa por tipo: los mismos 12, o solo --tipo.
    tipos = top
    if a.tipo:
        tipos = [a.tipo.upper()]
        if tipos[0] not in set(st["primary_type"]):
            raise SystemExit("No existe el tipo %s" % tipos[0])
        if tipos[0] not in por_tipo.groups:
            raise SystemExit("Sin crimenes de %s en %s" % (tipos[0], mes))
    dir_tipos = os.path.join(a.dir_png, "mes_tipo_" + mes)
    os.makedirs(dir_tipos, exist_ok=True)
    for tipo in tipos:
        archivo = re.sub(r"[^A-Za-z0-9]+", "_", tipo).strip("_") + ".png"
        dibujar(por_tipo.get_group(tipo), todas, a.hex_m, "%s en Chicago, %s" % (tipo, mes),
                os.path.join(dir_tipos, archivo), "%s, todos los meses" % tipo)


if __name__ == "__main__":
    main()
