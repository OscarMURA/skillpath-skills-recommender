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

path = recommend(LearnerProfile(role=role, known_skills=known_skills))

st.subheader("Tu ruta de aprendizaje")
if path.items:
    st.table(
        pd.DataFrame(
            {
                "Orden": range(1, len(path.items) + 1),
                "Habilidad": [i.skill for i in path.items],
                "Frecuencia (%)": [i.frequency for i in path.items],
                "Esfuerzo": [i.effort for i in path.items],
                "Explicación": [i.explanation for i in path.items],
            }
        ).set_index("Orden")
    )
else:
    st.info("Ya dominas todas las habilidades del catálogo.")
