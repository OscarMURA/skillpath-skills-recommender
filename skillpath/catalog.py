"""Catalog curado de Skills (catalog/skills.csv) y Frequency real por Role.

El Catalog se carga desde el CSV versionado; la Frequency (% de las Offers del
Role que mencionan la Skill) se lee de catalog/frequency_by_role.csv.
"""

import csv
from pathlib import Path


from skillpath.frequency import (
    ALIASES_CSV,
    FREQUENCY_CSV,
    ROLES,
    SKILLS_CSV,
    load_aliases,
    load_frequency_table,
)
from skillpath.models import Skill

__all__ = ["CATALOG", "FREQUENCY", "ALIASES", "ROLES", "SKILLS_CSV", "load_catalog"]

def load_catalog(path: Path) -> dict[str, Skill]:
    """Read the Catalog CSV (name,category,description,difficulty,prerequisites,reviewed).

    Prerequisites are separated by ``;`` (empty -> no Prerequisites).
    """
    catalog: dict[str, Skill] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            prerequisites = tuple(
                p.strip() for p in row["prerequisites"].split(";") if p.strip()
            )
            catalog[row["name"]] = Skill(
                name=row["name"],
                category=row["category"],
                description=row["description"],
                difficulty=int(row["difficulty"]),
                prerequisites=prerequisites,
                reviewed=row["reviewed"].strip().lower() == "true",
            )
    return catalog


# Curated Catalog (~60 Skills), read from catalog/skills.csv. Names are already
# normalized, as in the Frequency table.
CATALOG: dict[str, Skill] = load_catalog(SKILLS_CSV)

# Frequency (% of the Role's Offers mentioning the Skill), read once from the
# versioned table. Empty if the table has not been generated yet (the build
# command imports this module before writing it).
FREQUENCY: dict[str, dict[str, float]] = (
    load_frequency_table(FREQUENCY_CSV) if FREQUENCY_CSV.exists() else {}
)

# Skill name aliases, used to look Catalog names up in the Frequency table.
ALIASES: dict[str, str] = load_aliases(ALIASES_CSV)
