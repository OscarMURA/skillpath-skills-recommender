import math

import pytest

from skillpath.frequency import (
    ALIASES_CSV,
    EXCLUSIONS_TXT,
    FREQUENCY_CSV,
    ROLES,
    compute_frequency,
    load_aliases,
    load_exclusions,
    load_frequency_table,
    normalize_skill,
)

ALIASES = {"python3": "python", "ms excel": "excel", "communication skills": "communication"}
EXCLUSIONS = {"communication"}


def freq(df, role, skill):
    row = df[(df["role"] == role) & (df["skill"] == skill)]
    return row.iloc[0] if len(row) else None


def test_python_variants_are_one_skill():
    for raw in ["Python", " python3 ", "PYTHON", "python,"]:
        assert normalize_skill(raw, ALIASES) == "python"


def test_normalize_collapses_inner_spaces():
    assert normalize_skill("  Power   BI ", {}) == "power bi"


def test_variants_in_same_offer_count_once():
    df = compute_frequency({"R": ["Python, python3, PYTHON", "sql"]}, ALIASES, EXCLUSIONS)
    row = freq(df, "R", "python")
    assert row.offers_with_skill == 1 and row.frequency == 50.0


def test_repeated_skill_in_offer_counts_once():
    df = compute_frequency({"R": ["sql, sql, SQL", "excel"]}, {}, set())
    assert freq(df, "R", "sql").offers_with_skill == 1


def test_soft_skills_excluded():
    df = compute_frequency(
        {"R": ["communication, Communication Skills, sql"]}, ALIASES, EXCLUSIONS
    )
    assert list(df["skill"]) == ["sql"]


def test_empty_and_nan_offers_not_in_denominator():
    offers = ["python", "python, sql", "", None, math.nan, "   "]
    df = compute_frequency({"R": offers}, {}, set())
    assert (df["role_offers"] == 2).all()
    assert freq(df, "R", "python").frequency == 100.0
    assert freq(df, "R", "sql").frequency == 50.0


def test_exact_frequency_and_range():
    offers = ["sql, python", "sql", "excel", "python, excel"]
    df = compute_frequency({"R": offers}, {}, set())
    assert freq(df, "R", "sql").frequency == 50.0
    assert ((df["frequency"] > 0) & (df["frequency"] <= 100)).all()


def test_roles_are_independent_and_order_deterministic():
    df = compute_frequency({"B": ["b, a"], "A": ["z"]}, {}, set())
    assert list(zip(df["role"], df["skill"])) == [("A", "z"), ("B", "a"), ("B", "b")]
    again = compute_frequency({"B": ["b, a"], "A": ["z"]}, {}, set())
    assert df.equals(again)


def test_load_aliases_and_exclusions(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text("alias,skill\nPython3,Python\n MS  Excel ,Excel\n", encoding="utf-8")
    e = tmp_path / "e.txt"
    e.write_text("# comment\nCommunication\n\n  Teamwork  # inline\n", encoding="utf-8")
    assert load_aliases(a) == {"python3": "python", "ms excel": "excel"}
    assert load_exclusions(e) == {"communication", "teamwork"}


def test_versioned_aliases_and_exclusions():
    aliases = load_aliases(ALIASES_CSV)
    exclusions = load_exclusions(EXCLUSIONS_TXT)
    assert normalize_skill("Python3", aliases) == "python"
    assert normalize_skill("Microsoft Excel", aliases) == "excel"
    assert "communication" in exclusions
    assert normalize_skill("Communication Skills", aliases) in exclusions
    for target in aliases.values():
        assert target not in aliases, f"alias encadenado: {target}"


def test_versioned_frequency_table():
    from skillpath.catalog import ALIASES, CATALOG

    table = load_frequency_table(FREQUENCY_CSV)
    assert set(table) == set(ROLES)
    for role, skills in table.items():
        assert all(0 < f <= 100 for f in skills.values())
        for name in CATALOG:
            assert normalize_skill(name, ALIASES) in skills, (role, name)


def test_unknown_file_raises():
    with pytest.raises(FileNotFoundError):
        load_aliases("/no/such/file.csv")


@pytest.mark.parametrize(
    "raw, expected",
    [(".NET", ".net"), ("C++", "c++"), ("C#", "c#"), ("Python.", "python"),
     ("Node.js", "node.js"), ("CI/CD", "ci/cd"), ('"sql",', "sql"), ("(excel)", "excel")],
)
def test_normalize_keeps_names_and_strips_surplus_punctuation(raw, expected):
    assert normalize_skill(raw, {}) == expected


def test_dotnet_alias():
    assert normalize_skill("dotnet", load_aliases(ALIASES_CSV)) == ".net"
