import ast
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from skillpath import LearnerProfile, recommend
from skillpath.catalog import CATALOG, ROLES
from skillpath.models import MASTERED_LEVELS

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")
ENTRY = "Inicial (estudiante o recién graduado)"

# Synonyms that GLOSSARY.md marks with _Avoid_ (plus Spanish words the UI must not use).
FORBIDDEN = [
    "usuario", "perfil de usuario", "brecha", "faltantes", "ruta", "ruta de aprendizaje",
    "plan de estudio", "recomendación", "esfuerzo", "costo", "dificultad estimada",
    "nivel de dominio", "popularidad", "conteo", "demanda", "vacante", "posting", "anuncio",
    "competencia", "tecnología", "habilidad blanda", "dependencia", "requisito previo",
    "cargo", "job title", "lista de habilidades", "habilidad", "habilidades", "frecuencia",
    "ofertas", "oferta", "esfuerzo estimado", "prerrequisito", "prerrequisitos", "perfil",
    "rol", "roles", "catálogo",
]
FORBIDDEN_RE = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(w) for w in sorted(FORBIDDEN, key=len, reverse=True)) + r")(?!\w)",
    re.IGNORECASE,
)


def new_app():
    return AppTest.from_file(APP, default_timeout=30).run()


def with_role(role):
    at = new_app()
    at.selectbox(key="role").select(role).run()
    return at


def learning_path_markdown(at):
    """Markdown cards of the Learning path: '**1. sql** · categoría'."""
    return [m.value for m in at.markdown if re.match(r"\*\*\d+\. ", m.value)]


def gap_table(at):
    """The Skill gap dataframe (second dataframe: the first is the most frequent list)."""
    return at.dataframe[1].value


def frequent_table(at):
    return at.dataframe[0].value


def is_cold_start_info(at):
    return any("Sin datos tuyos" in i.value for i in at.info)


def top_frequent(role, n):
    return [i.skill for i in recommend(LearnerProfile(role)).most_frequent(n)]


def expected_gap(path, known=None):
    return [i.skill for i in path.items if i.frequency > 0]


# ------------------------------------------------------------------ basics
@pytest.mark.parametrize("role", ROLES)
def test_app_runs_with_empty_profile(role):
    at = with_role(role)
    assert not at.exception
    assert len(learning_path_markdown(at)) == 10  # default N
    assert is_cold_start_info(at)


@pytest.mark.parametrize("role", ROLES)
def test_app_runs_with_skills_and_interests(role):
    at = with_role(role)
    at.multiselect(key="known_selected").select("python").run()
    at.multiselect(key="interests_selected").select("tableau").select("machine learning").run()
    assert not at.exception
    assert not at.warning
    assert not is_cold_start_info(at)
    # a related Skill gets an explanation that mentions the relation
    assert any("Se relaciona con" in m for m in learning_path_markdown(at) + [t.value for t in at.markdown])


def test_learning_path_size_is_adjustable():
    at = new_app()
    assert len(learning_path_markdown(at)) == 10
    at.number_input(key="path_size").set_value(15).run()
    assert not at.exception
    assert len(learning_path_markdown(at)) == 15


@pytest.mark.parametrize("role", ROLES)
def test_learning_path_matches_engine_order(role):
    at = with_role(role)
    expected = [i.skill for i in recommend(LearnerProfile(role)).items][:10]
    shown = [re.match(r"\*\*\d+\. (.+?)\*\* ·", m).group(1) for m in learning_path_markdown(at)]
    assert shown == expected


# --------------------------------------------------------------- Skill gap
@pytest.mark.parametrize("role", ROLES)
def test_skill_gap_has_exactly_the_demanded_unmastered_skills(role):
    at = with_role(role)
    gap = gap_table(at)
    assert list(gap.columns) == [
        "Posición", "Skill", "Categoría", "Frequency (%)", "Effort", "Difficulty",
        "Prerequisites pendientes",
    ]
    path = recommend(LearnerProfile(role))
    assert set(gap["Skill"]) == set(expected_gap(path))
    assert len(gap) == len(expected_gap(path))
    assert (gap["Frequency (%)"] > 0).all()

    # with a declared Skill the Skill gap shrinks accordingly
    at.multiselect(key="known_selected").select("python").run()
    path = recommend(LearnerProfile(role, {"python": "intermediate"}))
    assert set(gap_table(at)["Skill"]) == set(expected_gap(path))


