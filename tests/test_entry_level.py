import pytest

from skillpath import LearnerProfile, recommend
from skillpath import catalog
from skillpath.frequency import normalize_skill
from skillpath.catalog import ROLES
from skillpath.recommender import ENTRY_PRIOR_OFFERS, MIN_ENTRY_OFFERS


def _fingerprint(path):
    return [(i.skill, i.frequency, i.effort, i.explanation) for i in path.items]


@pytest.mark.parametrize("role", ROLES)
def test_default_equals_explicit_experienced_and_base_table(role):
    default = recommend(LearnerProfile(role))
    explicit = recommend(LearnerProfile(role, experience_level="experienced"))
    assert _fingerprint(default) == _fingerprint(explicit)
    for item in default.items:
        base = catalog.FREQUENCY[role].get(normalize_skill(item.skill, catalog.ALIASES), 0.0)
        assert item.frequency == base
        assert "nivel inicial" not in item.explanation
    assert default.entry_sample_size is None


@pytest.mark.parametrize("role", ROLES)
def test_entry_changes_result_with_real_data(role):
    base = recommend(LearnerProfile(role))
    entry = recommend(LearnerProfile(role, experience_level="entry"))
    assert entry.experience_level == "entry"
    assert entry.entry_sample_size == catalog.ENTRY_SAMPLE_SIZE[role]
    assert [i.skill for i in base.items] != [i.skill for i in entry.items] or [
        i.frequency for i in base.items
    ] != [i.frequency for i in entry.items]
    assert {i.skill for i in base.items} == {i.skill for i in entry.items}


@pytest.fixture
def small_tables(monkeypatch):
    base = {"sql": 40.0, "python": 20.0, "excel": 10.0}
    entry = {"sql": 60.0, "python": 0.0, "excel": 30.0}  # other Catalog Skills are "excluded"
    monkeypatch.setattr(catalog, "FREQUENCY", {"Data Analyst": base})
    monkeypatch.setattr(catalog, "ENTRY_FREQUENCY", {"Data Analyst": entry})
    return base, entry


def _by_skill(profile):
    return {i.skill: i for i in recommend(profile).items}


def test_blend_is_exact(monkeypatch, small_tables):
    base, entry = small_tables
    monkeypatch.setattr(catalog, "ENTRY_SAMPLE_SIZE", {"Data Analyst": 50})
    w = 50 / (50 + ENTRY_PRIOR_OFFERS)
    items = _by_skill(LearnerProfile("Data Analyst", experience_level="entry"))
    for skill in base:
        assert items[skill].frequency == pytest.approx(w * entry[skill] + (1 - w) * base[skill])
    # absent from the entry table (excluded) -> base only (0 here, not in base either)
    excluded = next(s for s in items if s not in entry)
    assert items[excluded].frequency == base.get(excluded, 0.0)


def test_excluded_skill_uses_base(monkeypatch):
    monkeypatch.setattr(catalog, "FREQUENCY", {"Data Analyst": {"sql": 40.0, "statistics": 8.0}})
    monkeypatch.setattr(catalog, "ENTRY_FREQUENCY", {"Data Analyst": {"sql": 60.0}})
    monkeypatch.setattr(catalog, "ENTRY_SAMPLE_SIZE", {"Data Analyst": 100})
    items = _by_skill(LearnerProfile("Data Analyst", experience_level="entry"))
    assert items["statistics"].frequency == 8.0
    assert "solo ofertas base" in items["statistics"].explanation
    assert items["sql"].frequency == pytest.approx(50.0)  # w = 0.5


def test_small_sample_is_not_blended(monkeypatch, small_tables):
    base, _ = small_tables
    monkeypatch.setattr(catalog, "ENTRY_SAMPLE_SIZE", {"Data Analyst": MIN_ENTRY_OFFERS - 1})
    path = recommend(LearnerProfile("Data Analyst", experience_level="entry"))
    assert path.entry_weight == 0.0
    for item in path.items:
        assert item.frequency == base.get(item.skill, 0.0)
    assert any("menos del mínimo" in i.explanation for i in path.items if i.skill in base)


def test_minimum_sample_is_blended(monkeypatch, small_tables):
    monkeypatch.setattr(catalog, "ENTRY_SAMPLE_SIZE", {"Data Analyst": MIN_ENTRY_OFFERS})
    path = recommend(LearnerProfile("Data Analyst", experience_level="entry"))
    assert path.entry_weight == pytest.approx(30 / 130)


@pytest.mark.parametrize("role", ROLES)
def test_entry_explanation_mentions_sample(role):
    path = recommend(LearnerProfile(role, experience_level="entry"))
    n = catalog.ENTRY_SAMPLE_SIZE[role]
    mixed = [i for i in path.items if "mezcla" in i.explanation]
    assert mixed
    for item in mixed:
        assert "nivel inicial" in item.explanation
        assert f"{n} ofertas" in item.explanation
        assert "muestra pequeña" in item.explanation


def test_invalid_experience_level_raises():
    with pytest.raises(ValueError, match="Nivel de experiencia"):
        recommend(LearnerProfile("Data Analyst", experience_level="senior"))


@pytest.mark.parametrize("role", ROLES)
def test_entry_is_deterministic(role):
    profile = LearnerProfile(role, {"excel": "basic"}, experience_level="entry")
    assert recommend(profile) == recommend(profile)
