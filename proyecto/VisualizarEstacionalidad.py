"""Visualiza indices mensuales y CV anual en dos figuras con paneles por lugar.

python proyecto/VisualizarEstacionalidad.py --top 4 --columnas 2
python proyecto/VisualizarEstacionalidad.py --anios 2020 2023 2025 --lugares STREET RESIDENCE
Requiere matplotlib. Lee las salidas de EstacionalidadMensual.py sin Spark.
"""
import argparse
import ast
import hashlib
import math
from pathlib import Path
from textwrap import fill

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

CARPETA = Path(__file__).resolve().parent


def salida_automatica(lugares, anios, columnas, top=None, personalizados=False):
    """Identifica la selección y la distribución sin usar un nombre fijo."""
    if personalizados:
        # Distingue selecciones con igual cantidad de lugares, sin nombres largos
        # ni caracteres que no se pueden usar en archivos de Windows.
        firma = hashlib.sha256(repr(lugares).encode("utf-8")).hexdigest()[:10]
        seleccion = f"lugares{len(lugares)}-{firma}"
    elif top is not None:
        seleccion = f"top{len(lugares)}"
    else:
        seleccion = f"todos{len(lugares)}"

    # Un rango solo representa años consecutivos; 2020 y 2025 no es 2020-2025.
    rangos = []
    inicio = fin = anios[0]
    for anio in anios[1:]:
        if anio == fin + 1:
            fin = anio
        else:
            rangos.append(str(inicio) if inicio == fin else f"{inicio}-{fin}")
            inicio = fin = anio
    rangos.append(str(inicio) if inicio == fin else f"{inicio}-{fin}")
    nombre = (f"estacionalidad_{seleccion}_anios{'_'.join(rangos)}"
              f"_cols{min(columnas, len(lugares))}.png")
    return CARPETA / nombre


def leer_tuplas(ruta):
    with ruta.open(encoding="utf-8-sig") as archivo:
        for numero, linea in enumerate(archivo, 1):
            if not linea.strip():
                continue
            try:
                fila = ast.literal_eval(linea)
                if not isinstance(fila, tuple) or len(fila) != 10:
                    raise ValueError("se esperan tuplas de diez campos")
                yield fila
            except (SyntaxError, ValueError) as error:
                raise ValueError(f"{ruta}, línea {numero}: {error}") from error


def leer_datos(indices, cv):
    datos = {}
    for fila in leer_tuplas(indices):
        anio, mes, lugar = int(fila[0]), int(fila[1]), fila[2]
        if not 1 <= mes <= 12 or fila[5] <= 0 or not math.isfinite(fila[9]) or fila[9] < 0:
            raise ValueError(f"Índice inválido: {anio}, {mes}, {lugar}")
        grupo = datos.setdefault((anio, lugar), {"total": fila[5], "meses": {}})
        if mes in grupo["meses"] or grupo["total"] != fila[5]:
            raise ValueError(f"Mes duplicado o total inconsistente: {anio}, {lugar}")
        grupo["meses"][mes] = fila[9]
    resumen = {}
    for fila in leer_tuplas(cv):
        clave = (int(fila[0]), fila[1])
        if clave in resumen or fila[2] != 12 or fila[3] <= 0:
            raise ValueError(f"Resumen anual inválido o duplicado: {clave}")
        if any(not math.isfinite(fila[i]) or fila[i] < 0 for i in (6, 9)):
            raise ValueError(f"CV inválido: {clave}")
        resumen[clave] = fila
    if not datos or set(datos) != set(resumen):
        raise ValueError("Los archivos deben contener los mismos años y lugares y no estar vacíos.")
    for clave, grupo in datos.items():
        if set(grupo["meses"]) != set(range(1, 13)) or grupo["total"] != resumen[clave][3]:
            raise ValueError(f"Faltan meses o los totales difieren entre archivos: {clave}")
        grupo["cv"] = resumen[clave]
    return datos