@pytest.mark.parametrize("role", ROLES)
def test_mastery_level_decides_whether_a_skill_leaves_the_gap(role):
    skill = top_frequent(role, 8)[0]
    at = with_role(role)
    assert skill in set(gap_table(at)["Skill"])
    at.checkbox(key=f"suggest_{role}_{skill}").check().run()
    assert not at.exception
    assert not is_cold_start_info(at)
    assert skill not in set(gap_table(at)["Skill"])  # intermediate = mastered
    assert skill not in list(frequent_table(at)["Skill"])
    at.selectbox(key=f"level_{skill}").select("básico").run()
    assert skill in set(gap_table(at)["Skill"])  # basic does not count as mastered
    at.selectbox(key=f"level_{skill}").select("avanzado").run()
    assert skill not in set(gap_table(at)["Skill"])


@pytest.mark.parametrize("role", ROLES)
def test_pending_prerequisites_are_shown(role):
    at = with_role(role)
    gap = gap_table(at).set_index("Skill")
    with_prereqs = [s for s in gap.index if CATALOG[s].prerequisites]
    assert with_prereqs
    for skill in with_prereqs:
        assert gap.loc[skill, "Prerequisites pendientes"] == ", ".join(CATALOG[skill].prerequisites)
    without = [s for s in gap.index if not CATALOG[s].prerequisites]
    assert all(gap.loc[s, "Prerequisites pendientes"] == "—" for s in without)

    # mastering one Prerequisite removes it from the pending text
    skill = with_prereqs[0]
    prereq = CATALOG[skill].prerequisites[0]
    at.multiselect(key="known_selected").select(prereq).run()
    pending = gap_table(at).set_index("Skill")["Prerequisites pendientes"]
    if skill in pending.index:
        assert prereq not in pending[skill].split(", ")


def test_pending_prerequisites_for_pandas_with_python_known():
    at = with_role("Data Analyst")
    row = gap_table(at).set_index("Skill").loc["pandas"]
    assert "python" in row["Prerequisites pendientes"]
    at.multiselect(key="known_selected").select("python").run()
    row = gap_table(at).set_index("Skill").loc["pandas"]
    assert row["Prerequisites pendientes"] == "—"


@pytest.mark.parametrize("role", ROLES)
def test_category_filter_and_sort(role):
    at = with_role(role)
    full = gap_table(at)
    category = full["Categoría"].iloc[0]
    at.multiselect(key="gap_categories").select(category).run()
    assert not at.exception
    filtered = gap_table(at)
    assert set(filtered["Categoría"]) == {category}
    assert set(filtered["Skill"]) == set(full[full["Categoría"] == category]["Skill"])

    at.multiselect(key="gap_categories").unselect(category).run()
    at.selectbox(key="gap_sort").select("Frequency").run()
    freqs = list(gap_table(at)["Frequency (%)"])
    assert freqs == sorted(freqs, reverse=True)
    at.selectbox(key="gap_sort").select("Effort").run()
    efforts = list(gap_table(at)["Effort"])
    assert efforts == sorted(efforts)
    at.selectbox(key="gap_sort").select("Posición en el Learning path").run()
    positions = list(gap_table(at)["Posición"])
    assert positions == sorted(positions)


@pytest.mark.parametrize("role", ROLES)
def test_zero_frequency_skills_are_mentioned_aside(role):
    at = with_role(role)
    path = recommend(LearnerProfile(role))
    zero = [i for i in path.items if i.frequency == 0]
    texts = [c.value for c in at.caption]
    if zero:
        assert any(f"{len(zero)} Skills del Catalog no aparecen" in t for t in texts)
    else:
        assert not any("no aparecen en las Offers" in t for t in texts)


