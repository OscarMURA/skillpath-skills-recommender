"""Regenerate catalog/cooccurrence.csv from the datasets in datos/.

Usage: .venv/bin/python -m skillpath.build_cooccurrence [--datos DIR] [--out PATH]
       [--min-offers 5]
"""

import argparse
from pathlib import Path

from skillpath.cooccurrence import COOCCURRENCE_CSV, compute_cooccurrence
from skillpath.frequency import (
    ALIASES_CSV,
    DATOS_DIR,
    EXCLUSIONS_TXT,
    SKILLS_CSV,
    load_aliases,
    load_exclusions,
    load_offers,
)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datos", type=Path, default=DATOS_DIR)
    p.add_argument("--out", type=Path, default=COOCCURRENCE_CSV)
    p.add_argument("--min-offers", type=int, default=5, help="drop pairs with fewer Offers together")
    args = p.parse_args(argv)

    from skillpath.catalog import load_catalog

    catalog = load_catalog(SKILLS_CSV)
    df = compute_cooccurrence(
        load_offers(args.datos),
        load_aliases(ALIASES_CSV),
        load_exclusions(EXCLUSIONS_TXT),
        catalog,
        min_offers=args.min_offers,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Escrito {args.out} ({len(df)} filas, {args.out.stat().st_size / 1024:.1f} KB)")
    for role, g in df.groupby("role", sort=False):
        print(f"{role}: {len(g)} pares")


if __name__ == "__main__":
    main()
