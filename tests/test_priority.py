"""Priority, Effort and Mastery level behaviour of `recommend` (ticket 04)."""

import pytest

from skillpath import LearnerProfile, catalog, recommend
from skillpath.models import Skill

ROLES = ["Data Analyst", "Software Engineer", "Data Scientist"]
FIXTURE_ROLE = "Test Role"


def use_fixture(monkeypatch, skills, frequency):
    """Replace the Catalog and Frequency with a small fixture.

    skills: name -> (difficulty, prerequisites); frequency: name -> percentage.
    """
    catalog_fixture = {
        name: Skill(name, "test", "fixture", difficulty, tuple(prereqs))
        for name, (difficulty, prereqs) in skills.items()
    }
    monkeypatch.setattr(catalog, "CATALOG", catalog_fixture)
    monkeypatch.setattr(catalog, "FREQUENCY", {FIXTURE_ROLE: dict(frequency)})
    monkeypatch.setattr(catalog, "ALIASES", {})


def path_of(known=None, role=FIXTURE_ROLE):
    return recommend(LearnerProfile(role, known or {}))


def names(path):
    return [i.skill for i in path.items]


def by_name(path):
    return {i.skill: i for i in path.items}


def missing_ancestors(skill, mastered):
    """Independent reference: transitive Prerequisites not mastered (walk stops at mastered)."""
    seen, stack = set(), list(catalog.CATALOG[skill].prerequisites)
    while stack:
        p = stack.pop()
        if p in mastered or p in seen:
            continue
        seen.add(p)
        stack.extend(catalog.CATALOG[p].prerequisites)
    return seen


def assert_prerequisites_first(path, known):
    mastered = {s for s, lvl in known.items() if lvl in ("intermediate", "advanced")}
    position = {s: n for n, s in enumerate(names(path))}
    for skill in position:
        for ancestor in missing_ancestors(skill, mastered):
            assert position[ancestor] < position[skill], f"{ancestor} antes de {skill}"


# --- Mastery level -------------------------------------------------------


@pytest.mark.parametrize("level", ["intermediate", "advanced"])
def test_mastered_skill_not_recommended(monkeypatch, level):
    use_fixture(monkeypatch, {"alpha": (2, []), "beta": (2, [])}, {"alpha": 10, "beta": 5})
    assert names(path_of({"alpha": level})) == ["beta"]


def test_basic_skill_is_recommended(monkeypatch):
    use_fixture(monkeypatch, {"alpha": (2, []), "beta": (2, [])}, {"alpha": 10, "beta": 5})
    assert "alpha" in names(path_of({"alpha": "basic"}))


def test_basic_prerequisite_counts_as_missing(monkeypatch):
    use_fixture(
        monkeypatch,
        {"base": (2, []), "dependent": (3, ["base"])},
        {"base": 1, "dependent": 50},
    )
    basic = path_of({"base": "basic"})
    mastered = path_of({"base": "intermediate"})
    assert by_name(basic)["dependent"].effort == 3 + 1
    assert by_name(mastered)["dependent"].effort == 3
    assert by_name(basic)["dependent"].effort > by_name(mastered)["dependent"].effort
    # The basic Skill is still a candidate and comes before its dependent,
    # even though the dependent has a much higher priority.
    assert names(basic) == ["base", "dependent"]
    assert "base" not in names(mastered)
    assert "Conviene aprender antes: base." in by_name(basic)["dependent"].explanation


# --- Order with Prerequisites -------------------------------------------


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "known",
    [{}, {"python": "advanced"}, {"python": "basic", "sql": "intermediate"}, {"linux": "basic"}],
)
def test_real_catalog_prerequisites_first_transitively(role, known):
    assert_prerequisites_first(recommend(LearnerProfile(role, known)), known)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("known", [{}, {"python": "advanced"}])
def test_real_catalog_deep_chains_in_order(role, known):
    position = {s: n for n, s in enumerate(names(recommend(LearnerProfile(role, known))))}
    chains = [
        ["python", "machine learning", "deep learning", "tensorflow"],
        ["python", "machine learning", "deep learning", "pytorch"],
        ["statistics", "machine learning", "deep learning", "tensorflow"],
        ["statistics", "machine learning", "deep learning", "pytorch"],
        ["linux", "docker", "kubernetes"],
    ]
    for chain in chains:
        present = [s for s in chain if s in position]
        positions = [position[s] for s in present]
        assert positions == sorted(positions), chain