# ----------------------------------------------------------- Role changes
def test_changing_role_updates_result_and_keeps_declared_skills():
    at = with_role("Data Analyst")
    at.multiselect(key="known_selected").select("python").select("sql").run()
    at.selectbox(key="level_python").select("básico").run()
    first = list(gap_table(at)["Skill"])

    at.selectbox(key="role").select("Software Engineer").run()
    assert not at.exception
    assert at.multiselect(key="known_selected").value == ["python", "sql"]
    assert at.selectbox(key="level_python").value == "básico"
    assert at.selectbox(key="level_sql").value == "intermedio"
    second = list(gap_table(at)["Skill"])
    assert second != first
    expected = recommend(
        LearnerProfile(
            "Software Engineer", {"python": "basic", "sql": "intermediate"}
        )
    )
    assert set(second) == set(expected_gap(expected))
    assert "python" in second and "sql" not in second


# ----------------------------------------------------------------- warnings
def test_app_warns_about_unrecognized_interest():
    at = new_app()
    at.text_input(key="interests_free").set_value("zzz qqq, tableau").run()
    assert not at.exception
    assert any("zzz qqq" in w.value for w in at.warning)
    assert not any("tableau" in w.value for w in at.warning)


@pytest.mark.parametrize("role", ROLES)
def test_start_without_data_shows_cold_start_result(role):
    at = with_role(role)
    at.checkbox(key="start_empty").check().run()
    assert not at.exception
    assert is_cold_start_info(at)
    frequent = frequent_table(at)
    assert len(frequent) == 10
    assert list(frequent["Skill"]) == top_frequent(role, 10)


@pytest.mark.parametrize("role", ROLES)
def test_start_without_data_ignores_declared_skills(role):
    at = with_role(role)
    at.multiselect(key="known_selected").select("python").run()
    assert not is_cold_start_info(at)
    at.checkbox(key="start_empty").check().run()
    assert not at.exception
    assert is_cold_start_info(at)
    assert set(gap_table(at)["Skill"]) == set(expected_gap(recommend(LearnerProfile(role))))


def test_minimal_profile_with_multiselect_skill_is_not_cold_start():
    at = new_app()
    assert is_cold_start_info(at)  # default: nothing declared
    at.multiselect(key="known_selected").select("tableau").run()
    assert not at.exception
    assert not is_cold_start_info(at)
    assert "tableau" not in set(gap_table(at)["Skill"])


def test_mastering_the_whole_catalog_shows_friendly_message():
    at = new_app()
    at.multiselect(key="known_selected").set_value(list(CATALOG)).run()
    assert not at.exception
    assert any("Ya dominas todas las Skills" in s.value for s in at.success)


# --------------------------------------------------------------- vocabulary
def visible_text(at):
    texts = []
    for kind in ("title", "header", "subheader", "markdown", "caption", "info", "warning", "success"):
        texts += [e.value for e in getattr(at, kind)]
    for kind in ("selectbox", "multiselect", "radio", "checkbox", "text_input", "number_input", "metric"):
        for e in getattr(at, kind):
            texts += [str(e.label), str(e.help or "")]
            if kind == "metric":
                texts.append(str(e.value))
    texts += [t.label for t in at.tabs] + [x.label for x in at.expander]
    for df in at.dataframe:
        value = df.value
        texts += list(value.columns)
        texts += [str(c) for c in value.to_numpy().ravel() if isinstance(c, str)]
    return texts


def forbidden_in(texts):
    return sorted({m.group(0).lower() for t in texts for m in FORBIDDEN_RE.finditer(t)})


def test_visible_text_uses_canonical_vocabulary():
    at = new_app()
    assert forbidden_in(visible_text(at)) == []
    at.selectbox(key="role").select("Data Scientist").run()
    at.radio(key="experience_level").set_value(ENTRY).run()
    at.multiselect(key="known_selected").select("python").select("sql").run()
    at.multiselect(key="interests_selected").select("machine learning").run()
    at.text_input(key="interests_free").set_value("zzz qqq").run()
    assert not at.exception
    assert forbidden_in(visible_text(at)) == []
    at.checkbox(key="start_empty").check().run()
    assert forbidden_in(visible_text(at)) == []


