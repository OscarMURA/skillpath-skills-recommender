"""Genera docs/taller/documento_final.docx a partir de documento_final.md.

Uso: .venv/bin/python docs/taller/build_docx.py
Requiere (solo en el venv, no en pyproject.toml): pypandoc_binary, python-docx.
"""
import re
import subprocess
import sys
from pathlib import Path

import pypandoc
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = Path(__file__).resolve().parent
MD = AQUI / "documento_final.md"
SALIDA = AQUI / "documento_final.docx"
TMP = AQUI / "_tmp_pandoc.docx"
FUENTE = "Calibri"
MONO = "Menlo"
# Tamaño (ancho, alto) en cm de cada imagen; la arquitectura es muy alta y se limita por altura.
TAMANOS = {
    "architecture.png": (11.5, 18.7),
    "app-data-analyst.png": (15.0, None),
    "app-data-scientist.png": (15.0, None),
    "app-software-engineer.png": (15.0, None),
}


def preparar_markdown():
    """Separa portada y cuerpo; fija el tamaño de las imágenes."""
    lineas = MD.read_text(encoding="utf-8").split("\n")
    idx = next(i for i, l in enumerate(lineas) if l.startswith("# PARTE 1"))
    portada = lineas[:idx]
    cuerpo = lineas[idx:]
    # primer párrafo "Este objetivo es el hilo conductor..." va al cuerpo (tras el TOC)
    texto = "\n".join(cuerpo)
    # el cuadro del objetivo se quita del cuerpo: vive en la portada
    texto_md = "\n".join(l for l in portada)
    objetivo = re.search(r"> \*\*Objetivo del sistema\.\*\*(.*)", texto_md).group(1).strip()

    def tam(m):
        alt, ruta = m.group(1), m.group(2)
        ancho, alto = TAMANOS[Path(ruta).name]
        attr = f"width={ancho}cm" if alto is None else f"height={alto}cm"
        return f"![{alt}]({ruta}){{{attr}}}"

    texto = re.sub(r"!\[(.*?)\]\((.*?)\)", tam, texto)
    return portada, objetivo, texto


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def bordes_tabla(tabla, color="808080", sz="4"):
    tblPr = tabla._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        b.append(e)
    tblPr.append(b)


def borde_parrafo(p, lado="left", color="1F4E79", sz="24", fondo=None):
    pPr = p._p.get_or_add_pPr()
    pb = OxmlElement("w:pBdr")
    for l in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{l}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz if l == lado else "4")
        e.set(qn("w:space"), "8")
        e.set(qn("w:color"), color)
        pb.append(e)
    pPr.append(pb)
    if fondo:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fondo)
        pPr.append(shd)


def fuente_estilo(est, nombre=FUENTE, size=None, bold=None, color=None, italic=None):
    est.font.name = nombre
    rpr = est.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), nombre)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    if size:
        est.font.size = Pt(size)
    if bold is not None:
        est.font.bold = bold
    if italic is not None:
        est.font.italic = italic
    if color:
        est.font.color.rgb = RGBColor.from_string(color)


def campo(p, instr, texto_previo="Haga clic derecho y elija «Actualizar campo»."):
    """Inserta un campo complejo de Word en el párrafo p."""
    def fc(tipo, dirty=False):
        r = p.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), tipo)
        if dirty:
            e.set(qn("w:dirty"), "true")
        r._r.append(e)
    fc("begin", True)
    r = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r._r.append(it)
    fc("separate")
    p.add_run(texto_previo)
    fc("end")


def toc_campo(doc, nuevo, titulos):
    """Campo TOC con resultado provisional (lista de títulos) para que no quede vacío
    antes de actualizarlo; Word lo recalcula con números de página (updateFields)."""
    def fc(p, tipo):
        r = p.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), tipo)
        if tipo == "begin":
            e.set(qn("w:dirty"), "true")
        r._r.append(e)
    ps = []
    for est, texto in titulos:
        p = nuevo("", desp=2 if est == "Heading 2" else 4)
        p.paragraph_format.left_indent = Cm(0.8) if est == "Heading 2" else Cm(0)
        r = p.add_run(texto)
        r.bold = est == "Heading 1"
        ps.append(p)
    fc(ps[0], "begin") if False else None
    # begin + instrucción + separate se anteponen al primer párrafo
    primero = ps[0]
    pre = []
    def mk(tipo=None, instr=None):
        r = OxmlElement("w:r")
        if tipo:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), tipo)
            if tipo == "begin":
                e.set(qn("w:dirty"), "true")
        else:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = instr
        r.append(e)
        return r
    ref = primero._p.find(qn("w:r"))
    for r in (mk("begin"), mk(instr=' TOC \\o "1-2" \\h \\z \\u '), mk("separate")):
        ref.addprevious(r)
    ps[-1]._p.append(mk("end"))


ORDEN = {
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
              "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
              "tblCaption", "tblDescription"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
             "textDirection", "tcFitText", "vAlign", "hideMark"],
    "trPr": ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
             "tblHeader", "tblCellSpacing", "jc", "hidden"],
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
            "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
            "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
            "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
}


