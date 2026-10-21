import pandas as pd
import pytest

from skillpath.catalog import CATALOG
from skillpath.entry_frequency import (
    CALIBRATION_CSV,
    ENTRY_FREQUENCY_CSV,
    ENTRY_LEVELS,
    compute_entry_frequency,
    role_from_title,
    unreliable_skills,
)
from skillpath.frequency import (
    ALIASES_CSV,
    ROLES,
    load_aliases,
    load_frequency_table,
    normalize_skill,
)
from skillpath.skill_detection import build_patterns, detect_skills

ALIASES = load_aliases(ALIASES_CSV)
NAMES = sorted({normalize_skill(n, ALIASES) for n in CATALOG})
PATTERNS = build_patterns(NAMES, ALIASES)


def detect(text):
    return detect_skills(text, PATTERNS)


@pytest.mark.parametrize(
    "text, skill",
    [
        ("Experience with R&D projects", "r"),
        ("Contact Mr. R about it", "r"),
        ("Section (r) of the policy", "r"),
        ("Level r is required", "r"),
        ("Let's go to the market", "go"),
        ("go to market strategy", "go"),
        ("Go to market strategy and Python", "go"),
        ("You will excel in this role", "excel"),
        ("Candidates who excel at teamwork", "excel"),
        ("Excel in a fast paced team", "excel"),
        ("an excellent communicator", "excel"),
        ("We want you to Excel at problem solving", "excel"),
        ("the rest of the team", "rest api"),
        ("take a rest", "rest api"),
        ("Knowledge of JavaScript frameworks", "java"),
        ("Experience with MySQL and PostgreSQL", "sql"),
        ("NoSQL stores", "sql"),
        ("Spark curiosity and joy", "spark"),
        ("We react quickly to change", "react"),
        ("Oracle Corporation is an equal opportunity employer", "oracle"),
        ("Azure DevOps pipelines", "azure"),
        ("Experience with SQL Server", "sql"),
        ("snowflake schema design", "snowflake"),
        ("machine learning algorithms", "algorithms"),
        ("Build scalable systems", "scala"),
    ],
)
def test_known_false_positives_not_detected(text, skill):
    assert skill not in detect(text)


@pytest.mark.parametrize(
    "text, skills",
    [
        ("Python, R, SQL", {"python", "r", "sql"}),
        ("proficiency in R or Python", {"r", "python"}),
        ("R programming and RStudio", {"r"}),
        ("SAS, R, or Stata", {"r", "sas"}),
        ("C++ and C# developers", {"c++", "c#"}),
        ("C sharp experience", {"c#"}),
        ("Node.js and REST APIs", {"node.js", "rest api"}),
        ("RESTful services", {"rest api"}),
        ("CI/CD pipelines", {"ci/cd"}),
        ("Golang services", {"go"}),
        ("Python, Go, and Java", {"go", "python", "java"}),
        ("experience with the Go programming language", {"go"}),
        ("Microsoft Excel and PowerPoint", {"excel"}),
        ("Advanced Excel (pivot tables)", {"excel"}),
        ("excel spreadsheets", {"excel"}),
        ("scikit-learn and sklearn", {"scikit-learn"}),
        ("A/B testing and AB tests", {"a/b testing"}),
        ("Power BI, PowerBI, Tableau", {"power bi", "tableau"}),
        ("Postgres and MySQL", {"postgresql", "mysql"}),
        ("Apache Spark and PySpark", {"spark"}),
        ("Python, Scala, Spark", {"spark", "scala"}),
        ("on GitHub", {"git"}),
        ("React.js and ReactJS", {"react"}),
        ("Oracle database", {"oracle"}),
        ("object-oriented programming", {"object-oriented programming"}),
        ("T-SQL and PL/SQL", {"sql"}),
        ("MS SQL Server", {"sql server"}),
        ("k8s and Docker", {"kubernetes", "docker"}),
    ],
)
def test_true_positives_detected(text, skills):
    assert skills <= detect(text)


def test_javascript_is_not_java_and_java_is_found_alone():
    assert detect("Java developer") >= {"java"}
    assert "java" not in detect("JavaScript developer") and "javascript" in detect("JavaScript developer")


def test_case_insensitive_and_empty_text():
    assert "python" in detect("PYTHON")
    assert detect("") == set() and detect(None) == set()


def test_short_acronyms_are_case_sensitive():
    assert "machine learning" in detect("We use ML models")
    assert "machine learning" not in detect("the ml of the tank")


# ----------------------------------------------------------------- titles