def test_app_source_strings_use_canonical_vocabulary():
    """Covers static text that AppTest does not expose (column help, tooltips)."""
    tree = ast.parse(Path(APP).read_text(encoding="utf-8"))
    strings = [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    # drop dictionary-key style identifiers and code-like strings
    strings = [s for s in strings if " " in s]
    assert forbidden_in(strings) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("experience_level", ["experienced", "entry"])
def test_engine_explanations_use_canonical_vocabulary(role, experience_level):
    for profile in (
        LearnerProfile(role, experience_level=experience_level),
        LearnerProfile(
            role, {"python": "intermediate", "excel": "basic"}, ["visualización"],
            experience_level=experience_level,
        ),
    ):
        path = recommend(profile)
        assert forbidden_in([i.explanation for i in path.items]) == []


# ------------------------------------------------------------ query params
def test_query_params_seed_the_learner_profile_on_first_load():
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["role"] = "Data Scientist"
    at.query_params["exp"] = "entry"
    at.query_params["known"] = "python:intermediate,sql:basic,nope:advanced,pandas:xyz"
    at.query_params["interests"] = "deep learning,visualización,zzz qqq"
    at.run()
    assert not at.exception
    assert at.selectbox(key="role").value == "Data Scientist"
    assert at.radio(key="experience_level").value == ENTRY
    assert at.multiselect(key="known_selected").value == ["python", "sql", "pandas"]
    assert at.selectbox(key="level_sql").value == "básico"
    assert at.selectbox(key="level_pandas").value == "intermedio"  # unknown level -> default
    assert "nope" not in at.multiselect(key="known_selected").value
    assert at.multiselect(key="interests_selected").value == ["deep learning", "visualización"]
    assert at.text_input(key="interests_free").value == "zzz qqq"
    assert any("zzz qqq" in w.value for w in at.warning)
    # only the first load seeds: later edits are not overwritten
    at.selectbox(key="role").select("Data Analyst").run()
    assert at.selectbox(key="role").value == "Data Analyst"


def test_query_params_ignore_invalid_values():
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["role"] = "Astronaut"
    at.query_params["exp"] = "senior"
    at.query_params["known"] = ":,x,y:advanced"
    at.run()
    assert not at.exception
    assert at.selectbox(key="role").value == ROLES[0]
    assert at.multiselect(key="known_selected").value == []


@pytest.mark.parametrize("role", ROLES)
def test_suggestions_hide_skills_already_in_multiselect(role):
    top = top_frequent(role, 3)
    at = with_role(role)
    assert all(at.checkbox(key=f"suggest_{role}_{s}") for s in top)
    at.multiselect(key="known_selected").select(top[0]).select(top[1]).run()
    assert not at.exception
    keys = {c.key for c in at.checkbox if c.key and c.key.startswith("suggest_")}
    assert f"suggest_{role}_{top[0]}" not in keys and f"suggest_{role}_{top[1]}" not in keys
    assert f"suggest_{role}_{top[2]}" in keys
    assert len(keys) == 8  # topped up with the next most frequent Skills
    assert top[0] not in set(gap_table(at)["Skill"])


def test_checked_suggestion_stays_visible_and_all_known_shows_caption():
    at = with_role("Data Analyst")
    skill = top_frequent("Data Analyst", 1)[0]
    at.checkbox(key=f"suggest_Data Analyst_{skill}").check().run()
    assert at.checkbox(key=f"suggest_Data Analyst_{skill}").value  # not hidden by itself
    at.multiselect(key="known_selected").set_value(list(CATALOG)).run()
    assert not [c for c in at.checkbox if c.key and c.key.startswith("suggest_")]
    assert any("Ya declaraste todas las Skills" in c.value for c in at.sidebar.caption)
