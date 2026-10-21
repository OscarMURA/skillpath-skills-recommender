"""Regenerate catalog/frequency_by_role.csv from the datasets in datos/.

Usage: .venv/bin/python -m skillpath.build_frequency [--datos DIR] [--out PATH]
       [--min-frequency 1.0] [--top N] [--no-catalog-aliases]
"""

import argparse
from pathlib import Path

from skillpath.frequency import (
    ALIASES_CSV,
    DATOS_DIR,
    EXCLUSIONS_TXT,
    FREQUENCY_CSV,
    compute_frequency,
    load_aliases,
    load_exclusions,
    load_offers,
    normalize_skill,
)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datos", type=Path, default=DATOS_DIR)
    p.add_argument("--out", type=Path, default=FREQUENCY_CSV)
    p.add_argument("--min-frequency", type=float, default=1.0)
    p.add_argument("--top", type=int, default=0, help="print the N most frequent Skills per Role")
    p.add_argument("--raw", action="store_true", help="ignore aliases and exclusions (for review)")
    args = p.parse_args(argv)

    from skillpath.catalog import CATALOG  # always keep Catalog Skills

    aliases = {} if args.raw else load_aliases(ALIASES_CSV)
    exclusions = set() if args.raw else load_exclusions(EXCLUSIONS_TXT)
    offers = load_offers(args.datos)
    df = compute_frequency(offers, aliases, exclusions)

    catalog_names = {normalize_skill(n, aliases) for n in CATALOG}
    keep = (df["frequency"] >= args.min_frequency) | df["skill"].isin(catalog_names)
    out = df[keep].copy()
    out["frequency"] = out["frequency"].round(2)

    if args.top:
        for role, g in df.groupby("role", sort=False):
            print(f"\n{role}: top {args.top}")
            for r in g.head(args.top).itertuples():
                print(f"  {r.frequency:6.2f}%  {r.skill}")

    if not args.raw:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out, index=False)
        print(f"\nEscrito {args.out} ({len(out)} filas)")
    for role, g in df.groupby("role", sort=False):
        print(f"{role}: {g['role_offers'].iloc[0]} Offers con job_skills; {(out['role'] == role).sum()} filas")


if __name__ == "__main__":
    main()
