import csv

import pytest

from skillpath.catalog import ALIASES, CATALOG, FREQUENCY, load_catalog
from skillpath.catalog_validation import CATEGORIES, find_cycle, validate_catalog
from skillpath.frequency import SKILLS_CSV, normalize_skill


def raw_rows():
    with open(SKILLS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_size_in_range():
    assert 55 <= len(CATALOG) <= 65


def test_names_unique_in_csv():
    names = [r["name"] for r in raw_rows()]
    assert len(names) == len(set(names))


def test_category_closed_list_and_description():
    for skill in CATALOG.values():
        assert skill.category in CATEGORIES, skill.name
        assert skill.description.strip(), skill.name


def test_difficulty_integer_in_range():
    for skill in CATALOG.values():
        assert isinstance(skill.difficulty, int) and 1 <= skill.difficulty <= 5, skill.name


def test_prerequisites_exist_and_not_self():
    for skill in CATALOG.values():
        for p in skill.prerequisites:
            assert p in CATALOG, f"{skill.name} -> {p}"
            assert p != skill.name


def test_real_catalog_has_no_cycles():
    assert find_cycle({n: s.prerequisites for n, s in CATALOG.items()}) is None


def test_find_cycle_detects_cycle():
    cycle = find_cycle({"a": ("b",), "b": ("c",), "c": ("a",)})
    assert cycle is not None and cycle[0] == cycle[-1]
    assert set(cycle) == {"a", "b", "c"}


def test_find_cycle_detects_self_reference():
    assert find_cycle({"a": ("a",)}) == ["a", "a"]


def test_find_cycle_acyclic_returns_none():
    assert find_cycle({"a": ("b", "c"), "b": ("c",), "c": ()}) is None


def test_names_normalized_and_in_frequency():
    in_frequency = {s for table in FREQUENCY.values() for s in table}
    for name in CATALOG:
        assert normalize_skill(name, ALIASES) == name
        assert name in in_frequency, name


def test_key_skills_present():
    for name in ["sql", "excel", "python", "pandas", "tableau"]:
        assert name in CATALOG


def test_reviewed_column_is_true_or_false():
    rows = raw_rows()
    assert rows and "reviewed" in rows[0]
    assert all(r["reviewed"] in ("true", "false") for r in rows)


def test_validate_catalog_real_is_clean():
    assert validate_catalog(CATALOG, FREQUENCY) == []


def test_load_catalog_parses_fixture(tmp_path):
    path = tmp_path / "skills.csv"
    path.write_text(
        "name,category,description,difficulty,prerequisites,reviewed\n"
        'a,programación,"Una, con coma",2,,false\n'
        "b,herramientas,Otra,3,a;c,true\n"
        "c,herramientas,Tercera,1,,false\n",
        encoding="utf-8",
    )
    catalog = load_catalog(path)
    assert list(catalog) == ["a", "b", "c"]
    assert catalog["a"].prerequisites == () and catalog["a"].description == "Una, con coma"
    assert catalog["b"].prerequisites == ("a", "c")
    assert catalog["b"].difficulty == 3 and isinstance(catalog["b"].difficulty, int)
    assert catalog["b"].reviewed is True and catalog["a"].reviewed is False
