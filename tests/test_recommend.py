import pytest

from skillpath import LearnerProfile, recommend

ROLE = "Data Analyst"


def names(profile):
    return [i.skill for i in recommend(profile).items]


def test_mastered_skills_excluded():
    result = names(LearnerProfile(ROLE, {"SQL": "intermediate", "Python": "advanced"}))
    assert "SQL" not in result and "Python" not in result


def test_basic_skill_still_recommended():
    assert "SQL" in names(LearnerProfile(ROLE, {"SQL": "basic"}))


def test_skill_after_missing_prerequisite():
    result = names(LearnerProfile(ROLE))
    assert result.index("Python") < result.index("Pandas")


def test_deterministic():
    profile = LearnerProfile(ROLE, {"Excel": "basic"})
    assert recommend(profile) == recommend(profile)


def test_empty_profile_returns_all_catalog_skills():
    assert sorted(names(LearnerProfile(ROLE))) == ["Excel", "Pandas", "Python", "SQL", "Tableau"]


def test_unknown_role_raises():
    with pytest.raises(ValueError, match="Role desconocido"):
        recommend(LearnerProfile("Chef"))


@pytest.mark.parametrize("role", ["Data Analyst", "Software Engineer", "Data Scientist"])
def test_all_three_roles_work(role):
    path = recommend(LearnerProfile(role))
    assert path.role == role
    assert sorted(i.skill for i in path.items) == ["Excel", "Pandas", "Python", "SQL", "Tableau"]
    assert all(i.frequency > 0 for i in path.items)


def test_frequency_matches_real_table():
    from skillpath.catalog import FREQUENCY

    items = {i.skill: i for i in recommend(LearnerProfile("Software Engineer")).items}
    assert items["Python"].frequency == FREQUENCY["Software Engineer"]["python"] > 0
    assert "%" in items["Python"].explanation


def test_skill_without_data_gets_zero_and_stays_candidate(monkeypatch):
    from skillpath import catalog

    table = {r: dict(s) for r, s in catalog.FREQUENCY.items()}
    del table["Data Analyst"]["tableau"]
    monkeypatch.setattr(catalog, "FREQUENCY", table)
    items = recommend(LearnerProfile(ROLE)).items
    tableau = next(i for i in items if i.skill == "Tableau")
    assert tableau.frequency == 0.0
    assert "No aparece en las ofertas de Data Analyst analizadas." in tableau.explanation
    assert items[-1].skill == "Tableau"