def ordenar_hijos(doc):
    """Reordena los hijos de tblPr/tcPr/trPr/pPr según el orden del esquema OOXML."""
    for etiqueta, orden in ORDEN.items():
        for el in doc.element.body.iter(qn(f"w:{etiqueta}")):
            hijos = list(el)
            clave = lambda h: orden.index(h.tag.split("}")[1]) if h.tag.split("}")[1] in orden else 999
            for h in hijos:
                el.remove(h)
            for h in sorted(hijos, key=clave):
                el.append(h)


def idioma_es(doc):
    rpr = doc.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    for l in rpr.findall(qn("w:lang")):
        rpr.remove(l)
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "es-CO")
    lang.set(qn("w:eastAsia"), "es-CO")
    lang.set(qn("w:bidi"), "ar-SA")
    rpr.append(lang)


def construir():
    portada, objetivo, cuerpo = preparar_markdown()
    pypandoc.convert_text(cuerpo, "docx", format="markdown+pipe_tables-smart", outputfile=str(TMP),
                          extra_args=["--resource-path", str(AQUI), "--wrap=none"])
    doc = Document(str(TMP))
    st = doc.styles
    idioma_es(doc)

    # --- estilos ---
    for n in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text"):
        if n in [s.name for s in st]:
            fuente_estilo(st[n], size=11)
    for n in ("Body Text", "First Paragraph"):
        pf = st[n].paragraph_format
        pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(6), 1.15
    pf = st["Compact"].paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(2), 1.15
    for n, sz, antes, desp, col in (("Heading 1", 20, 0, 12, "1F4E79"), ("Heading 2", 15, 16, 6, "1F4E79"),
                                    ("Heading 3", 12, 12, 4, "2E75B6")):
        fuente_estilo(st[n], size=sz, bold=True, color=col)
        p = st[n].paragraph_format
        p.space_before, p.space_after, p.keep_with_next = Pt(antes), Pt(desp), True
    st["Heading 1"].paragraph_format.page_break_before = True
    fuente_estilo(st["Caption"], size=10, bold=True, italic=False, color="1F4E79")
    st["Caption"].paragraph_format.space_after = Pt(4)
    st["Caption"].paragraph_format.space_before = Pt(6)
    for n in ("Source Code", "Verbatim Char"):
        if n in [s.name for s in st]:
            fuente_estilo(st[n], nombre=MONO, size=9 if n == "Source Code" else 9.5)
    if "Hyperlink" in [s.name for s in st]:
        st["Hyperlink"].font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
        st["Hyperlink"].font.underline = True

    # --- secciones: márgenes A4 2,5 cm ---
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for a in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, a, Cm(2.5))
    sec.header_distance = sec.footer_distance = Cm(1.25)
    sec.gutter = Cm(0)

    # --- párrafos del cuerpo ---
    body = doc.element.body
    parrafos = list(doc.paragraphs)
    for p in parrafos:
        txt = p.text.strip()
        if re.match(r"^Tabla [A-Z]?\d+\.", txt):
            p.style = st["Caption"]
            p.paragraph_format.keep_with_next = True
        elif p.style.name in ("Image Caption", "Captioned Figure"):
            p.style = st["Caption"]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.style.name == "Caption":
                pass
        # imágenes: centrar y mantener con el pie
        if p._p.findall(".//" + qn("w:drawing")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
        # fuente de tabla: texto pequeño en cursiva
        if txt.startswith("Fuente:") or txt.startswith("Fuentes:"):
            for r in p.runs:
                r.font.size = Pt(9)
    # el pie de figura debe ir centrado
    for p in doc.paragraphs:
        if re.match(r"^Figura \d+\.", p.text.strip()):
            p.style = st["Caption"]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # --- tablas ---
    for t in doc.tables:
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        for e in tblPr.findall(qn("w:tblW")):
            tblPr.remove(e)
        w = OxmlElement("w:tblW")
        w.set(qn("w:w"), "5000")
        w.set(qn("w:type"), "pct")
        tblPr.append(w)
        for e in tblPr.findall(qn("w:tblLayout")):
            tblPr.remove(e)
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "autofit")
        tblPr.append(lay)
        bordes_tabla(t)
        for i, fila in enumerate(t.rows):
            trPr = fila._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            if i == 0:
                h = OxmlElement("w:tblHeader")
                trPr.append(h)
            for c in fila.cells:
                tcPr = c._tc.get_or_add_tcPr()
                mar = OxmlElement("w:tcMar")
                for lado, v in (("top", 40), ("left", 80), ("bottom", 40), ("right", 80)):
                    m = OxmlElement(f"w:{lado}")
                    m.set(qn("w:w"), str(v))
                    m.set(qn("w:type"), "dxa")
                    mar.append(m)
                tcPr.append(mar)
                if i == 0:
                    sombrear(c, "DEEAF6")
                for p in c.paragraphs:
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.line_spacing = 1.0
                    if i < len(t.rows) - 1:
                        p.paragraph_format.keep_with_next = True  # evita cortar la tabla
                    for r in p.runs:
                        r.font.size = Pt(9)
                        if i == 0:
                            r.font.bold = True

    # --- cita del objetivo (si pandoc generó Block Text, resaltarla) ---
    for p in doc.paragraphs:
        if p.style.name == "Block Text":
            borde_parrafo(p, fondo="EAF1F8")
    # --- portada: se inserta al inicio del cuerpo ---
    primero = body[0]

    def nuevo(texto="", size=11, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.LEFT, antes=0, desp=6):
        p = doc.add_paragraph()
        body.remove(p._p)
        primero.addprevious(p._p)
        p.alignment = align
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(antes), Pt(desp)
        if texto:
            r = p.add_run(texto)
            r.font.size, r.font.bold = Pt(size), bold
            if color:
                r.font.color.rgb = RGBColor.from_string(color)
        return p

    titulo = portada[0].lstrip("# ").strip()
    nuevo("", antes=60)
    p = nuevo(titulo.split(" — ")[0], size=40, bold=True, color="1F4E79", desp=4)
    nuevo(titulo.split(" — ")[1][0].upper() + titulo.split(" — ")[1][1:], size=18, color="2E75B6", desp=30)
    nuevo("Taller de Sistemas Recomendadores 2026-1 — Documento final", size=14, bold=True, desp=24)
    nuevo("Grupo 7", size=13, bold=True, desp=2)
    nuevo("Integrantes: Gabriel Escobar, Oscar Ramirez", size=12, desp=18)
    # repositorio con enlace clicable
    p = nuevo("", desp=6)
    r = p.add_run("Repositorio (privado): ")
    r.bold = True
    url = "https://github.com/OscarMURA/skillpath-skills-recommender"
    rid = doc.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                             is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    rr = OxmlElement("w:r")
    rp = OxmlElement("w:rPr")
    rs = OxmlElement("w:rStyle")
    rs.set(qn("w:val"), "Hyperlink")
    rp.append(rs)
    rr.append(rp)
    tt = OxmlElement("w:t")
    tt.text = url
    rr.append(tt)
    h.append(rr)
    p._p.append(h)
    p = nuevo("", desp=6)
    p.add_run("Cuaderno de Jupyter: ").bold = True
    rc = p.add_run("notebooks/skillpath.ipynb")
    rc.font.name = MONO
    rc.font.size = Pt(10)
    p.add_run(" (versionado con las salidas ya ejecutadas).")
    p = nuevo("", desp=30)
    p.add_run("Aplicación web: ").bold = True
    rc = p.add_run("app/streamlit_app.py")
    rc.font.name = MONO
    rc.font.size = Pt(10)
    p.add_run("; se ejecuta con ")
    rc = p.add_run('pip install -e ".[dev]"')
    rc.font.name = MONO
    rc.font.size = Pt(10)
    p.add_run(" y ")
    rc = p.add_run("streamlit run app/streamlit_app.py")
    rc.font.name = MONO
    rc.font.size = Pt(10)
    p.add_run(" (Python 3.12 o superior).")
    p = nuevo("", desp=0)
    p.add_run("Objetivo del sistema. ").bold = True
    p.add_run(objetivo)
    borde_parrafo(p, fondo="EAF1F8")
    intro = next(l for l in portada if l.startswith("Este objetivo es el hilo"))
    intro = intro.replace("`", "")
    nuevo("", desp=6)
    nuevo(intro, size=10.5, desp=0)
    # salto de página + TOC
    p = nuevo("")
    p.add_run().add_break(WD_BREAK.PAGE)
    p = nuevo("Tabla de contenido", size=20, bold=True, color="1F4E79", desp=12)
    toc_campo(doc, nuevo, [(x.style.name, x.text) for x in doc.paragraphs
                           if x.style.name in ("Heading 1", "Heading 2")])
    # el primer Heading 1 ya fuerza salto de página; el cuerpo arranca con él

    # el párrafo introductorio ("Este objetivo es el hilo...") se queda en el cuerpo? Está en portada[15..]; se añade tras el TOC

    # --- pie con numeración (sin número en portada): sección única + título distinto en la primera página ---
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    pie = sec.footer
    pie.is_linked_to_previous = False
    fp = pie.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.add_run("SkillPath — Grupo 7 — Página ").font.size = Pt(9)
    campo(fp, " PAGE ", "1")
    for r in fp.runs:
        r.font.size = Pt(9)

    # --- settings: actualizar campos al abrir; propiedades ---
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    # updateFields debe ir antes de hdrShapeDefaults/footnotePr/endnotePr/compat (orden del esquema)
    sig = next((settings.find(qn(t)) for t in ("w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat", "w:docVars",
                                                 "w:rsids", "w:mathPr", "w:themeFontLang", "w:clrSchemeMapping")
                if settings.find(qn(t)) is not None), None)
    if sig is not None:
        sig.addprevious(uf)
    else:
        settings.append(uf)
    ordenar_hijos(doc)
    doc.core_properties.title = titulo
    doc.core_properties.author = "Grupo 7"
    doc.core_properties.language = "es-CO"
    doc.save(str(SALIDA))
    TMP.unlink(missing_ok=True)
    print("OK", SALIDA)


if __name__ == "__main__":
    construir()
