"""Minimal Streamlit page for SkillPath (UI text in Spanish)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from skillpath import LearnerProfile, recommend
from skillpath.catalog import CATALOG, ROLES

EXPERIENCE = {"Con experiencia": "experienced", "Inicial (estudiante o recién graduado)": "entry"}
LEVELS = {"básico": "basic", "intermedio": "intermediate", "avanzado": "advanced"}

st.title("SkillPath")
st.write("Recibe una ruta ordenada de habilidades técnicas por aprender.")
st.write(
    "Solo necesitas elegir el rol objetivo. Si quieres una ruta más personal, marca las "
    "habilidades que ya conoces (con tu nivel) y tus intereses; todo eso es opcional. "
    "Si prefieres no dar datos, activa «Empezar sin datos»."
)

role = st.selectbox("Rol objetivo", ROLES)
experience_label = st.radio(
    "Nivel de experiencia",
    list(EXPERIENCE),
    key="experience_level",
    help="«Inicial» mezcla las ofertas base con ofertas de nivel inicial (arshkon) para calcular la frecuencia.",
)
experience_level = EXPERIENCE[experience_label]
start_empty = st.checkbox(
    "Empezar sin datos",
    key="start_empty",
    help="Ignora las habilidades y los intereses y muestra el resultado de un perfil vacío.",
)

SUGGESTIONS = 8
suggested = [
    i.skill
    for i in recommend(
        LearnerProfile(role=role, experience_level=experience_level)
    ).most_frequent(SUGGESTIONS)
]
st.caption(f"Sugerencias: las más frecuentes en las ofertas de {role}. Marca las que ya conoces.")
columns = st.columns(4)
checked = []
for n, skill in enumerate(suggested):
    if columns[n % 4].checkbox(skill, key=f"suggest_{role}_{skill}"):
        checked.append(skill)

selected = st.multiselect("Habilidades que ya conoces", list(CATALOG))
known_skills = {}
for skill in checked + [s for s in selected if s not in checked]:
    label = st.selectbox(
        f"Nivel de dominio en {skill}", list(LEVELS), index=1, key=f"level_{skill}"
    )
    known_skills[skill] = LEVELS[label]

categories = sorted({skill.category for skill in CATALOG.values()})
chosen_interests = st.multiselect(
    "Intereses (habilidades o categorías)", list(CATALOG) + categories
)
free_interests = st.text_input(
    "Otros intereses (separados por comas)", help="Por ejemplo: dashboards, análisis de datos"
)
interests = chosen_interests + [t.strip() for t in free_interests.split(",") if t.strip()]

if start_empty:
    known_skills, interests = {}, []
path = recommend(
    LearnerProfile(
        role=role,
        known_skills=known_skills,
        interests=interests,
        experience_level=experience_level,
    )
)
if path.experience_level == "entry":
    if path.entry_sample_size is None:
        st.warning(
            f"No hay ofertas de nivel inicial para {role}: la frecuencia usa solo las ofertas base."
        )
    elif path.entry_weight == 0.0:
        st.warning(
            f"Solo hay {path.entry_sample_size} ofertas de nivel inicial de {role} (arshkon), "
            "muy pocas para mezclarlas: la frecuencia usa solo las ofertas base."
        )
    else:
        st.warning(
            f"La frecuencia mezcla las ofertas base con solo {path.entry_sample_size} ofertas de "
            f"nivel inicial de {role} (arshkon): es una muestra pequeña; tómala como orientación."
        )
if path.cold_start:
    st.info(
        "Sin datos tuyos no podemos personalizar: se muestra la ruta calculada con la "
        "frecuencia y el esfuerzo del rol, y la lista de las habilidades más frecuentes. "
        "Completa el formulario (habilidades conocidas o intereses) para personalizarla."
    )
if path.unrecognized_interests:
    st.warning(
        "No reconocimos estos intereses y no se usaron: "
        + ", ".join(path.unrecognized_interests)
    )

st.subheader("Tu ruta de aprendizaje")
if path.items:
    st.table(
        pd.DataFrame(
            {
                "Orden": range(1, len(path.items) + 1),
                "Habilidad": [i.skill for i in path.items],
                "Frecuencia (%)": [i.frequency for i in path.items],
                "Esfuerzo": [i.effort for i in path.items],
                "Similitud": [round(i.similarity, 2) for i in path.items],
                "Explicación": [i.explanation for i in path.items],
            }
        ).set_index("Orden")
    )
else:
    st.info("Ya dominas todas las habilidades del catálogo.")

# Always visible: useful to any Learner and easy to read (pure Frequency).
frequent = path.most_frequent(10)
st.subheader(f"Las más frecuentes en las ofertas de {role}")
if not path.cold_start:
    st.caption("Entre las habilidades que aún no dominas.")
st.table(
    pd.DataFrame(
        {
            "Orden": range(1, len(frequent) + 1),
            "Habilidad": [i.skill for i in frequent],
            "Frecuencia (%)": [i.frequency for i in frequent],
        }
    ).set_index("Orden")
)
