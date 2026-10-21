"""Similarity, interests and explanations. Behaviour is checked only via `recommend`."""

import csv

import pytest

from skillpath import LearnerProfile, recommend
from skillpath.catalog import CATALOG, ROLES
from skillpath.cooccurrence import COOCCURRENCE_CSV, compute_cooccurrence

ROLE = "Data Scientist"


def by_skill(profile):
    return {i.skill: i for i in recommend(profile).items}


def ranks(profile):
    return {i.skill: n for n, i in enumerate(recommend(profile).items, 1)}


# (a) related Skills come ahead of unrelated ones
def test_known_skill_makes_related_skills_rank_higher():
    empty = ranks(LearnerProfile(ROLE))
    with_pandas = ranks(LearnerProfile(ROLE, {"pandas": "advanced"}))
    items = by_skill(LearnerProfile(ROLE, {"pandas": "advanced"}))
    for related in ("numpy", "scikit-learn"):
        assert items[related].similarity > 0.5
        assert with_pandas[related] < empty[related]
    assert items["numpy"].similarity > items["css"].similarity
    assert items["scikit-learn"].similarity > items["angular"].similarity
    assert with_pandas["numpy"] < with_pandas["css"]


def test_python_is_closer_to_sql_than_to_css():
    items = by_skill(LearnerProfile(ROLE, {"python": "advanced"}))
    assert items["sql"].similarity > items["css"].similarity + 0.3


# (b) interests change the result
def test_interests_change_the_path():
    base = recommend(LearnerProfile("Data Analyst"))
    with_interest = recommend(LearnerProfile("Data Analyst", interests=["visualización"]))
    assert [i.skill for i in base.items] != [i.skill for i in with_interest.items]
    r0, r1 = ranks(LearnerProfile("Data Analyst")), ranks(
        LearnerProfile("Data Analyst", interests=["visualización"])
    )
    assert r1["tableau"] < r0["tableau"]
    items = {i.skill: i for i in with_interest.items}
    assert items["tableau"].similarity > 0.5 > items["jira"].similarity


def test_skill_name_interest_is_recognized_with_alias_and_case():
    path = recommend(LearnerProfile("Data Analyst", interests=["Machine Learning"]))
    assert path.unrecognized_interests == []
    assert {i.skill: i for i in path.items}["statistics"].similarity > 0


def test_interest_in_a_skill_favors_that_skill():
    items = by_skill(LearnerProfile("Data Analyst", interests=["tableau"]))
    assert items["tableau"].similarity == pytest.approx(1.0)


# (c) empty profile keeps the Frequency / Effort behaviour
@pytest.mark.parametrize("role", ROLES)
def test_empty_profile_orders_by_frequency_over_effort(role):
    path = recommend(LearnerProfile(role))
    assert all(i.similarity == 0.0 for i in path.items)
    position = {i.skill: n for n, i in enumerate(path.items)}
    # Without similarity, no Skill with a strictly higher Frequency/Effort may come
    # after a lower one unless a missing Prerequisite forces it (topological step).
    for a in path.items:
        for b in path.items:
            if a.frequency / a.effort > b.frequency / b.effort and position[a.skill] > position[b.skill]:
                assert CATALOG[a.skill].prerequisites, (a.skill, b.skill)


def test_empty_profile_top_matches_signed_example():
    top = [i.skill for i in recommend(LearnerProfile("Software Engineer")).items[:4]]
    assert top == ["agile", "python", "html", "sql"]  # docs/priority-formula.md, example 3


# (d) determinism
def test_deterministic_with_similarity():
    profile = LearnerProfile(ROLE, {"python": "advanced", "sql": "basic"}, ["machine learning", "nube"])
    assert recommend(profile) == recommend(profile)


# (e) explanations
@pytest.mark.parametrize("role", ROLES)
def test_every_item_has_explanation_and_mentions_relation(role):
    profile = LearnerProfile(role, {"python": "advanced"})
    path = recommend(profile)
    assert all(i.explanation.strip() for i in path.items)
    r = by_skill(profile)["sql"]
    assert "python" in r.explanation and "Se relaciona con lo que ya sabes" in r.explanation


def test_explanation_without_anchor_does_not_invent_relations():
    for item in recommend(LearnerProfile(ROLE)).items:
        assert "Sin Skills ni intereses" in item.explanation
        assert "Se relaciona" not in item.explanation


