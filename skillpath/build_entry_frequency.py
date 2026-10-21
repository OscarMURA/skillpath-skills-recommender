"""Regenerate catalog/frequency_entry_by_role.csv and catalog/detection_calibration.csv.

Usage: .venv/bin/python -m skillpath.build_entry_frequency [--datos DIR] [--out PATH]
       [--levels "Entry level" "Internship"] [--calibration-out PATH] [--skip-calibration]

1. Calibrates the text detector against asaniczka (job_summary vs job_skills) and
   drops the Skills whose detection is unreliable (or reads the saved calibration
   with --skip-calibration).
2. Reads arshkon in chunks, keeps Offers whose title matches one Role and whose
   level is in --levels, detects Catalog Skills in ``description`` and writes the CSV.
"""

import argparse
from pathlib import Path

import pandas as pd

from skillpath.catalog import CATALOG
from skillpath.entry_frequency import (
    ARSHKON_CSV,
    CALIBRATION_CSV,
    ENTRY_FREQUENCY_CSV,
    ENTRY_LEVELS,
    REPORT_LEVELS,
    calibrate,
    compute_entry_frequency,
    iter_arshkon,
    unreliable_skills,
)
from skillpath.frequency import (
    ALIASES_CSV,
    DATOS_DIR,
    EXCLUSIONS_TXT,
    FREQUENCY_CSV,
    ROLES,
    load_aliases,
    load_exclusions,
    load_frequency_table,
    normalize_skill,
)
from skillpath.skill_detection import build_patterns


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datos", type=Path, default=DATOS_DIR)
    p.add_argument("--out", type=Path, default=ENTRY_FREQUENCY_CSV)
    p.add_argument("--levels", nargs="+", default=list(ENTRY_LEVELS))
    p.add_argument("--calibration-out", type=Path, default=CALIBRATION_CSV)
    p.add_argument("--skip-calibration", action="store_true", help="read the saved calibration")
    p.add_argument("--top", type=int, default=10, help="print the N most frequent Skills per Role")
    args = p.parse_args(argv)

    aliases = load_aliases(ALIASES_CSV)
    exclusions = load_exclusions(EXCLUSIONS_TXT)
    catalog_names = sorted({normalize_skill(n, aliases) for n in CATALOG})
    patterns = build_patterns(catalog_names, aliases)

    if args.skip_calibration:
        calibration = pd.read_csv(args.calibration_out)
    else:
        reference = load_frequency_table(FREQUENCY_CSV)
        calibration = calibrate(patterns, catalog_names, aliases, exclusions, reference, args.datos)
        args.calibration_out.parent.mkdir(parents=True, exist_ok=True)
        calibration.to_csv(args.calibration_out, index=False)
        print(f"Escrito {args.calibration_out} ({len(calibration)} filas)")
    excluded = unreliable_skills(calibration)
    reliable = [s for s in catalog_names if s not in excluded]
    print(f"Skills no fiables excluidas ({len(excluded)}): {', '.join(excluded) or '-'}")

    tally: dict = {}
    unique_tally: dict = {}
    arshkon = args.datos / ARSHKON_CSV.relative_to(DATOS_DIR)
    levels = set(args.levels)
    offers = (
        (role, desc)
        for role, level, desc in iter_arshkon(arshkon, tally=tally, unique_tally=unique_tally)
        if level in levels
    )
    df = compute_entry_frequency(offers, patterns, reliable)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"\nEscrito {args.out} ({len(df)} filas); niveles usados: {', '.join(args.levels)}")

    print("\nOffers de arshkon por Role y nivel: total -> descripciones distintas (por nivel):")
    for role in ROLES:
        parts = [
            f"{lv}={tally.get((role, lv), 0)}->{unique_tally.get((role, lv), 0)}"
            for lv in REPORT_LEVELS
        ]
        before = sum(tally.get((role, lv), 0) for lv in args.levels)
        used = int(df.loc[df["role"] == role, "role_offers"].iloc[0])
        print(f"  {role}: {', '.join(parts)}")
        print(f"    nivel inicial ({', '.join(args.levels)}): antes={before}, despues de deduplicar por Role={used}")

    for role in ROLES:
        g = df[df["role"] == role].head(args.top)
        print(f"\n{role}: top {args.top} (n={int(g['role_offers'].iloc[0])})")
        for r in g.itertuples():
            print(f"  {r.frequency:6.2f}%  {r.skill}")


if __name__ == "__main__":
    main()