def graficar(datos, lugares, anios, columnas, destino, modo, es_top, mostrar):
    import matplotlib
    if not mostrar:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator, PercentFormatter

    columnas = min(columnas, len(lugares))
    filas = math.ceil(len(lugares) / columnas)
    subtitulo = (f"Top {len(lugares)} lugares con más reportes acumulados en los años seleccionados"
                 if es_top else f"{len(lugares)} lugares seleccionados")
    subtitulo = fill(subtitulo, columnas * 45)
    nleyenda = min(len(anios), columnas * 3)
    cabecera = 1.4 + (0.25 * math.ceil(len(anios) / nleyenda) if modo == "indices" else 0.3)
    ancho, alto = columnas * 5.2, filas * 3.4 + cabecera + 1
    fig, ejes = plt.subplots(filas, columnas, figsize=(ancho, alto), squeeze=False)
    fig.subplots_adjust(left=0.65/ancho, right=1-0.25/ancho, bottom=1/alto,
                        top=1-cabecera/alto, hspace=0.65, wspace=0.3)
    colores = plt.get_cmap("tab20")
    estilos = {a: dict(color=colores(i % 20), linestyle=["-", "--", "-.", ":"][(i // 20) % 4])
               for i, a in enumerate(anios)}
    for ax, lugar in zip(ejes.flat, lugares):
        if modo == "indices":
            for anio in anios:
                if (anio, lugar) in datos:
                    ax.plot(range(1, 13), [datos[anio, lugar]["meses"][m] for m in range(1, 13)],
                            linewidth=1, marker="o", markersize=2, **estilos[anio])
            ax.axhline(100, color="black", linestyle=":", linewidth=1.2)
            ax.set_xticks(range(1, 13), MESES, rotation=45)
            ax.set_xlabel("Mes")
            ax.set_ylabel("Índice (base anual = 100)")
        else:
            for campo, color, estilo in [(9, "#0072B2", "-"), (6, "#D55E00", "--")]:
                valores = [datos[a, lugar]["cv"][campo] if (a, lugar) in datos else float("nan")
                           for a in anios]
                ax.plot(anios, valores, marker="o", markersize=3, color=color, linestyle=estilo)
            ax.set_xlabel("Año")
            ax.set_ylabel("CV mensual (%)")
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            if len(anios) == 1:
                ax.set_xticks(anios)
            ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        ax.set_title(fill(lugar, 42), fontsize=9, fontweight="bold")
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in list(ejes.flat)[len(lugares):]:
        ax.set_visible(False)
    titulo = "Índice mensual ajustado por días" if modo == "indices" else "Variación mensual por año y lugar"
    fig.suptitle(titulo, y=1-0.12/alto, fontsize=14)
    fig.text(0.5, 1-0.48/alto, subtitulo, ha="center", va="top", fontsize=10)
    if modo == "indices":
        presentes = [a for a in anios if any((a, l) in datos for l in lugares)]
        leyenda = [Line2D([], [], label=str(a), **estilos[a]) for a in presentes]
        nota = "Línea negra: 100 = tasa diaria anual. Índice 120 = 20 % sobre esa tasa."
    else:
        leyenda = [Line2D([], [], color="#0072B2", label="CV de tasas diarias"),
                   Line2D([], [], color="#D55E00", linestyle="--", label="CV de conteos")]
        nleyenda = 1 if columnas == 1 else 2
        nota = "CV poblacional de los 12 meses. El CV de tasas ajusta por duración del mes.\nUn CV alto indica dispersión; no demuestra por sí solo estacionalidad."
    fig.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, 1-1/alto),
               ncols=nleyenda, frameon=False, fontsize=8)
    nota = "\n".join(fill(linea, int(ancho * 15)) for linea in nota.splitlines())
    fig.text(0.5, 0.1/alto, nota, ha="center", va="bottom", fontsize=8)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=120)
    if mostrar:
        plt.show()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--indices", type=Path, default=CARPETA / "indices-mensuales.txt")
    parser.add_argument("--cv", type=Path, default=CARPETA / "cv-anual.txt")
    parser.add_argument("--anios", "--anio", nargs="+", type=int)
    parser.add_argument("--lugares", nargs="+", help="Nombres exactos; reemplaza --top.")
    parser.add_argument("--top", type=int, help="N lugares con más reportes acumulados; por defecto, todos.")
    parser.add_argument("--columnas", type=int, default=4)
    parser.add_argument("--salida", type=Path, help="Carpeta de destino; por defecto, junto al script.")
    parser.add_argument("--mostrar", action="store_true")
    args = parser.parse_args()
    if args.columnas < 1 or (args.top is not None and args.top < 1):
        parser.error("--columnas y --top deben ser positivos.")
    try:
        datos = leer_datos(args.indices, args.cv)
        disponibles = {a for a, _ in datos}
        anios = sorted(set(args.anios) if args.anios else disponibles)
        if set(anios) - disponibles:
            raise ValueError(f"Años sin datos: {sorted(set(anios) - disponibles)}")
        disponibles = {l for a, l in datos if a in anios}
        if args.lugares:
            lugares = list(dict.fromkeys(args.lugares))
            if set(lugares) - disponibles:
                raise ValueError(f"Lugares sin datos: {sorted(set(lugares) - disponibles)}")
        else:
            lugares = sorted(disponibles, key=lambda l: (
                -sum(datos[a, l]["total"] for a in anios if (a, l) in datos), l))[:args.top]
        base = salida_automatica(lugares, anios, args.columnas, args.top, bool(args.lugares)).name
        carpeta = args.salida or CARPETA
        for modo, prefijo in [("indices", "estacionalidad-indices"), ("cv", "estacionalidad-cv")]:
            destino = carpeta / base.replace("estacionalidad", prefijo, 1)
            print(f"Generando {modo}: {len(lugares)} paneles...", flush=True)
            graficar(datos, lugares, anios, args.columnas, destino, modo,
                     args.top is not None and not args.lugares, args.mostrar)
            print(f"Guardado: {destino.resolve()}", flush=True)
    except ImportError:
        parser.error("Instala matplotlib: python -m pip install matplotlib")
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
