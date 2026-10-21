"""Genera docs/taller/img/architecture.png (diagrama de arquitectura de SkillPath).

Uso: .venv/bin/python docs/taller/img/architecture.py
Solo matplotlib; las etiquetas coinciden con el codigo de skillpath/ y app/.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).with_name("architecture.png")

W, H = 8.0, 12.9          # pulgadas; se imprime a ~16 cm de ancho (x0.79)
FS = 11.5                 # cuerpo (~9 pt impreso)
FS_T = 12.0               # titulos de caja
LH = 0.178                # alto de linea (pulgadas)
PAD = 0.07

# Colores (borde, relleno)
GRAY = ("#5b6770", "#f1f3f5")
PROC = ("#5b6770", "#ffffff")
BLUE = ("#1f5fa8", "#dbe9f8")      # estrategia basada en contenido
ORANGE = ("#b85c00", "#fde8cc")    # estrategia basada en conocimiento
HYB = ("#4b3a8f", "#e9e4f7")       # combinacion hibrida
OUTC = ("#2d7a4f", "#dff1e6")      # presentacion
FREEZE = ("#8a1c3a", "#f9e1e8")    # arranque en frio

fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.canvas.draw()
rend = fig.canvas.get_renderer()
FONT = "Helvetica"


def text_w(s, fs, bold=False):
    t = ax.text(0, 0, s, fontsize=fs, fontfamily=FONT, fontweight="bold" if bold else "normal")
    w = t.get_window_extent(rend).width / fig.dpi
    t.remove()
    return w


def wrap(s, width, fs, bold=False):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if text_w(trial, fs, bold) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


class Box:
    def __init__(self, x, w, title, body, color, h=None):
        self.x, self.w, self.color = x, w, color
        inner = w - 2 * PAD
        self.tl = wrap(title, inner, FS_T, True)
        self.bl = wrap(body, inner, FS) if body else []
        self.need = 2 * PAD + (len(self.tl) + len(self.bl)) * LH + 0.04
        self.h = h or self.need
        self.top = self.bot = None

    def place(self, top, h):
        self.top, self.h = top, h
        self.bot = top - h

    def draw(self):
        ec, fc = self.color
        ax.add_patch(FancyBboxPatch((self.x, self.bot), self.w, self.h,
                                    boxstyle="round,pad=0,rounding_size=0.06",
                                    ec=ec, fc=fc, lw=1.6, zorder=2))
        y = self.top - PAD - 0.01
        for ln in self.tl:
            ax.text(self.x + PAD, y, ln, fontsize=FS_T, fontweight="bold", color=ec,
                    fontfamily=FONT, va="top", zorder=3)
            y -= LH
        for ln in self.bl:
            ax.text(self.x + PAD, y, ln, fontsize=FS, color="#1d1d1f",
                    fontfamily=FONT, va="top", zorder=3)
            y -= LH

    @property
    def cx(self):
        return self.x + self.w / 2


def row(boxes, top):
    h = max(b.need for b in boxes)
    for b in boxes:
        b.place(top, h)
        b.draw()
    return top - h


def arrow(p0, p1, color="#333333", ls="-", lw=1.8, rad=0.0, z=1):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=14, lw=lw,
                                 color=color, linestyle=ls, shrinkA=0, shrinkB=0,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z))


def line(pts, color, lw=1.8, ls="-", z=1):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def label(x, y, s, color="#333333", ha="center", fs=FS - 0.5, bold=False):
    ax.text(x, y, s, fontsize=fs, color=color, ha=ha, va="center", fontfamily=FONT,
            fontweight="bold" if bold else "normal", zorder=6,
            bbox=dict(fc="white", ec="none", pad=1.2))


def vheading(ytop, ybot, s):
    ax.text(0.16, (ytop + ybot) / 2, s, fontsize=FS_T + 0.5, fontweight="bold", color="#33393f",
            fontfamily=FONT, va="center", ha="center", rotation=90)


def heading(y, s):
    ax.text(0.08, y, s, fontsize=FS_T + 0.5, fontweight="bold", color="#33393f",
            fontfamily=FONT, va="center")


# ------------------------------------------------------------------ geometry
M = 0.36
RM = 0.34                         # margen derecho para la flecha del Catalog
G = 0.14
CW = (W - M - RM - 3 * G) / 4
cx = [M + i * (CW + G) for i in range(4)]
CATX = W - 0.17                   # x de la flecha lateral

# ---------------------------------------------------------------- title
ax.text(W / 2, H - 0.22, "SkillPath — Arquitectura del sistema recomendador", fontsize=15.5,
        fontweight="bold", ha="center", va="center", fontfamily=FONT, color="#1d1d1f")

# ------------------------------------------------------------------ layer 1
y = H - 0.62
heading(y, "1. Fuentes de datos")
y -= 0.30
s1 = [
    Box(cx[0], CW, "asaniczka (Kaggle)",
        "Ofertas de LinkedIn de Data Analyst, Software Engineer y Data Scientist; niveles "
        "Associate y Mid senior; columna de habilidades", GRAY),
    Box(cx[1], CW, "arshkon (LinkedIn 2023–2024)",
        "Ofertas solo de nivel inicial (Entry e Internship); sin habilidades técnicas: "
        "están en el texto", GRAY),
    Box(cx[2], CW, "Catalog curado a mano",
        "64 habilidades con categoría, descripción, Difficulty (1–5) y Prerequisites", GRAY),
    Box(cx[3], CW, "Formulario del usuario",
        "Role objetivo, habilidades que ya tiene con su nivel de dominio, intereses y "
        "experiencia", GRAY),
]
y1 = row(s1, y)

# ------------------------------------------------------------------ layer 2
GAP = 0.34
y2top = y1 - GAP + 0.04
s2 = [
    Box(cx[0], CW, "Frequency por Role",
        "Normaliza habilidades (alias, exclusiones) y calcula el % de ofertas del Role que "
        "las mencionan", PROC),
    Box(cx[1], CW, "Frequency de nivel inicial",
        "Detecta las habilidades del Catalog en la descripción (diccionario) y las calibra "
        "contra asaniczka", PROC),
    Box(cx[2], CW, "Co-ocurrencia por Role",
        "Cercanía entre habilidades del Catalog que aparecen juntas en las ofertas de "
        "asaniczka", PROC),
    Box(cx[3], CW, "Perfil del usuario",
        "Learner profile: Role, habilidades con Mastery level, intereses, experiencia", PROC),
]
y2 = row(s2, y2top)
arrow((s1[0].cx, y1), (s2[0].cx, y2top), "#333333")
arrow((s1[1].cx, y1), (s2[1].cx, y2top), "#333333")
arrow((s1[2].cx, y1), (s2[2].cx, y2top), "#333333")
arrow((s1[3].cx, y1), (s2[3].cx, y2top), "#333333")

# layer 3 (inside layer 2 band)
y3top = y2 - 0.30
s3 = [
    Box(cx[0], 2 * CW + G, "Frequency usada por habilidad",
        "Con experiencia: la del Role. Nivel inicial: mezcla w·inicial + (1−w)·base, "
        "con w = n/(n+100)", PROC),
    Box(cx[2], CW, "TF-IDF por habilidad",
        "Documento = nombre + categoría + descripción + 8 vecinas por co-ocurrencia", PROC),
    Box(cx[3], CW, "Arranque en frío",
        "Formulario corto: solo el Role es obligatorio. Perfil vacío: similitud 0", FREEZE),
]
y3 = row(s3, y3top)
# arrows layer2 -> layer3
arrow((s2[0].cx, y2), (cx[0] + CW / 2, y3top), "#333333")
arrow((s2[1].cx, y2), (cx[1] + CW / 2, y3top), "#333333")
arrow((s2[2].cx, y2), (s3[1].cx, y3top), "#333333")
arrow((s2[3].cx, y2), (s3[2].cx, y3top), "#333333")

vheading(y2top, y3, "2. Procesamiento y representación")

# ---------------------------------------------------------------- engine group
ey_top = y3 - 0.62

inner_m = 0.12
ex0, ex1 = M, W - RM
inner_w = ex1 - ex0 - 2 * inner_m
half = (inner_w - 0.2) / 2

k = Box(ex0 + inner_m, half, "Basada en conocimiento",
        "Mastery level: lo dominado (intermedio o avanzado) se excluye. Prerequisites que "
        "faltan y Difficulty dan el Effort = Difficulty + faltantes", ORANGE)
c = Box(ex0 + inner_m + half + 0.2, half, "Basada en contenido",
        "Similitud del coseno (TF-IDF) entre el perfil (habilidades conocidas según su "
        "dominio + intereses) y cada habilidad candidata", BLUE)
strat_top = ey_top - 0.12
strat_bot = row([k, c], strat_top)

pr = Box(ex0 + inner_m, inner_w, "Prioridad = Frequency × (1 + similitud) / Effort",
         "Combinación de ambas estrategias: la demanda del mercado sube la prioridad; "
         "el Effort la baja y la similitud la aumenta hasta el doble", HYB)
pr_top = strat_bot - 0.40
pr_bot = row([pr], pr_top)
od = Box(ex0 + inner_m, inner_w, "Orden final de la ruta",
         "Desempate por Frequency y nombre; ajuste que coloca cada habilidad después de "
         "todos sus Prerequisites faltantes", HYB)
od_top = pr_bot - 0.34
od_bot = row([od], od_top)

arrow((k.cx, strat_bot), (k.cx, pr_top), ORANGE[0], lw=2.2)
arrow((c.cx, strat_bot), (c.cx, pr_top), BLUE[0], lw=2.2)
arrow((pr.cx, pr_bot), (pr.cx, od_top), HYB[0], lw=2.2)

ey_bot = od_bot - 0.12
vheading(ey_top, ey_bot, "3. Motor de recomendación híbrido")
ax.add_patch(FancyBboxPatch((ex0, ey_bot), ex1 - ex0, ey_top - ey_bot,
                            boxstyle="round,pad=0,rounding_size=0.1", ec="#4b3a8f",
                            fc="#f7f5fc", lw=1.8, ls=(0, (6, 3)), zorder=0))

# arrows into the engine
arrow((s3[0].cx, y3), (s3[0].cx, ey_top), "#333333", lw=2)
label(s3[0].cx, (y3 + ey_top) / 2, "Frequency (popularidad)")
arrow((s3[1].cx, y3), (s3[1].cx, ey_top), BLUE[0], lw=2.2)
label(s3[1].cx, (y3 + ey_top) / 2, "vectores", color=BLUE[0])
arrow((s3[2].cx, y3), (s3[2].cx, ey_top), FREEZE[0], lw=2.2)
label(s3[2].cx, (y3 + ey_top) / 2, "perfil", color=FREEZE[0])

# Catalog -> engine along the right margin (Difficulty, Prerequisites)
ycat = s1[2].top + 0.13
yend = ey_top - 0.32
line([(s1[2].cx, s1[2].top), (s1[2].cx, ycat), (CATX, ycat), (CATX, yend)], ORANGE[0], lw=2.2)
arrow((CATX, yend), (ex1, yend), ORANGE[0], lw=2.2)
ax.text(CATX, (ycat + yend) / 2, "Difficulty y Prerequisites", rotation=90, fontsize=FS - 0.5,
        color=ORANGE[0], ha="center", va="center", fontfamily=FONT, zorder=6,
        bbox=dict(fc="white", ec="none", pad=1.2))

# ---------------------------------------------------------------- presentation
pt = ey_bot - 0.62
heading(pt + 0.32, "4. Presentación: app Streamlit")
pw = (ex1 - ex0 - 2 * 0.14) / 3
p1 = Box(ex0, pw, "Ruta de aprendizaje",
         "Learning path ordenado, con la explicación de cada habilidad", OUTC)
p2 = Box(ex0 + pw + 0.14, pw, "Brecha de habilidades",
         "Skill gap: lo que el Role pide y aún no dominas", OUTC)
p3 = Box(ex0 + 2 * (pw + 0.14), pw, "Más frecuentes del Role",
         "Lista por Frequency pura (útil con perfil vacío)", OUTC)
pb = row([p1, p2, p3], pt)
arrow((W / 2 - 0.0, ey_bot), (W / 2, pt), HYB[0], lw=2.4)

# ---------------------------------------------------------------- legend
ly = pb - 0.32
items = [
    (BLUE, "Estrategia basada en contenido"),
    (ORANGE, "Estrategia basada en conocimiento"),
    (HYB, "Combinación híbrida"),
    (FREEZE, "Arranque en frío"),
    (GRAY, "Frequency = popularidad en las ofertas (factor de prioridad)"),
]
ax.text(0.08, ly, "Leyenda", fontsize=FS, fontweight="bold", va="center", fontfamily=FONT)
pos = [(1.0, ly), (4.0, ly), (1.0, ly - 0.3), (4.0, ly - 0.3), (1.0, ly - 0.6)]
for ((ec, fc), s_), (lx, yy) in zip(items, pos):
    ax.add_patch(FancyBboxPatch((lx, yy - 0.08), 0.24, 0.16, boxstyle="round,pad=0,rounding_size=0.03",
                                ec=ec, fc=fc, lw=1.4))
    ax.text(lx + 0.32, yy, s_, fontsize=FS - 0.5, va="center", fontfamily=FONT)
ax.plot([0, 0], [ly - 0.45, ly - 0.45], alpha=0)
LEG_BOTTOM = ly - 0.78

ax.set_ylim(LEG_BOTTOM, H)
fig.set_size_inches(W, H - LEG_BOTTOM)
fig.savefig(OUT, dpi=400)
print("saved", OUT, "bottom y", ly)
