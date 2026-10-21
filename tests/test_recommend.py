import pytest

from skillpath import LearnerProfile, recommend
from skillpath.catalog import CATALOG

ROLE = "Data Analyst"


def names(profile):
    return [i.skill for i in recommend(profile).items]


def test_mastered_skills_excluded():
    result = names(LearnerProfile(ROLE, {"sql": "intermediate", "python": "advanced"}))
    assert "sql" not in result and "python" not in result


def test_basic_skill_still_recommended():
    assert "sql" in names(LearnerProfile(ROLE, {"sql": "basic"}))


def test_skill_after_missing_prerequisite():
    result = names(LearnerProfile(ROLE))
    assert result.index("python") < result.index("pandas")


def test_deterministic():
    profile = LearnerProfile(ROLE, {"excel": "basic"})
    assert recommend(profile) == recommend(profile)


def test_empty_profile_returns_all_catalog_skills():
    assert sorted(names(LearnerProfile(ROLE))) == sorted(CATALOG)


def test_unknown_role_raises():
    with pytest.raises(ValueError, match="Role desconocido"):
        recommend(LearnerProfile("Chef"))


@pytest.mark.parametrize("role", ["Data Analyst", "Software Engineer", "Data Scientist"])
def test_all_three_roles_work(role):
    path = recommend(LearnerProfile(role))
    assert path.role == role
    assert sorted(i.skill for i in path.items) == sorted(CATALOG)
    with_data = [i for i in path.items if i.frequency > 0]
    assert len(with_data) > len(path.items) / 2


def test_frequency_matches_real_table():
    from skillpath.catalog import FREQUENCY

    items = {i.skill: i for i in recommend(LearnerProfile("Software Engineer")).items}
    assert items["python"].frequency == FREQUENCY["Software Engineer"]["python"] > 0
    assert "%" in items["python"].explanation


def test_skill_without_data_gets_zero_and_stays_candidate(monkeypatch):
    from skillpath import catalog

    table = {r: dict(s) for r, s in catalog.FREQUENCY.items()}
    del table["Data Analyst"]["tableau"]
    monkeypatch.setattr(catalog, "FREQUENCY", table)
    items = recommend(LearnerProfile(ROLE)).items
    tableau = next(i for i in items if i.skill == "tableau")
    assert tableau.frequency == 0.0
    assert "No aparece en las ofertas de Data Analyst analizadas." in tableau.explanation
    # After every Skill with Frequency > 0 that does not depend on it.
    position = {i.skill: n for n, i in enumerate(items)}
    for item in items:
        if item.frequency > 0 and "tableau" not in CATALOG[item.skill].prerequisites:
            assert position[item.skill] < position["tableau"], item.skill


@pytest.mark.parametrize("role", ["Data Analyst", "Software Engineer", "Data Scientist"])
def test_only_catalog_skills_and_prerequisites_first(role):
    items = recommend(LearnerProfile(role)).items
    position = {i.skill: n for n, i in enumerate(items)}
    for item in items:
        assert item.skill in CATALOG
        for p in CATALOG[item.skill].prerequisites:
            assert position[p] < position[item.skill], f"{p} antes de {item.skill}"


def test_prerequisites_first_with_partial_mastery():
    items = recommend(LearnerProfile("Data Scientist", {"python": "advanced", "sql": "basic"})).items
    position = {i.skill: n for n, i in enumerate(items)}
    assert "python" not in position
    for item in items:
        for p in CATALOG[item.skill].prerequisites:
            if p in position:
                assert position[p] < position[item.skill]
