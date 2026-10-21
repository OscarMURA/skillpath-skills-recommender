"""Co-occurrence of Catalog Skills in the Offers of each Role.

Two Catalog Skills co-occur when the same Offer mentions both (after the same
normalization and aliases used for Frequency). Closeness is the Ochiai
coefficient (cosine between the two binary "appears in Offer i" vectors):

    closeness(a, b) = offers_together / sqrt(offers_a * offers_b)

It is symmetric and lies in [0, 1]. Unlike offers_together / offers_a it does not
make everything close to python, and unlike Jaccard it does not bury a rare Skill
whose Offers nearly always also mention a frequent one (pandas -> python).
Pairs are stored once, in canonical order (skill_a < skill_b alphabetically).
"""

import csv
import math
from collections import defaultdict
from collections.abc import Iterable
from itertools import combinations
from pathlib import Path

import pandas as pd

from skillpath.frequency import CATALOG_DIR, _is_empty, normalize_skill

COOCCURRENCE_CSV = CATALOG_DIR / "cooccurrence.csv"
COLUMNS = ["role", "skill_a", "skill_b", "offers_together", "closeness"]


def compute_cooccurrence(
    job_skills_by_role: dict[str, Iterable],
    aliases: dict[str, str],
    exclusions: set[str],
    catalog_names: Iterable[str],
    min_offers: int = 1,
) -> pd.DataFrame:
    """Co-occurrence of Catalog Skills per Role, one row per unordered pair.

    Offers with empty/NaN ``job_skills`` are ignored; each Offer counts once per
    pair. ``catalog_names`` are mapped with the same normalization as Offers and
    the output uses the Catalog spelling. Pairs with fewer than ``min_offers``
    Offers together are dropped (to keep the file small).
    """
    by_normalized = {normalize_skill(n, aliases): n for n in catalog_names}
    rows = []
    for role, offers in job_skills_by_role.items():
        singles: dict[str, int] = defaultdict(int)
        pairs: dict[tuple[str, str], int] = defaultdict(int)
        for value in offers:
            if _is_empty(value):
                continue
            skills = {normalize_skill(s, aliases) for s in str(value).split(",")}
            present = sorted(
                by_normalized[s] for s in skills if s in by_normalized and s not in exclusions
            )
            for s in present:
                singles[s] += 1
            for pair in combinations(present, 2):
                pairs[pair] += 1
        for (a, b), n in pairs.items():
            if n < min_offers:
                continue
            rows.append((role, a, b, n, round(n / math.sqrt(singles[a] * singles[b]), 4)))
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.sort_values(["role", "skill_a", "skill_b"]).reset_index(drop=True)


def load_cooccurrence(path: Path | str = COOCCURRENCE_CSV) -> dict[str, dict[str, dict[str, float]]]:
    """Read the CSV: role -> skill -> neighbour -> closeness (both directions)."""
    table: dict[str, dict[str, dict[str, float]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = float(r["closeness"])
            role = table.setdefault(r["role"], {})
            role.setdefault(r["skill_a"], {})[r["skill_b"]] = c
            role.setdefault(r["skill_b"], {})[r["skill_a"]] = c
    return table
