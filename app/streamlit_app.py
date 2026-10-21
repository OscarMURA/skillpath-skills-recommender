"""Minimal Streamlit page for SkillPath (UI text in Spanish)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from skillpath import LearnerProfile, recommend
from skillpath.catalog import CATALOG, ROLES

LEVELS = {"básico": "basic", "intermedio": "intermediate", "avanzado": "advanced"}

st.title("SkillPath")
st.write("Recibe una ruta ordenada de habilidades técnicas por aprender.")

role = st.selectbox("Rol objetivo", ROLES)
selected = st.multiselect("Habilidades que ya conoces", list(CATALOG))
known_skills = {}
for skill in selected:
    label = st.selectbox(f"Nivel de dominio en {skill}", list(LEVELS), key=f"level_{skill}")
    known_skills[skill] = LEVELS[label]

categories = sorted({skill.category for skill in CATALOG.values()})
chosen_interests = st.multiselect(
    "Intereses (habilidades o categorías)", list(CATALOG) + categories
)
free_interests = st.text_input(
    "Otros intereses (separados por comas)", help="Por ejemplo: dashboards, análisis de datos"
)
interests = chosen_interests + [t.strip() for t in free_interests.split(",") if t.strip()]

path = recommend(
    LearnerProfile(role=role, known_skills=known_skills, interests=interests)
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
