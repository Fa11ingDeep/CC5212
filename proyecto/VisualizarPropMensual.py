"""Genera una imagen con un subgráfico por lugar y una línea por año.

Uso desde la raíz del repositorio:
    python proyecto/VisualizarPropMensual.py
    python proyecto/VisualizarPropMensual.py --anios 2020 2023 2025 --top 6
    python proyecto/VisualizarPropMensual.py --lugares STREET RESIDENCE APARTMENT

Dependencia: python -m pip install matplotlib
La proporción es mensual / total anual del MISMO lugar, no la participación
de ese lugar en el total de crímenes del mes. No requiere Spark ni internet.
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
    nombre = (f"prop-mensual-v1_{seleccion}_anios{'_'.join(rangos)}"
              f"_cols{min(columnas, len(lugares))}.png")
    return CARPETA / nombre


def leer_datos(ruta):
    """Lee tuplas de Spark sin ejecutar código y verifica sus denominadores."""
    datos = {}
    with ruta.open(encoding="utf-8-sig") as archivo:
        for numero, linea in enumerate(archivo, 1):
            if not linea.strip():
                continue
            try:
                anio, mes, lugar, conteo, total, proporcion = ast.literal_eval(linea)
                anio, mes = int(anio), int(mes)
                if not (1 <= mes <= 12 and isinstance(lugar, str) and lugar.strip()
                        and isinstance(conteo, int) and isinstance(total, int)
                        and 0 <= conteo <= total and total > 0
                        and math.isclose(proporcion, conteo / total, rel_tol=1e-9,
                                         abs_tol=1e-12)):
                    raise ValueError("valores o proporción inconsistentes")
                clave = (anio, lugar)
                grupo = datos.setdefault(clave, {"total": total, "meses": {}})
                if grupo["total"] != total or mes in grupo["meses"]:
                    raise ValueError("total anual inconsistente o mes duplicado")
                grupo["meses"][mes] = (conteo, proporcion)
            except (ValueError, SyntaxError, TypeError) as error:
                raise ValueError(f"{ruta}, línea {numero}: {error}") from error
    if not datos:
        raise ValueError("El archivo no contiene datos.")
    for (anio, lugar), grupo in datos.items():
        if sum(c for c, _ in grupo["meses"].values()) != grupo["total"]:
            raise ValueError(f"Los conteos mensuales no suman el total de {anio}, {lugar}.")
    return datos


def graficar(datos, lugares, anios, meses_por_anio, salida, columnas=4, mostrar=False,
             es_top=False):
    import matplotlib

    if not mostrar:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import PercentFormatter

    columnas = min(columnas, len(lugares))
    filas = math.ceil(len(lugares) / columnas)
    columnas_leyenda = min(len(anios), columnas * 3)
    subtitulo = ""
    if es_top:
        subtitulo = fill(
            f"Top {len(lugares)} lugares con más reportes acumulados en los años seleccionados",
            width=columnas * 42)
    margen_leyenda = 0.7 if columnas == 1 else 0.45
    if subtitulo:
        margen_leyenda += 0.25 * len(subtitulo.splitlines()) + 0.1
    alto_cabecera = margen_leyenda + 0.45 + 0.25 * math.ceil(len(anios) / columnas_leyenda)
    alto_pie = 1.2 if columnas == 1 else 1.0
    ancho, alto = columnas * 4.8, filas * 3.2 + alto_cabecera + alto_pie
    fig, ejes = plt.subplots(filas, columnas, figsize=(ancho, alto), squeeze=False)
    fig.subplots_adjust(left=0.6 / ancho, right=1 - 0.25 / ancho,
                        top=1 - alto_cabecera / alto, bottom=alto_pie / alto,
                        hspace=0.65, wspace=0.3)
    colores = plt.get_cmap("tab10" if len(anios) <= 10 else "tab20")
    estilos = {anio: {"color": colores(i % colores.N),
                      "linestyle": ["-", "--", "-.", ":"][(i // colores.N) % 4]}
               for i, anio in enumerate(anios)}
    presentes = [a for a in anios if any((a, lugar) in datos for lugar in lugares)]
    incompletos = [str(a) for a in presentes if len(meses_por_anio[a]) < 12]
    for ax, lugar in zip(ejes.flat, lugares):
        for anio in anios:
            # Un año sin datos para este lugar no representa una serie de ceros.
            if (anio, lugar) not in datos:
                continue
            grupo = datos[anio, lugar]
            # Spark omite meses sin reportes. Solo se completan con cero cuando
            # el mes está presente en el año; meses aún no observados quedan vacíos.
            valores = [grupo["meses"].get(mes, (0, 0.0))[1]
                       if mes in meses_por_anio[anio] else float("nan")
                       for mes in range(1, 13)]
            ax.plot(range(1, 13), valores, marker="o", markersize=2,
                    linewidth=1, **estilos[anio])

        ax.set_title(fill(lugar, width=42), fontsize=9, fontweight="bold", pad=8)
        ax.set_xlabel("Mes", fontsize=8)
        ax.set_ylabel("Proporción anual", fontsize=8)
        ax.set_xticks(range(1, 13), MESES, rotation=45)
        ax.tick_params(labelsize=7)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in list(ejes.flat)[len(lugares):]:
        ax.set_visible(False)

    titulo = "Proporción mensual por tipo de lugar"
    if columnas == 1:
        titulo = "Proporción mensual por tipo de lugar\n"
    fig.suptitle(titulo,
                 y=1 - 0.12 / alto, fontsize=12 if columnas == 1 else 17)
    if subtitulo:
        fig.text(0.5, 1 - 0.48 / alto, subtitulo, ha="center", va="top", fontsize=10)
    leyenda = [Line2D([], [], **estilos[a],
                      label=f"{a}" + (" (parcial)" if str(a) in incompletos else ""))
               for a in presentes]
    fig.legend(handles=leyenda, title="Año", loc="upper center",
               bbox_to_anchor=(0.5, 1 - margen_leyenda / alto), ncols=columnas_leyenda,
               frameon=False, fontsize=8, title_fontsize=9)
    nota = "Cada panel es un lugar; cada línea, un año. Proporción = reportes del mes / total anual del lugar."
    if incompletos:
        nota += (f"\nAños parciales: {', '.join(incompletos)}; "
                 "el denominador incluye solo los reportes disponibles.")
    nota = "\n".join(fill(linea, width=int(ancho * 16)) for linea in nota.splitlines())
    fig.text(0.5, 0.08 / alto, nota, ha="center", va="bottom", fontsize=8)
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=120)
    if mostrar:
        plt.show()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entrada", nargs="?", type=Path,
                        default=CARPETA / "prop-mensual-location-full.txt")
    parser.add_argument("--anios", "--anio", nargs="+", type=int,
                        help="Años a comparar; por defecto, todos los disponibles.")
    parser.add_argument("--top", type=int,
                        help="Limita a los N lugares con más reportes en los años seleccionados.")
    parser.add_argument("--lugares", nargs="+",
                        help="Nombres exactos de lugares; reemplaza --top. Usar comillas si tienen espacios.")
    parser.add_argument("--salida", type=Path,
                        help="Archivo PNG, PDF o SVG; por defecto, nombre automático según "
                             "lugares, años y columnas en la carpeta del script.")
    parser.add_argument("--columnas", type=int, default=4,
                        help="Columnas de la cuadrícula (por defecto: 4).")
    parser.add_argument("--mostrar", action="store_true", help="También abre la figura en una ventana.")
    args = parser.parse_args()
    if args.top is not None and args.top < 1:
        parser.error("--top debe ser mayor que cero.")
    if args.columnas < 1:
        parser.error("--columnas debe ser mayor que cero.")
    try:
        datos = leer_datos(args.entrada)
        meses_por_anio = {}
        for (anio, _), grupo in datos.items():
            meses_por_anio.setdefault(anio, set()).update(grupo["meses"])
        anios = sorted(set(args.anios) if args.anios else meses_por_anio)
        faltantes = set(anios) - set(meses_por_anio)
        if faltantes:
            raise ValueError(f"Años sin datos: {sorted(faltantes)}. "
                             f"Disponibles: {sorted(meses_por_anio)}")
        disponibles = {lugar for a, lugar in datos if a in anios}
        if args.lugares:
            lugares = list(dict.fromkeys(args.lugares))
            faltantes = set(lugares) - set(disponibles)
            if faltantes:
                raise ValueError("Lugares sin datos en los años seleccionados: "
                                 + ', '.join(sorted(faltantes)))
        else:
            lugares = sorted(disponibles,
                             key=lambda lugar: (-sum(datos[a, lugar]["total"] for a in anios
                                                     if (a, lugar) in datos), lugar))[:args.top]
        salida = args.salida or salida_automatica(
            lugares, anios, args.columnas, args.top, bool(args.lugares))
        print(f"Generando una figura con {len(lugares)} subgráficos...", flush=True)
        graficar(datos, lugares, anios, meses_por_anio, salida,
                 args.columnas, args.mostrar,
                 es_top=args.top is not None and not args.lugares)
    except ImportError:
        parser.error("Falta matplotlib. Instálalo con: python -m pip install matplotlib")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Imagen con {len(lugares)} subgráficos guardada en: {salida.resolve()}")
    print(f"Años comparados: {', '.join(map(str, anios))}")


if __name__ == "__main__":
    main()