def test_explanation_mentions_interest_and_prerequisites():
    items = by_skill(LearnerProfile("Data Analyst", {"excel": "advanced"}, ["visualización"]))
    assert "Se relaciona con tus intereses: visualización" in items["tableau"].explanation
    assert "Ya dominas sus Prerequisites: excel" in items["power bi"].explanation
    assert "Conviene aprender antes: python" in items["pandas"].explanation


def test_weak_relations_are_not_listed():
    explanation = by_skill(LearnerProfile(ROLE, {"python": "advanced"}))["css"].explanation
    assert "Se relaciona" not in explanation and "Sin relación clara" in explanation


# (f) similarity range
@pytest.mark.parametrize("role", ROLES)
def test_similarity_in_unit_interval(role):
    profile = LearnerProfile(role, {"python": "basic", "sql": "advanced"}, ["devops", "tableau"])
    assert all(0.0 <= i.similarity <= 1.0 for i in recommend(profile).items)


def test_basic_known_skill_is_not_maximally_similar_to_itself():
    items = by_skill(LearnerProfile("Data Analyst", {"sql": "basic", "excel": "basic"}))
    assert items["sql"].similarity < 0.9


# (g) unrecognized interests
@pytest.mark.parametrize("junk", ["zzz qqq", "   ", "de la y"])
def test_unrecognized_interest_behaves_like_no_interest(junk):
    base = recommend(LearnerProfile("Data Analyst", {"excel": "advanced"}))
    path = recommend(LearnerProfile("Data Analyst", {"excel": "advanced"}, [junk]))
    assert path.items == base.items
    if junk.strip():
        assert path.unrecognized_interests == [junk]


def test_unrecognized_interest_is_reported_and_others_still_work():
    path = recommend(LearnerProfile("Data Analyst", interests=["zzz qqq", "tableau"]))
    assert path.unrecognized_interests == ["zzz qqq"]
    assert {i.skill: i for i in path.items}["tableau"].similarity == pytest.approx(1.0)


# (h) the committed co-occurrence file
def _rows():
    with open(COOCCURRENCE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_cooccurrence_file_is_consistent():
    fields, rows = _rows()
    assert fields == ["role", "skill_a", "skill_b", "offers_together", "closeness"]
    assert rows
    seen = set()
    for r in rows:
        assert r["role"] in ROLES
        assert r["skill_a"] in CATALOG and r["skill_b"] in CATALOG
        assert r["skill_a"] < r["skill_b"]  # canonical order: each pair once
        assert (r["role"], r["skill_a"], r["skill_b"]) not in seen
        seen.add((r["role"], r["skill_a"], r["skill_b"]))
        assert int(r["offers_together"]) >= 1
        assert 0.0 < float(r["closeness"]) <= 1.0
    assert {r["role"] for r in rows} == set(ROLES)


# co-occurrence pure functions, tiny fixtures
ALIASES = {"python3": "python", "ms excel": "excel"}
OFFERS = {
    "R": [
        "Python, SQL, communication",
        "python3, sql",
        "Python, Excel",
        "MS Excel, sql, Python3, Python",  # variants of one Skill count once
        None,  # empty Offer is ignored
        "",
        "Docker",  # not in the Catalog
    ]
}


def test_compute_cooccurrence_counts_and_closeness():
    df = compute_cooccurrence(OFFERS, ALIASES, {"communication"}, ["python", "sql", "excel"])
    rows = {(r.skill_a, r.skill_b): r for r in df.itertuples()}
    assert set(rows) == {("python", "sql"), ("excel", "python"), ("excel", "sql")}
    py_sql = rows[("python", "sql")]
    assert py_sql.offers_together == 3
    # python: 4 Offers, sql: 3 Offers, together 3 -> 3 / sqrt(4 * 3)
    assert py_sql.closeness == pytest.approx(3 / (4 * 3) ** 0.5, abs=1e-4)
    assert rows[("excel", "sql")].offers_together == 1


def test_compute_cooccurrence_min_offers_prunes_pairs():
    df = compute_cooccurrence(OFFERS, ALIASES, set(), ["python", "sql", "excel"], min_offers=2)
    assert [(r.skill_a, r.skill_b) for r in df.itertuples()] == [("excel", "python"), ("python", "sql")]
    assert df["closeness"].between(0, 1).all()