def test_deepest_skill_with_highest_frequency_still_last(monkeypatch):
    use_fixture(
        monkeypatch,
        {"l1": (1, []), "l2": (1, ["l1"]), "l3": (1, ["l2"]), "l4": (1, ["l3"])},
        {"l1": 1, "l2": 2, "l3": 3, "l4": 100},
    )
    assert names(path_of()) == ["l1", "l2", "l3", "l4"]


def test_stopping_at_mastered_skill_drops_deeper_requirements():
    # Mastering deep learning assumes machine learning: tensorflow does not require it.
    profile = LearnerProfile("Data Scientist", {"deep learning": "intermediate"})
    items = by_name(recommend(profile))
    assert items["tensorflow"].effort == 4  # no missing Prerequisites at all
    assert "Ya dominas sus Prerequisites" in items["tensorflow"].explanation


# --- Transitive Effort ---------------------------------------------------


def test_transitive_effort_real_catalog():
    # tensorflow (Difficulty 4) <- deep learning <- machine learning <- python, statistics
    assert catalog.CATALOG["tensorflow"].difficulty == 4
    items = by_name(recommend(LearnerProfile("Data Scientist")))
    assert items["tensorflow"].effort == 4 + 4
    assert "4 Prerequisites pendientes en total" in items["tensorflow"].explanation
    advanced_ml = by_name(
        recommend(LearnerProfile("Data Scientist", {"machine learning": "advanced"}))
    )
    assert advanced_ml["tensorflow"].effort == 4 + 1
    assert "machine learning" not in advanced_ml


def test_effort_counts_shared_ancestors_once(monkeypatch):
    # diamond: top <- left, right <- root; root must be counted once.
    use_fixture(
        monkeypatch,
        {"root": (1, []), "left": (1, ["root"]), "right": (1, ["root"]), "top": (2, ["left", "right"])},
        {"root": 1, "left": 1, "right": 1, "top": 1},
    )
    assert by_name(path_of())["top"].effort == 2 + 3


# --- Frequent but costly goes down --------------------------------------


def test_frequent_but_costly_skill_ranks_below_cheap_one(monkeypatch):
    use_fixture(
        monkeypatch,
        {
            "cheap": (1, []),
            "costly": (5, ["need1", "need2"]),
            "need1": (2, []),
            "need2": (2, []),
        },
        {"cheap": 20, "costly": 20, "need1": 0.1, "need2": 0.1},
    )
    order = names(path_of())
    assert order.index("cheap") < order.index("costly")


def test_real_case_statistics_before_machine_learning_for_data_analyst():
    items = by_name(recommend(LearnerProfile("Data Analyst")))
    order = names(recommend(LearnerProfile("Data Analyst")))
    assert items["statistics"].frequency == pytest.approx(5.59, abs=0.01)
    assert items["machine learning"].frequency == pytest.approx(5.65, abs=0.01)
    assert items["machine learning"].frequency > items["statistics"].frequency
    assert order.index("statistics") < order.index("machine learning")


# --- Determinism and tie-breaks -----------------------------------------


@pytest.mark.parametrize("role", ROLES)
def test_same_input_same_output(role):
    profile = LearnerProfile(role, {"python": "basic", "sql": "advanced"})
    results = [recommend(profile) for _ in range(3)]
    assert results[0] == results[1] == results[2]


def test_known_skills_insertion_order_does_not_matter():
    first = LearnerProfile("Data Scientist", {"python": "basic", "sql": "advanced", "git": "intermediate"})
    second = LearnerProfile("Data Scientist", {"git": "intermediate", "sql": "advanced", "python": "basic"})
    assert recommend(first) == recommend(second)


def test_tie_on_priority_prefers_higher_frequency(monkeypatch):
    # alpha: 5 / 1 = 5.0 ; zulu: 10 / 2 = 5.0 -> zulu has the higher Frequency.
    use_fixture(monkeypatch, {"alpha": (1, []), "zulu": (2, [])}, {"alpha": 5, "zulu": 10})
    assert names(path_of()) == ["zulu", "alpha"]


def test_full_tie_orders_alphabetically(monkeypatch):
    use_fixture(
        monkeypatch,
        {"charlie": (2, []), "alpha": (2, []), "bravo": (2, [])},
        {"charlie": 10, "alpha": 10, "bravo": 10},
    )
    assert names(path_of()) == ["alpha", "bravo", "charlie"]