@pytest.mark.parametrize(
    "title, role",
    [
        ("Data Analyst", "Data Analyst"),
        ("Senior DATA ANALYST - Finance", "Data Analyst"),
        ("Junior Data Scientist (NLP)", "Data Scientist"),
        ("Software Engineer II", "Software Engineer"),
        ("Backend Software Developer", "Software Engineer"),
        ("Software Development Engineer", "Software Engineer"),
        ("Data Analyst / Data Scientist", None),
        ("Data Scientist, Software Engineer", None),
        ("Nurse", None),
        ("Data Analysts", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_role_from_title(title, role):
    assert role_from_title(title) == role


# --------------------------------------------------------------- frequency

def test_compute_entry_frequency_exact_values_and_sample_size():
    offers = [
        ("Data Analyst", "SQL, SQL and Python"),
        ("Data Analyst", "Python only"),
        ("Data Analyst", "nothing here"),
        ("Data Analyst", None),
        ("Software Engineer", "Java and Python"),
        ("Not a role", "Python"),
    ]
    df = compute_entry_frequency(offers, PATTERNS, ["python", "sql", "java"])
    assert list(df.columns) == ["role", "skill", "offers_with_skill", "role_offers", "frequency"]
    assert len(df) == len(ROLES) * 3  # also Skills with 0 Offers, and empty Roles
    get = lambda role, skill: df[(df.role == role) & (df.skill == skill)].iloc[0]
    assert get("Data Analyst", "sql").offers_with_skill == 1  # one Offer counts once
    assert get("Data Analyst", "sql").frequency == 33.33
    assert get("Data Analyst", "python").frequency == 66.67
    assert (df[df.role == "Data Analyst"].role_offers == 3).all()  # empty description skipped
    assert get("Software Engineer", "java").frequency == 100.0
    assert (df[df.role == "Data Scientist"].role_offers == 0).all()
    assert (df[df.role == "Data Scientist"].frequency == 0).all()


def test_exact_duplicate_descriptions_count_once_per_role():
    offers = [
        ("Data Analyst", "We use Python."),
        ("Data Analyst", "  we  use\npython. "),  # same text after strip/collapse/case
        ("Data Analyst", "We use SQL."),
        ("Data Scientist", "We use Python."),  # same text, other Role: counts there
    ]
    df = compute_entry_frequency(offers, PATTERNS, ["python", "sql"])
    da = df[df.role == "Data Analyst"].set_index("skill")
    assert da.role_offers.iloc[0] == 2
    assert da.loc["python", "offers_with_skill"] == 1 and da.loc["python", "frequency"] == 50.0
    assert (df[df.role == "Data Scientist"].role_offers == 1).all()


def test_compute_entry_frequency_is_deterministic():
    offers = [("Data Scientist", "Python, R"), ("Data Scientist", "SQL")]
    a = compute_entry_frequency(offers, PATTERNS, ["sql", "python", "r"])
    b = compute_entry_frequency(list(reversed(offers)), PATTERNS, ["r", "python", "sql"])
    pd.testing.assert_frame_equal(a, b)


def test_default_levels_are_entry_and_internship():
    assert ENTRY_LEVELS == ("Entry level", "Internship")


# ------------------------------------------------------ versioned CSV files

@pytest.fixture(scope="module")
def entry_df():
    return pd.read_csv(ENTRY_FREQUENCY_CSV)


@pytest.fixture(scope="module")
def calibration_df():
    return pd.read_csv(CALIBRATION_CSV)


def test_entry_csv_columns_and_skills_in_catalog(entry_df):
    assert list(entry_df.columns) == ["role", "skill", "offers_with_skill", "role_offers", "frequency"]
    assert set(entry_df["skill"]) <= set(NAMES)
    assert set(entry_df["role"]) == set(ROLES)


def test_entry_csv_frequency_range_and_sample_size(entry_df):
    assert entry_df["frequency"].between(0, 100).all()
    for role, g in entry_df.groupby("role"):
        assert g["role_offers"].nunique() == 1, role
        assert g["role_offers"].iloc[0] > 0, role
        assert g["skill"].is_unique, role
        assert (g["offers_with_skill"] <= g["role_offers"]).all()
    assert entry_df.groupby("role")["skill"].apply(frozenset).nunique() == 1  # same Skills per Role


def test_entry_csv_has_no_unreliable_skill(entry_df, calibration_df):
    assert not set(unreliable_skills(calibration_df)) & set(entry_df["skill"])
    assert set(entry_df["skill"]) | set(unreliable_skills(calibration_df)) == set(NAMES)


def test_entry_csv_is_readable_as_frequency_table():
    from skillpath.entry_frequency import ENTRY_FREQUENCY_CSV as path

    table = load_frequency_table(path)
    assert set(table) == set(ROLES)


def test_calibration_csv_shape(calibration_df):
    assert list(calibration_df.columns) == [
        "role", "skill", "text_frequency", "skills_frequency", "reference_frequency",
        "diff", "ratio", "reliable",
    ]
    assert set(calibration_df["skill"]) == set(NAMES)
    assert len(calibration_df) == len(NAMES) * len(ROLES)
    assert calibration_df["reliable"].dtype == bool
