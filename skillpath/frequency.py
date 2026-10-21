"""Frequency of each Skill per Role, computed from real Offers.

Frequency = 100 * (Offers of the Role mentioning the Skill)
            / (Offers of the Role with a non-empty ``job_skills``).
Each Offer counts once per Skill, after normalizing names and applying aliases.
"""

import csv
import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

REPO_DIR = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_DIR / "catalog"
FREQUENCY_CSV = CATALOG_DIR / "frequency_by_role.csv"
ALIASES_CSV = CATALOG_DIR / "aliases.csv"
SKILLS_CSV = CATALOG_DIR / "skills.csv"
EXCLUSIONS_TXT = CATALOG_DIR / "exclusions.txt"
DATOS_DIR = REPO_DIR / "datos"

# One dataset = one Role.
ROLE_DATASETS: dict[str, str] = {
    "Data Analyst": "asaniczka_data-analyst-job-postings/postings.csv",
    "Software Engineer": "asaniczka_software-engineer-job-postings-linkedin/postings.csv",
    "Data Scientist": "asaniczka_data-scientist-linkedin-job-postings/postings.csv",
}
ROLES: list[str] = list(ROLE_DATASETS)

COLUMNS = ["role", "skill", "offers_with_skill", "role_offers", "frequency"]

_SPACES = re.compile(r"\s+")
# Only clearly surplus edge punctuation: a leading "." is kept (".net") and
# so are "+" and "#" ("c++", "c#").
_EDGE_PUNCT = re.compile(r"^[\s\"\'`(\[{*,;:!?-]+|[\s\"\'`)\]}*.,;:!?-]+$")


def _clean(raw: str) -> str:
    text = _SPACES.sub(" ", str(raw).strip().lower())
    return _EDGE_PUNCT.sub("", text).strip()


def normalize_skill(raw: str, aliases: dict[str, str]) -> str:
    """Lowercase, collapse spaces, strip edge punctuation, then apply aliases."""
    text = _clean(raw)
    return aliases.get(text, text)


def load_aliases(path: Path | str) -> dict[str, str]:
    """Read a CSV with columns ``alias,skill``; keys and values are normalized."""
    with open(path, newline="", encoding="utf-8") as f:
        return {_clean(r["alias"]): _clean(r["skill"]) for r in csv.DictReader(f)}


def load_exclusions(path: Path | str) -> set[str]:
    """Read a text file, one Skill per line; ``#`` comments and blanks ignored."""
    result = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            result.add(_clean(line))
    return result


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, float) and value != value) or not str(value).strip()


def compute_frequency(
    job_skills_by_role: dict[str, Iterable],
    aliases: dict[str, str],
    exclusions: set[str],
) -> pd.DataFrame:
    """Frequency per (role, skill). Offers with empty/NaN job_skills are not counted."""
    rows = []
    for role, offers in job_skills_by_role.items():
        counts: dict[str, int] = {}
        total = 0
        for value in offers:
            if _is_empty(value):
                continue
            skills = {normalize_skill(s, aliases) for s in str(value).split(",")}
            skills = {s for s in skills if s and s not in exclusions}
            total += 1
            for s in skills:
                counts[s] = counts.get(s, 0) + 1
        for skill, n in counts.items():
            rows.append((role, skill, n, total, 100 * n / total))
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["_neg"] = -df["frequency"]
    df = df.sort_values(["role", "_neg", "skill"]).drop(columns="_neg")
    return df.reset_index(drop=True)


def load_offers(datos_dir: Path | str = DATOS_DIR) -> dict[str, pd.Series]:
    """Read the ``job_skills`` column of each Role's dataset."""
    return {
        role: pd.read_csv(Path(datos_dir) / rel, usecols=["job_skills"])["job_skills"]
        for role, rel in ROLE_DATASETS.items()
    }


def load_frequency_table(path: Path | str = FREQUENCY_CSV) -> dict[str, dict[str, float]]:
    """Read the small CSV: role -> normalized skill -> frequency (%)."""
    table: dict[str, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            table.setdefault(r["role"], {})[r["skill"]] = float(r["frequency"])
    return table
