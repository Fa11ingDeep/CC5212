import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

W, H = 16, 9
BOX_W, BOX_H = 2.7, 1.25
NORMAL = dict(fc="#ececff", ec="#9370db")
CACHE = dict(fc="#cde2fb", ec="#256abf")
SALIDA = dict(fc="#e9f7ec", ec="#3c9a54")


def dibujar(nodos, aristas, salida, titulo):
    fig, ax = plt.subplots(figsize=(W, H), dpi=200)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    caja = {}
    for k, (x, y, texto, estilo, *tam) in nodos.items():
        w, h = tam if tam else (BOX_W, BOX_H)
        caja[k] = (x, y, w, h)
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    lw=1.4, **estilo, zorder=2))
        ax.text(x, y, texto, ha="center", va="center", fontsize=10.5, zorder=3,
                linespacing=1.35)

    def borde(k, desde, hacia):
        # punto donde la recta desde->hacia sale de la caja k (desde esta dentro de k)
        x, y, w, h = caja[k]
        dx, dy = hacia[0] - desde[0], hacia[1] - desde[1]
        tx = ((x + w / 2 + 0.07 if dx > 0 else x - w / 2 - 0.07) - desde[0]) / dx if dx else 1e9
        ty = ((y + h / 2 + 0.07 if dy > 0 else y - h / 2 - 0.07) - desde[1]) / dy if dy else 1e9
        t = min(tx, ty)
        return desde[0] + dx * t, desde[1] + dy * t

    # arista: (origen, destino, etiqueta, curva, desplazamiento x del ancla en origen, en destino)
    for a, b, etiqueta, curva, ox, oxb in aristas:
        pa = (caja[a][0] + ox, caja[a][1])
        pb = (caja[b][0] + oxb, caja[b][1])
        p1, p2 = borde(a, pa, pb), borde(b, pb, pa)
        ax.annotate("", xy=p2, xytext=p1, zorder=1,
                    arrowprops=dict(arrowstyle="-|>", lw=1.3, color="#333",
                                    linestyle=(0, (3, 2)) if etiqueta else "-",
                                    mutation_scale=14,
                                    connectionstyle=f"arc3,rad={curva}"))
        if etiqueta:
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            largo = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
            if largo < 1.3:
                # flecha corta: la etiqueta va encima para no taparla
                if abs(p2[1] - p1[1]) < 0.1:
                    my += 0.2
                else:
                    mx -= 0.55
            ax.text(mx, my, etiqueta, ha="center", va="center", fontsize=9,
                    color="#555", zorder=4,
                    bbox=dict(fc="#f2f2f2", ec="none", pad=1.5))

    ax.text(0.25, H - 0.25, titulo, fontsize=15, weight="bold", va="top")
    ley = [("transformacion (misma etapa)", "-"), ("shuffle (nueva etapa)", (0, (3, 2)))]
    for i, (t, ls) in enumerate(ley):
        y = 0.25 + i * 0.32
        ax.plot([W - 4.0, W - 3.4], [y, y], color="#333", lw=1.3, linestyle=ls)
        ax.text(W - 3.3, y, t, fontsize=9, va="center")
    fig.savefig(salida, bbox_inches="tight", pad_inches=0.15, facecolor="white")


def e(a, b, etiqueta=None, curva=0, ox=0, oxb=0):
    return (a, b, etiqueta, curva, ox, oxb)


S = "shuffle"

# ---------------- Coropletas ----------------
nodos = {
    "A": (1.6, 7.5, "spark.read.parquet\ndate, primary_type,\nlatitude, longitude", NORMAL),
    "B": (1.6, 5.6, "select + where\ndentro de Chicago,\nfecha < 2026", NORMAL),
    "C": (1.6, 3.7, "select date,\nprimary_type, n_pleta\n(celda hexagonal)", NORMAL),
    "T": (1.6, 1.4, "groupBy date,\nprimary_type, n_pleta\n$\\bf{por\\_tipo}$ (cache, 2,2 M)", CACHE, 2.7, 1.5),
    "M": (6.2, 1.4, "groupBy date, n_pleta: sum\n$\\bf{por\\_mes}$ (cache, 266 mil)", CACHE, 2.9, 1.25),
    "AN": (10.2, 1.4, "withColumn anio", NORMAL, 2.0, 0.8),
    "AA": (14.3, 1.4, "groupBy anio,\nn_pleta: sum", NORMAL, 2.6, 1.0),
    "WA": (14.3, 7.5, "Window (una particion)\nvmin, q3, vmax, nivel\n$\\bf{coropletas\\_anual\\_clas}$", SALIDA, 2.9, 1.25),
    "WT": (4.95, 4.75, "Window por primary_type\nvmin, q3, vmax, nivel\n$\\bf{coropletas\\_secuencia\\_tipo\\_clas}$", SALIDA, 3.2, 1.25),
    "WM": (10.1, 4.75, "Window (una particion)\nvmin, q3, vmax, nivel\n$\\bf{coropletas\\_secuencia\\_clas}$", SALIDA, 2.9, 1.25),
    "TO": (7.5, 7.5, "groupBy n_pleta: sum", NORMAL, 2.3, 0.8),
    "WTO": (10.9, 7.5, "Window (una particion)\nvmin, q3, vmax, nivel\n$\\bf{coropletas\\_total\\_clas}$", SALIDA, 2.9, 1.25),
}
aristas = [
    e("A", "B"), e("B", "C"), e("C", "T", S),
    e("T", "M", S), e("M", "AN"), e("AN", "AA", S),
    e("AA", "WA", S),
    e("T", "WT", S, ox=0.7, oxb=-0.6),
    e("M", "WM", S, ox=1.2, oxb=-0.6),
    e("M", "TO", S, ox=1.15, oxb=0),
    e("TO", "WTO", S),
]
dibujar(nodos, aristas, sys.argv[1] + "/dag_coropletas.png", "Coropletas.py")

# ---------------- PropMensual ----------------
nodos = {
    "A": (1.6, 7.5, "spark.read.parquet\nid, date, primary_type,\nlocation_description", NORMAL),
    "R": (1.6, 4.5, ".rdd", NORMAL, 1.4, 0.7),
    "C": (1.6, 1.5, "filter: fecha y\nlugar validos\n$\\bf{cleanLines}$ (cache)", CACHE),
    "D": (4.75, 1.5, "map:\n((anio, mes, lugar), 1)", NORMAL),
    "F": (7.9, 1.5, "reduceByKey\ncrimenes por\nanio, mes y lugar", NORMAL),
    "H": (11.05, 1.5, "map:\n((anio, lugar),\n(mes, conteo))", NORMAL),
    "E": (4.75, 4.5, "map:\n((anio, lugar), 1)", NORMAL),
    "G": (7.9, 4.5, "reduceByKey\ncrimenes por\nanio y lugar", NORMAL),
    "I": (14.3, 1.5, "join por\n(anio, lugar)", NORMAL, 2.6, 1.25),
    "J": (14.3, 4.5, "map: (anio, mes, lugar,\nconteo, total,\nproporcion)", NORMAL, 2.8, 1.25),
    "K": (14.3, 7.5, "saveAsTextFile", SALIDA, 2.4, 0.8),
}
aristas = [
    e("A", "R"), e("R", "C"), e("C", "D"), e("D", "F", S),
    e("F", "H"), e("H", "I", S),
    e("C", "E"), e("E", "G", S), e("G", "I", S),
    e("I", "J"), e("J", "K"),
]
dibujar(nodos, aristas, sys.argv[1] + "/dag_propmensual.png", "PropMensual.py")
