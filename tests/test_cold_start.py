"""Cold start: empty Learner profile and Skills added to the Catalog (ticket 06)."""

import dataclasses

import pytest

from skillpath import LearnerProfile, catalog, recommend
from skillpath.catalog import CATALOG, ROLES
from skillpath.frequency import compute_frequency
from skillpath.similarity import get_model

TOP5_FORMULA = {
    "Data Analyst": ["sql", "excel", "agile", "data visualization", "tableau"],
    "Software Engineer": ["agile", "python", "html", "sql", "java"],
    "Data Scientist": ["python", "sql", "data visualization", "agile", "r"],
}


def pure_frequency_top(role, n):
    table = catalog.FREQUENCY[role]
    ranked = sorted(
        (s for s in CATALOG if table.get(s, 0.0) > 0), key=lambda s: (-table[s], s)
    )
    return ranked[:n]


@pytest.mark.parametrize("role", ROLES)
def test_empty_profile_is_cold_start_and_deterministic(role):
    path = recommend(LearnerProfile(role))
    assert path.cold_start
    assert path == recommend(LearnerProfile(role))
    assert len(path.items) == len(CATALOG)
    for item in path.items:
        assert item.explanation.strip()
        assert "Sin habilidades ni intereses reconocidos" in item.explanation


@pytest.mark.parametrize("role", ROLES)
def test_empty_profile_most_frequent_are_the_roles_top_frequency(role):
    path = recommend(LearnerProfile(role))
    top = path.most_frequent(10)
    assert [i.skill for i in top] == pure_frequency_top(role, 10)
    assert top[0].frequency == max(catalog.FREQUENCY[role][s] for s in CATALOG if s in catalog.FREQUENCY[role])
    assert [i.frequency for i in top] == sorted((i.frequency for i in top), reverse=True)
    assert len(path.most_frequent()) == 10


@pytest.mark.parametrize("role", ROLES)
def test_empty_profile_learning_path_keeps_signed_formula(role):
    items = recommend(LearnerProfile(role)).items
    assert [i.skill for i in items[:5]] == TOP5_FORMULA[role]


def test_most_frequent_excludes_zero_frequency():
    path = recommend(LearnerProfile("Data Analyst"))
    assert all(i.frequency > 0 for i in path.most_frequent(len(CATALOG)))


def test_known_skill_or_recognized_interest_is_not_cold_start():
    assert not recommend(LearnerProfile("Data Analyst", {"sql": "basic"})).cold_start
    assert not recommend(LearnerProfile("Data Analyst", interests=["tableau"])).cold_start
    assert not recommend(LearnerProfile("Data Analyst", interests=["machine learning"])).cold_start


def test_unrecognized_interest_alone_is_still_cold_start():
    path = recommend(LearnerProfile("Data Analyst", interests=["zzz qqq"]))
    assert path.cold_start
    assert path.unrecognized_interests == ["zzz qqq"]


def test_known_skill_outside_catalog_or_invalid_level_is_cold_start():
    assert recommend(LearnerProfile("Data Analyst", {"cobol": "advanced"})).cold_start
    assert recommend(LearnerProfile("Data Analyst", {"sql": "wizard"})).cold_start


# --- A Skill added to the Catalog needs no history -------------------------


@pytest.fixture
def catalog_with_sqlmesh(monkeypatch):
    new = dataclasses.replace(
        CATALOG["sql"],
        name="sqlmesh",
        description=(
            "Herramienta para la transformación de datos con sql dentro del almacén "
            "de datos, con pruebas y documentación."
        ),
        difficulty=2,
        prerequisites=("sql",),
        reviewed=False,
    )
    monkeypatch.setattr(catalog, "CATALOG", {**CATALOG, "sqlmesh": new})
    get_model.cache_clear()
    yield new
    monkeypatch.undo()
    get_model.cache_clear()


def find(path, name):
    matches = [i for i in path.items if i.skill == name]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("role", ROLES)
def test_new_skill_is_recommended_without_history(catalog_with_sqlmesh, role):
    assert "sqlmesh" not in catalog.FREQUENCY[role]
    path = recommend(LearnerProfile(role))
    assert len(path.items) == len(CATALOG) + 1
    sqlmesh = find(path, "sqlmesh")
    assert sqlmesh.frequency == 0.0
    assert sqlmesh.effort == 2 + 1
    assert "No aparece en las ofertas" in sqlmesh.explanation
    names = [i.skill for i in path.items]
    assert names.index("sql") < names.index("sqlmesh")
    assert "sqlmesh" not in [i.skill for i in path.most_frequent(len(names))]


def test_new_skill_effort_drops_when_prerequisite_is_known(catalog_with_sqlmesh):
    path = recommend(LearnerProfile("Data Analyst", {"sql": "intermediate"}))
    assert find(path, "sqlmesh").effort == 2


@pytest.mark.parametrize("interest", ["sqlmesh", "bases de datos"])
def test_interest_in_new_skill_or_its_category_is_recognized(catalog_with_sqlmesh, interest):
    path = recommend(LearnerProfile("Data Analyst", interests=[interest]))
    assert interest not in path.unrecognized_interests
    assert not path.cold_start
    assert find(path, "sqlmesh").similarity > 0


def test_known_related_skill_gives_new_skill_similarity(catalog_with_sqlmesh):
    path = recommend(LearnerProfile("Data Scientist", {"sql": "advanced"}))
    assert find(path, "sqlmesh").similarity > 0


def test_new_skill_frequency_comes_from_offers_not_learners():
    # Re-running the Frequency computation over Offers that mention it is enough.
    offers = {"R": ["sqlmesh, sql", "sql", "sqlmesh", "python"]}
    df = compute_frequency(offers, {}, set())
    row = df[(df["role"] == "R") & (df["skill"] == "sqlmesh")].iloc[0]
    assert row.frequency == 50.0
