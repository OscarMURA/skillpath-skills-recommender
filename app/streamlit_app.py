"""Streamlit app for SkillPath: the Learner's Learning path (UI text in Spanish)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from skillpath import LearnerProfile, LearningPath, recommend
from skillpath.catalog import CATALOG, ROLES
from skillpath.models import MASTERED_LEVELS

EXPERIENCE = {"Con experiencia": "experienced", "Inicial (estudiante o recién graduado)": "entry"}
LEVELS = {"básico": "basic", "intermedio": "intermediate", "avanzado": "advanced"}
SUGGESTIONS = 8
DEFAULT_PATH_SIZE = 10
SORT_OPTIONS = ["Posición en el Learning path", "Frequency", "Effort"]

st.set_page_config(page_title="SkillPath", layout="wide")


@st.cache_data(show_spinner=False)
def compute_path(
    role: str,
    known_skills: tuple[tuple[str, str], ...],
    interests: tuple[str, ...],
    experience_level: str,
) -> LearningPath:
    """Cached call to the engine; arguments are hashable."""
    return recommend(
        LearnerProfile(
            role=role,
            known_skills=dict(known_skills),
            interests=list(interests),
            experience_level=experience_level,
        )
    )


def pending_prerequisites(skill: str, known_skills: dict[str, str]) -> list[str]:
    """Direct Prerequisites of a Skill that the Learner has not mastered."""
    return [
        p for p in CATALOG[skill].prerequisites if known_skills.get(p) not in MASTERED_LEVELS
    ]


def seed_from_query_params() -> None:
    """Seed the Learner profile from the URL on the first load only (handy for screenshots).

    ?role=Data+Scientist&exp=entry&known=python:intermediate,sql:basic&interests=deep+learning,zzz
    Unknown values are ignored.
    """
    if "role" in st.session_state:
        return
    params = st.query_params
    role_param = params.get("role")
    if role_param in ROLES:
        st.session_state["role"] = role_param
    exp_param = params.get("exp")
    for label, value in EXPERIENCE.items():
        if exp_param == value:
            st.session_state["experience_level"] = label
    known = []
    for entry in (params.get("known") or "").split(","):
        name, _, level = entry.strip().partition(":")
        if name not in CATALOG or name in known:
            continue
        known.append(name)
        level_label = next(
            (k for k, v in LEVELS.items() if level.strip() in (k, v)), "intermedio"
        )
        st.session_state[f"level_{name}"] = level_label
    if known:
        st.session_state["known_selected"] = known
    valid = set(CATALOG) | {skill.category for skill in CATALOG.values()}
    interests_param = [t.strip() for t in (params.get("interests") or "").split(",") if t.strip()]
    recognized = [t for t in interests_param if t in valid]
    if recognized:
        st.session_state["interests_selected"] = recognized
    if len(recognized) < len(interests_param):
        st.session_state["interests_free"] = ", ".join(t for t in interests_param if t not in valid)


seed_from_query_params()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Tu Learner profile")
    st.caption("Solo el Role es obligatorio; lo demás es opcional.")
    role = st.selectbox(
        "Role objetivo",
        ROLES,
        key="role",
        help="El Role al que quieres llegar. Las Offers de ese Role definen qué Skills se piden.",
    )
    experience_label = st.radio(
        "Experiencia",
        list(EXPERIENCE),
        key="experience_level",
        help=(
            "«Inicial» mezcla las Offers base con Offers de nivel inicial (arshkon) para "
            "calcular la Frequency."
        ),
    )
    experience_level = EXPERIENCE[experience_label]
    start_empty = st.checkbox(
        "Empezar sin datos",
        key="start_empty",
        help="Ignora tus Skills y tus intereses y muestra el Learning path de un Learner profile vacío.",
    )

    already_known = set(st.session_state.get("known_selected", []))
    top_suggestions = [
        i.skill
        for i in compute_path(role, (), (), experience_level).most_frequent(len(CATALOG))
        if i.skill not in already_known
    ][:SUGGESTIONS]
    # Skills marked in a previous run stay listed even if they are not among this Role's top
    # suggestions, so the selection survives a Role change (Streamlit drops the state of any
    # widget that is not rendered).
    kept_checked = [
        s
        for s in st.session_state.get("suggest_checked", [])
        if s not in top_suggestions and s not in already_known
    ]
    suggested = top_suggestions + kept_checked
    st.markdown(f"**Sugerencias:** las más frecuentes en las Offers de {role}. Marca las que ya conoces.")
    if not suggested:
        st.caption("Ya declaraste todas las Skills más frecuentes del Role.")
    checked = []
    for skill in suggested:
        if st.checkbox(skill, key=f"suggest_{skill}"):
            checked.append(skill)
    st.session_state["suggest_checked"] = list(checked)

    selected = st.multiselect(
        "Skills que ya conoces",
        list(CATALOG),
        key="known_selected",
        placeholder="Elige Skills",
        help="Elige cualquier Skill del Catalog. Esta lista y las sugerencias que marcaste se conservan si cambias de Role.",
    )
    known_skills = {}
    declared = checked + [s for s in selected if s not in checked]
    if declared:
        st.markdown("**Mastery level de cada Skill**")
        st.caption("Desde intermedio se considera dominada; básico no.")
    for skill in declared:
        # Default through Session State (not `index=`): the level can also be seeded from the URL.
        st.session_state.setdefault(f"level_{skill}", "intermedio")
        label = st.selectbox(f"Mastery level en {skill}", list(LEVELS), key=f"level_{skill}")
        known_skills[skill] = LEVELS[label]

    categories = sorted({skill.category for skill in CATALOG.values()})
    chosen_interests = st.multiselect(
        "Intereses (Skills o categorías)",
        list(CATALOG) + categories,
        key="interests_selected",
        placeholder="Elige Skills o categorías",
        help="Las Skills relacionadas con tus intereses suben un poco en el Learning path.",
    )
    free_interests = st.text_input(
        "Otros intereses (separados por comas)",
        key="interests_free",
        placeholder="Escribe tus intereses",
        help="Por ejemplo: dashboards, análisis de datos",
    )
    interests = chosen_interests + [t.strip() for t in free_interests.split(",") if t.strip()]

if start_empty:
    known_skills, interests = {}, []
path = compute_path(
    role, tuple(sorted(known_skills.items())), tuple(interests), experience_level
)

# ------------------------------------------------------------------- main
st.title("SkillPath")
st.write(
    "SkillPath te propone un Learning path: la lista ordenada de Skills que conviene aprender "
    f"para llegar a tu Role objetivo, a partir de lo que piden las Offers de {role} y de lo que "
    "ya sabes. Completa tu Learner profile en la barra lateral."
)
with st.expander("¿Qué significa cada término?"):
    st.markdown(
        "- **Skill**: capacidad técnica concreta (lenguaje, herramienta, framework o concepto).\n"
        "- **Role**: uno de los tres objetivos profesionales: Data Analyst, Software "
        "Engineer o Data Scientist.\n"
        "- **Offer**: publicación laboral usada como evidencia de qué Skills pide un Role.\n"
        "- **Learner profile**: tu Role objetivo, tus Skills conocidas con su Mastery level y tus intereses.\n"
        "- **Mastery level**: cuánto dominas una Skill (básico, intermedio o avanzado); desde "
        "intermedio se considera dominada.\n"
        "- **Learning path**: lista ordenada de Skills por aprender.\n"
        "- **Skill gap**: las Skills que tu Role pide y que aún no dominas.\n"
        "- **Frequency**: porcentaje de las Offers del Role que mencionan la Skill.\n"
        "- **Difficulty**: qué tan compleja es la Skill por sí misma, de 1 a 5.\n"
        "- **Prerequisite**: Skill que conviene conocer antes de aprender otra.\n"
        "- **Effort**: estimación de cuánto te tomará aprender la Skill: su Difficulty más los Prerequisites "
        "que aún no dominas."
    )

if path.experience_level == "entry":
    if path.entry_sample_size is None:
        st.warning(
            f"No hay Offers de nivel inicial para {role}: la Frequency usa solo las Offers base."
        )
    elif path.entry_weight == 0.0:
        st.warning(
            f"Solo hay {path.entry_sample_size} Offers de nivel inicial de {role} (arshkon): "
            "es una muestra pequeña, muy pocas para mezclarlas; la Frequency usa solo las "
            "Offers base."
        )
    else:
        st.warning(
            f"La Frequency mezcla las Offers base con solo {path.entry_sample_size} Offers de "
            f"nivel inicial de {role} (arshkon): es una muestra pequeña; tómala como orientación."
        )
if path.cold_start:
    st.info(
        "Sin datos tuyos no podemos personalizar tu Learning path: se calculó solo con la "
        "Frequency y el Effort del Role. Agrega Skills conocidas o intereses en la barra "
        "lateral para personalizarlo."
    )
if path.unrecognized_interests:
    st.warning(
        "No reconocimos estos intereses y no se usaron: " + ", ".join(path.unrecognized_interests)
    )

gap_items = [i for i in path.items if i.frequency > 0]
no_data_items = [i for i in path.items if i.frequency == 0]

tab_path, tab_gap, tab_about = st.tabs(
    ["Learning path", "Skill gap completo", "Cómo funciona y límites"], key="main_tab"
)

with tab_path:
    c1, c2, c3 = st.columns(3)
    c1.metric("Role", role)
    c2.metric(
        "Skills en tu Skill gap",
        len(gap_items),
        help="Skills que el Role pide (Frequency mayor que 0) y que aún no dominas.",
    )
    c3.metric(
        "Skills que ya dominas",
        len(CATALOG) - len(path.items),
        help="Skills del Catalog que declaraste en Mastery level intermedio o avanzado.",
    )

    if not path.items:
        st.success("¡Ya dominas todas las Skills del Catalog! No queda nada por aprender aquí.")
    else:
        st.subheader("Tu Learning path")
        size = st.number_input(
            "Cuántas Skills mostrar",
            min_value=1,
            max_value=len(path.items),
            value=min(DEFAULT_PATH_SIZE, len(path.items)),
            step=1,
            key="path_size",
            help="El Learning path completo está ordenado; aquí ves las primeras Skills.",
        )
        st.caption(
            f"Las primeras {int(size)} de {len(path.items)} Skills, en el orden recomendado. "
            "El Skill gap completo está en la pestaña siguiente."
        )
        for position, item in enumerate(path.items[: int(size)], start=1):
            with st.container(border=True):
                st.markdown(f"**{position}. {item.skill}** · {CATALOG[item.skill].category}")
                st.caption(f"Frequency {item.frequency:.1f}% · Effort {item.effort}")
                st.write(item.explanation)

        # Always visible: useful to any Learner and easy to read (pure Frequency).
        frequent = path.most_frequent(10)
        st.subheader(f"Las más frecuentes en las Offers de {role}")
        if not path.cold_start:
            st.caption("Entre las Skills que aún no dominas.")
        st.dataframe(
            pd.DataFrame(
                {
                    "Orden": range(1, len(frequent) + 1),
                    "Skill": [i.skill for i in frequent],
                    "Frequency (%)": [i.frequency for i in frequent],
                }
            ),
            hide_index=True,
            column_config={
                "Orden": st.column_config.NumberColumn(
                    "Orden", help="Posición según la Frequency, de mayor a menor."
                ),
                "Skill": st.column_config.TextColumn("Skill", help="Capacidad técnica del Catalog."),
                "Frequency (%)": st.column_config.NumberColumn(
                    "Frequency (%)",
                    format="%.1f",
                    help="Porcentaje de las Offers del Role que mencionan la Skill.",
                ),
            },
        )

with tab_gap:
    st.subheader("Skill gap completo")
    st.caption(
        f"Todas las Skills que las Offers de {role} piden (Frequency mayor que 0) y que aún no dominas."
    )
    if not gap_items:
        st.success("No tienes Skills pendientes en tu Skill gap.")
    else:
        rows = pd.DataFrame(
            {
                "Posición": [path.items.index(i) + 1 for i in gap_items],
                "Skill": [i.skill for i in gap_items],
                "Categoría": [CATALOG[i.skill].category for i in gap_items],
                "Frequency (%)": [i.frequency for i in gap_items],
                "Effort": [i.effort for i in gap_items],
                "Difficulty": [CATALOG[i.skill].difficulty for i in gap_items],
                "Prerequisites pendientes": [
                    ", ".join(pending_prerequisites(i.skill, known_skills)) or "—"
                    for i in gap_items
                ],
            }
        )
        f1, f2 = st.columns(2)
        chosen = f1.multiselect(
            "Filtrar por categoría",
            sorted(rows["Categoría"].unique()),
            key="gap_categories",
            placeholder="Todas las categorías",
            help="Déjalo vacío para ver todas las categorías.",
        )
        order = f2.selectbox(
            "Ordenar por",
            SORT_OPTIONS,
            key="gap_sort",
            help="También puedes ordenar haciendo clic en el encabezado de una columna.",
        )
        if chosen:
            rows = rows[rows["Categoría"].isin(chosen)]
        if order == "Frequency":
            rows = rows.sort_values(["Frequency (%)", "Posición"], ascending=[False, True])
        elif order == "Effort":
            rows = rows.sort_values(["Effort", "Posición"])
        else:
            rows = rows.sort_values("Posición")
        st.caption(f"{len(rows)} de {len(gap_items)} Skills.")
        st.dataframe(
            rows,
            hide_index=True,
            width="stretch",
            column_config={
                "Posición": st.column_config.NumberColumn(
                    "Posición", help="Lugar de la Skill en tu Learning path completo."
                ),
                "Skill": st.column_config.TextColumn("Skill", help="Capacidad técnica del Catalog."),
                "Categoría": st.column_config.TextColumn(
                    "Categoría", help="Grupo temático de la Skill en el Catalog."
                ),
                "Frequency (%)": st.column_config.NumberColumn(
                    "Frequency (%)",
                    format="%.1f",
                    help="Porcentaje de las Offers del Role que mencionan la Skill.",
                ),
                "Effort": st.column_config.NumberColumn(
                    "Effort",
                    help="Estimación de cuánto te tomará aprender la Skill: Difficulty más los Prerequisites que aún no dominas.",
                ),
                "Difficulty": st.column_config.NumberColumn(
                    "Difficulty", help="Complejidad de la Skill por sí misma, de 1 (baja) a 5 (alta)."
                ),
                "Prerequisites pendientes": st.column_config.TextColumn(
                    "Prerequisites pendientes",
                    help="Prerequisites directos de la Skill que aún no dominas («—» si no tiene o ya los dominas).",
                ),
            },
        )
    if no_data_items:
        st.caption(
            f"{len(no_data_items)} Skills del Catalog no aparecen en las Offers de {role} "
            "(Frequency 0 %); van al final del Learning path y no se listan aquí."
        )

with tab_about:
    left, _ = st.columns([2, 1])
    with left:
        st.subheader("Cómo funciona")
        st.markdown(
            "- **Datos:** las Offers de cada Role (Data Analyst, Software Engineer, Data Scientist). "
            "La **Frequency** de una Skill es el porcentaje de esas Offers que la mencionan.\n"
            "- **Effort:** la Difficulty de la Skill (1 a 5) más los Prerequisites que aún no dominas.\n"
            "- **Orden:** sube lo que tiene Frequency alta y Effort bajo. Cada Skill va después de sus "
            "Prerequisites pendientes.\n"
            "- **Personalización:** las Skills relacionadas con las que ya conoces o con tus intereses "
            "suben un poco en el Learning path.\n"
            "- **Mastery level:** desde intermedio una Skill cuenta como dominada y sale de tu Skill gap."
        )
        st.subheader("Límites")
        st.markdown(
            "- Las Offers son de EE. UU. y están en inglés: no reflejan otros países ni el español.\n"
            "- El sistema prioriza lo frecuente y lo accesible. Las Skills de Difficulty alta (como "
            "deep learning) quedan abajo, y un interés pesa poco frente a la Frequency.\n"
            "- La muestra de nivel inicial es pequeña: 80, 216 y 47 Offers de arshkon (Data Analyst, "
            "Software Engineer, Data Scientist).\n"
            "- Los Prerequisites y la Difficulty del Catalog son juicio experto, no mediciones.\n"
            "- En la evaluación offline el sistema supera claramente al azar, pero no a ordenar solo "
            "por Frequency. Ninguna métrica offline mide si aprendes mejor."
        )
