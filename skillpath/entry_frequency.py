"""Frequency of Catalog Skills in entry-level Offers (arshkon) and detector calibration.

arshkon gives no usable Skills, so Skills are detected in ``description`` with the
dictionary detector (``skill_detection``). The Role comes from the title. The
detector is calibrated against asaniczka (``job_summary`` vs ``job_skills``).
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from skillpath.frequency import (
    CATALOG_DIR,
    COLUMNS,
    DATOS_DIR,
    ROLE_DATASETS,
    ROLES,
    _is_empty,
    normalize_skill,
)
from skillpath.skill_detection import detect_skills

ARSHKON_CSV = DATOS_DIR / "arshkon_linkedin-job-postings" / "postings.csv"
ENTRY_FREQUENCY_CSV = CATALOG_DIR / "frequency_entry_by_role.csv"
CALIBRATION_CSV = CATALOG_DIR / "detection_calibration.csv"

# Entry level = "Entry level" + "Internship" (students and recent graduates).
# "Associate" is left out: asaniczka (the base) is already made of Associate and
# Mid senior Offers, so including it would dilute the contrast.
ENTRY_LEVELS: tuple[str, ...] = ("Entry level", "Internship")
REPORT_LEVELS: tuple[str, ...] = ("Entry level", "Internship", "Associate")

ROLE_TITLE_PATTERNS: dict[str, re.Pattern] = {
    "Data Analyst": re.compile(r"\bdata analyst\b", re.IGNORECASE),
    "Data Scientist": re.compile(r"\bdata scientist\b", re.IGNORECASE),
    "Software Engineer": re.compile(
        r"\bsoftware (?:engineer|developer|development engineer)\b", re.IGNORECASE
    ),
}

CALIBRATION_COLUMNS = [
    "role", "skill", "text_frequency", "skills_frequency", "reference_frequency",
    "diff", "ratio", "reliable",
]
# Reliability thresholds (see detection_calibration in catalog/README.md).
MIN_SKILLS_FREQUENCY = 2.0   # roles where job_skills is informative enough for the ratio
MAX_ABS_DIFF = 10.0          # percentage points, in any Role
RATIO_RANGE = (0.5, 2.0)     # only where skills_frequency >= MIN_SKILLS_FREQUENCY


def role_from_title(title) -> str | None:
    """The Role whose title pattern matches, or None if none or more than one matches."""
    if _is_empty(title):
        return None
    hits = [role for role, pat in ROLE_TITLE_PATTERNS.items() if pat.search(str(title))]
    return hits[0] if len(hits) == 1 else None


def normalize_description(text) -> str:
    """Key for exact-duplicate detection: strip, collapse whitespace, ignore case."""
    return re.sub(r"\s+", " ", str(text).strip()).lower()


def compute_entry_frequency(
    offers: Iterable[tuple[str, str]],
    patterns: dict[str, re.Pattern],
    catalog_names: Iterable[str],
) -> pd.DataFrame:
    """Frequency per (role, skill) over ``(role, description)`` pairs.

    One row per Role in ROLES and per Skill in ``catalog_names`` (also with 0
    Offers), so ``role_offers`` (the sample size) is always present. Offers with
    an empty description are skipped, and so are exact duplicates within a Role
    (same description after ``normalize_description``): each text counts once,
    so the result does not depend on Offer order. Same columns as ``frequency_by_role.csv``.
    """
    skills = sorted(set(catalog_names))
    total = {role: 0 for role in ROLES}
    counts = {role: {s: 0 for s in skills} for role in ROLES}
    sub = {s: patterns[s] for s in skills}
    seen: set[tuple[str, str]] = set()
    for role, description in offers:
        if role not in total or _is_empty(description):
            continue
        key = (role, normalize_description(description))
        if key in seen:
            continue
        seen.add(key)
        total[role] += 1
        for s in detect_skills(description, sub):
            counts[role][s] += 1
    rows = []
    for role in ROLES:
        n = total[role]
        for s in skills:
            c = counts[role][s]
            rows.append((role, s, c, n, round(100 * c / n, 2) if n else 0.0))
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["_neg"] = -df["frequency"]
    df = df.sort_values(["role", "_neg", "skill"]).drop(columns="_neg")
    return df.reset_index(drop=True)


def iter_arshkon(
    path: Path | str = ARSHKON_CSV,
    chunksize: int = 2000,
    tally: dict | None = None,
    unique_tally: dict | None = None,
):
    """Yield ``(role, level, description)`` of Offers whose title matches one Role.

    Reads in chunks (only 3 columns). If ``tally`` is given it accumulates
    ``(role, level)`` -> count over ALL matched Offers, regardless of level;
    ``unique_tally`` does the same counting distinct normalized descriptions
    per ``(role, level)``.
    """
    seen: set[tuple[str, str, str]] = set()
    cols = ["title", "description", "formatted_experience_level"]
    for chunk in pd.read_csv(path, usecols=cols, chunksize=chunksize):
        for title, desc, level in zip(
            chunk["title"], chunk["description"], chunk["formatted_experience_level"]
        ):
            role = role_from_title(title)
            if role is None:
                continue
            level = "" if _is_empty(level) else str(level)
            if tally is not None:
                tally[(role, level)] = tally.get((role, level), 0) + 1
            if unique_tally is not None and not _is_empty(desc):
                key = (role, level, normalize_description(desc))
                if key not in seen:
                    seen.add(key)
                    unique_tally[(role, level)] = unique_tally.get((role, level), 0) + 1
            yield role, level, desc


# ---------------------------------------------------------------- calibration

def _skills_sets(value, aliases, exclusions) -> set[str]:
    skills = {normalize_skill(s, aliases) for s in str(value).split(",")}
    return {s for s in skills if s and s not in exclusions}


def calibrate(
    patterns: dict[str, re.Pattern],
    catalog_names: Iterable[str],
    aliases: dict[str, str],
    exclusions: set[str],
    reference: dict[str, dict[str, float]],
    datos_dir: Path | str = DATOS_DIR,
    chunksize: int = 4000,
    examples: dict | None = None,
) -> pd.DataFrame:
    """Detector (``job_summary``) vs ``job_skills`` on the SAME asaniczka Offers.

    Uses every Offer with non-empty ``job_summary`` and ``job_skills``. If
    ``examples`` is given it is filled with ``(role, skill) -> {"fp": [...], "fn": [...]}``
    offer indexes for manual review.
    """
    skills = sorted(set(catalog_names))
    sub = {s: patterns[s] for s in skills}
    rows = []
    for role, rel in ROLE_DATASETS.items():
        n = 0
        text_c = {s: 0 for s in skills}
        sk_c = {s: 0 for s in skills}
        for chunk in pd.read_csv(
            Path(datos_dir) / rel, usecols=["job_summary", "job_skills"], chunksize=chunksize
        ):
            for summary, js in zip(chunk["job_summary"], chunk["job_skills"]):
                if _is_empty(summary) or _is_empty(js):
                    continue
                n += 1
                found = detect_skills(summary, sub)
                listed = _skills_sets(js, aliases, exclusions)
                for s in found:
                    text_c[s] += 1
                for s in listed & set(skills):
                    sk_c[s] += 1
                if examples is not None:
                    for s in found - listed:
                        examples.setdefault((role, s), {"fp": [], "fn": []})["fp"].append(summary)
                    for s in (listed & set(skills)) - found:
                        examples.setdefault((role, s), {"fp": [], "fn": []})["fn"].append(summary)
        for s in skills:
            t = 100 * text_c[s] / n
            k = 100 * sk_c[s] / n
            rows.append((role, s, t, k, reference.get(role, {}).get(s, 0.0)))
    df = pd.DataFrame(
        rows, columns=["role", "skill", "text_frequency", "skills_frequency", "reference_frequency"]
    )
    df["diff"] = df["text_frequency"] - df["skills_frequency"]
    df["ratio"] = df["text_frequency"] / df["skills_frequency"].where(df["skills_frequency"] > 0)
    df["reliable"] = df["skill"].map(_reliability(df))
    for c in ["text_frequency", "skills_frequency", "reference_frequency", "diff", "ratio"]:
        df[c] = df[c].round(2)
    df["_o"] = df["role"].map({r: i for i, r in enumerate(ROLES)})
    df = df.sort_values(["skill", "_o"]).drop(columns="_o").reset_index(drop=True)
    return df[CALIBRATION_COLUMNS]


def _reliability(df: pd.DataFrame) -> dict[str, bool]:
    """Skill -> reliable?  Unreliable if, in any Role, |diff| > MAX_ABS_DIFF, or, in a
    Role with skills_frequency >= MIN_SKILLS_FREQUENCY, the ratio is outside RATIO_RANGE."""
    result = {}
    for skill, g in df.groupby("skill"):
        bad = (g["diff"].abs() > MAX_ABS_DIFF).any()
        informative = g[g["skills_frequency"] >= MIN_SKILLS_FREQUENCY]
        bad = bad or (
            (informative["ratio"] < RATIO_RANGE[0]) | (informative["ratio"] > RATIO_RANGE[1])
        ).any()
        result[skill] = not bool(bad)
    return result


def unreliable_skills(calibration: pd.DataFrame) -> list[str]:
    ok = calibration.groupby("skill")["reliable"].all()
    return sorted(ok[~ok].index)
