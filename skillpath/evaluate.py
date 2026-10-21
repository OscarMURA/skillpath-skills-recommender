"""Offline evaluation of SkillPath: leave-one-skill-out accuracy and bias metrics.

Usage: .venv/bin/python -m skillpath.evaluate [--datos DIR] [--out reports/]
       [--sample-per-role 500] [--seed 42] [--test-fraction 0.2]

Two separate questions are answered, with two separate sets of artifacts:

1. Accuracy (leave-one-skill-out). The Offers of each Role are split into
   training and test by a stable hash. Frequency and co-occurrence are
   recomputed ONLY from the training Offers (in memory; the versioned files in
   ``catalog/`` are never touched) and injected into ``recommend`` with a
   context manager. For each sampled test Offer one Catalog Skill is hidden and
   we measure where each method ranks it.
2. Bias. Measured on the system as deployed (the versioned artifacts in
   ``catalog/``), over Learner profiles derived from the sampled test Offers and
   a small synthetic grid.

Data leakage: Offers with the same set of Skills (after normalization) share the
partition key, so they always fall on the same side of the split.
"""

import argparse
import csv
import hashlib
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path

import pandas as pd
from scipy import stats

from skillpath import catalog, similarity
from skillpath.cooccurrence import COOCCURRENCE_CSV, compute_cooccurrence
from skillpath.frequency import (
    ALIASES_CSV,
    DATOS_DIR,
    EXCLUSIONS_TXT,
    FREQUENCY_CSV,
    REPO_DIR,
    ROLE_DATASETS,
    ROLES,
    compute_frequency,
    load_aliases,
    load_exclusions,
    normalize_skill,
)
from skillpath.frequency import _is_empty
from skillpath.models import LearnerProfile
from skillpath.recommender import recommend

METHODS = ("popularity", "formula_no_similarity", "full", "random")
GROUPS = ("offers", "synthetic", "all")
KS = (5, 10)
MIN_FREQUENCY = 1.0  # same as build_frequency
MIN_OFFERS = 5  # same as build_cooccurrence
MIN_CATALOG_SKILLS = 2
DEFAULT_OUT = REPO_DIR / "reports"


# --------------------------------------------------------------------------
# Partition
# --------------------------------------------------------------------------

def stable_bucket(key: str) -> float:
    """Deterministic number in [0, 1) from a string (sha1, not Python's hash())."""
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:12], 16) / 16**12


def partition_key(job_link, job_skills, aliases: dict[str, str], exclusions: set[str]) -> str:
    """Key that decides the side of an Offer.

    Offers with the same set of normalized Skills get the same key, so identical
    (template) Offers never straddle the split. Offers without Skills fall back
    to their ``job_link``.
    """
    if not _is_empty(job_skills):
        skills = {normalize_skill(s, aliases) for s in str(job_skills).split(",")}
        skills = sorted(s for s in skills if s and s not in exclusions)
        if skills:
            return "skills:" + "|".join(skills)
    return f"link:{job_link}"


def is_test(key: str, test_fraction: float) -> bool:
    return stable_bucket(key) < test_fraction


def split_offers(
    links: list, job_skills: list, aliases: dict[str, str], exclusions: set[str], test_fraction: float
) -> tuple[list[int], list[int]]:
    """Indices (train, test) of the Offers of one Role."""
    train, test = [], []
    for i, (link, value) in enumerate(zip(links, job_skills)):
        key = partition_key(link, value, aliases, exclusions)
        (test if is_test(key, test_fraction) else train).append(i)
    return train, test


# --------------------------------------------------------------------------
# Training artifacts and injection
# --------------------------------------------------------------------------

def build_training_artifacts(
    train_by_role: dict[str, Iterable],
    aliases: dict[str, str],
    exclusions: set[str],
    catalog_skills,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, dict[str, float]]]]:
    """Frequency and co-occurrence tables computed only from the given Offers.

    Same parameters as ``build_frequency`` (Frequency >= 1 % or Catalog Skill,
    rounded to 2 decimals) and ``build_cooccurrence`` (min_offers=5, Ochiai).
    Returns tables in the format of ``load_frequency_table``/``load_cooccurrence``.
    """
    train_by_role = {role: list(offers) for role, offers in train_by_role.items()}
    df = compute_frequency(train_by_role, aliases, exclusions)
    catalog_names = {normalize_skill(n, aliases) for n in catalog_skills}
    df = df[(df["frequency"] >= MIN_FREQUENCY) | df["skill"].isin(catalog_names)]
    frequency: dict[str, dict[str, float]] = {}
    for r in df.itertuples():
        frequency.setdefault(r.role, {})[r.skill] = round(r.frequency, 2)
    co = compute_cooccurrence(train_by_role, aliases, exclusions, catalog_skills, MIN_OFFERS)
    cooccurrence: dict[str, dict[str, dict[str, float]]] = {}
    for r in co.itertuples():
        role = cooccurrence.setdefault(r.role, {})
        role.setdefault(r.skill_a, {})[r.skill_b] = r.closeness
        role.setdefault(r.skill_b, {})[r.skill_a] = r.closeness
    return frequency, cooccurrence


@contextmanager
def use_artifacts(frequency: dict, cooccurrence: dict) -> Iterator[None]:
    """Make ``recommend`` use the given Frequency and co-occurrence tables.

    Restores everything (and clears the similarity model cache) on exit.
    """
    saved_frequency = catalog.FREQUENCY
    saved_loader = similarity.load_cooccurrence
    similarity.get_model.cache_clear()
    try:
        catalog.FREQUENCY = frequency
        similarity.load_cooccurrence = lambda path=None: cooccurrence
        yield
    finally:
        catalog.FREQUENCY = saved_frequency
        similarity.load_cooccurrence = saved_loader
        similarity.get_model.cache_clear()


@contextmanager
def no_similarity() -> Iterator[None]:
    """Force similarity to 0 (Frequency / Effort + topological adjustment only)."""
    saved = similarity.compute_similarity

    def zero(role, known_skills, interests, candidates):
        return similarity.SimilarityResult(
            {c: 0.0 for c in candidates}, {c: [] for c in candidates}, [], False
        )

    try:
        similarity.compute_similarity = zero
        yield
    finally:
        similarity.compute_similarity = saved


# --------------------------------------------------------------------------
# Metrics (pure functions)
# --------------------------------------------------------------------------

def rank_of(skill: str, ranking: list[str]) -> int:
    """1-based position of ``skill`` in ``ranking``."""
    return ranking.index(skill) + 1


def hit_at_k(ranks: list[int], k: int) -> float:
    return sum(1 for r in ranks if r <= k) / len(ranks) if ranks else float("nan")


def mrr(ranks: list[int]) -> float:
    return sum(1 / r for r in ranks) / len(ranks) if ranks else float("nan")


def gini(values: list[float]) -> float:
    """Gini coefficient: 0 = perfectly even, close to 1 = concentrated."""
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if n == 0 or total == 0:
        return 0.0
    return 2 * sum((i + 1) * x for i, x in enumerate(xs)) / (n * total) - (n + 1) / n


def normalized_entropy(values: list[float]) -> float:
    """Shannon entropy divided by ln(n): 1 = uniform, 0 = a single item."""
    total = sum(values)
    if len(values) < 2 or total == 0:
        return 0.0
    h = -sum((v / total) * math.log(v / total) for v in values if v > 0)
    return h / math.log(len(values))


def top_share(values: list[float], n: int) -> float:
    """Fraction of the total taken by the n largest values."""
    total = sum(values)
    return sum(sorted(values, reverse=True)[:n]) / total if total else 0.0


def jaccard(a: Iterable, b: Iterable) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def coverage(exposed: Iterable[str], all_skills: Iterable[str]) -> float:
    all_skills = set(all_skills)
    return len(set(exposed) & all_skills) / len(all_skills) if all_skills else 0.0


# --------------------------------------------------------------------------
# Offers -> Catalog Skills
# --------------------------------------------------------------------------

def catalog_skills_in_offer(
    value, aliases: dict[str, str], exclusions: set[str], by_normalized: dict[str, str]
) -> list[str]:
    """Sorted Catalog Skills mentioned by an Offer (same normalization as Frequency)."""
    if _is_empty(value):
        return []
    skills = {normalize_skill(s, aliases) for s in str(value).split(",")}
    return sorted(by_normalized[s] for s in skills if s in by_normalized and s not in exclusions)


def popularity_ranking(role: str, known: Iterable[str], frequency: dict, aliases: dict, skills) -> list[str]:
    """Candidates ordered by Frequency of the Role, ties by name."""
    table = frequency.get(role, {})
    known = set(known)
    cands = [n for n in skills if n not in known]
    return sorted(cands, key=lambda n: (-table.get(normalize_skill(n, aliases), 0.0), n))


def learner_from_skills(role: str, known: Iterable[str], experience_level: str = "experienced") -> LearnerProfile:
    return LearnerProfile(
        role=role,
        known_skills={s: "intermediate" for s in sorted(known)},
        interests=[],
        experience_level=experience_level,
    )


def ranking(profile: LearnerProfile) -> list[str]:
    return [i.skill for i in recommend(profile).items]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_role_offers(datos_dir: Path) -> dict[str, tuple[list, list]]:
    out = {}
    for role, rel in ROLE_DATASETS.items():
        df = pd.read_csv(Path(datos_dir) / rel, usecols=["job_link", "job_skills"])
        out[role] = (df["job_link"].tolist(), df["job_skills"].tolist())
    return out


def _f(x) -> str:
    if isinstance(x, float):
        if x != x:
            return ""
        return f"{x:.4f}"
    return str(x)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([_f(r[c]) for c in columns])


def sha1_file(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Step 1: partition + training artifacts + sample of test Offers
# --------------------------------------------------------------------------

def prepare(args, aliases, exclusions, by_normalized):
    data = load_role_offers(args.datos)
    train_values: dict[str, list] = {}
    cases_src: dict[str, list[tuple[int, list[str]]]] = {}
    summary_rows = []
    for role in ROLES:
        links, values = data[role]
        key_fn = lambda i: partition_key(links[i], values[i], aliases, exclusions)  # noqa: E731
        train_idx, test_idx = split_offers(links, values, aliases, exclusions, args.test_fraction)
        train_values[role] = [values[i] for i in train_idx]
        test_values = [values[i] for i in test_idx]

        # Residual leakage: test Offers whose Skill set equals that of a training Offer.
        train_keys = {key_fn(i) for i in train_idx if key_fn(i).startswith("skills:")}
        leak_chosen = sum(1 for i in test_idx if key_fn(i) in train_keys)
        alt_train = [i for i in range(len(values)) if stable_bucket(f"link:{links[i]}") >= args.test_fraction]
        alt_test = [i for i in range(len(values)) if stable_bucket(f"link:{links[i]}") < args.test_fraction]
        alt_keys = {key_fn(i) for i in alt_train if key_fn(i).startswith("skills:")}
        leak_alt = sum(1 for i in alt_test if key_fn(i) in alt_keys)
        groups = Counter(key_fn(i) for i in range(len(values)) if key_fn(i).startswith("skills:"))
        largest_group = max(groups.values()) if groups else 0

        eligible = []
        empty_test = 0
        for pos, i in enumerate(test_idx):
            if _is_empty(values[i]):
                empty_test += 1
                continue
            present = catalog_skills_in_offer(values[i], aliases, exclusions, by_normalized)
            if len(present) >= MIN_CATALOG_SKILLS:
                eligible.append((i, present))
        rng = random.Random(f"{args.seed}:{role}:sample")
        n_sample = min(args.sample_per_role, len(eligible))
        picked = sorted(rng.sample(range(len(eligible)), n_sample))
        cases_src[role] = [eligible[p] for p in picked]
        train_catalog_sets = {
            tuple(catalog_skills_in_offer(values[i], aliases, exclusions, by_normalized)) for i in train_idx
        }
        seen_in_train = sum(1 for _, present in cases_src[role] if tuple(present) in train_catalog_sets)
        summary_rows.append(
            {
                "role": role,
                "offers_total": len(values),
                "offers_empty_job_skills": sum(1 for v in values if _is_empty(v)),
                "train": len(train_idx),
                "test": len(test_idx),
                "test_empty_job_skills": empty_test,
                "test_with_lt2_catalog_skills": len(test_idx) - empty_test - len(eligible),
                "test_eligible": len(eligible),
                "test_sampled": n_sample,
                "largest_duplicate_group": largest_group,
                "test_identical_skills_in_train": leak_chosen,
                "test_identical_skills_in_train_if_link_hash": leak_alt,
                "sampled_catalog_set_seen_in_train": seen_in_train,
            }
        )
    frequency, cooccurrence = build_training_artifacts(train_values, aliases, exclusions, catalog.CATALOG)
    return frequency, cooccurrence, cases_src, summary_rows, data


# --------------------------------------------------------------------------
# Step 2: leave-one-skill-out
# --------------------------------------------------------------------------

def run_loo(args, frequency, cooccurrence, cases_src, aliases):
    skills = list(catalog.CATALOG)
    cases = []  # (role, known, hidden, rng_random_ranking)
    for role in ROLES:
        hide_rng = random.Random(f"{args.seed}:{role}:hide")
        rand_rng = random.Random(f"{args.seed}:{role}:random")
        for _, present in cases_src[role]:
            hidden = hide_rng.choice(present)
            known = [s for s in present if s != hidden]
            cands = sorted(n for n in skills if n not in known)
            rand_rng.shuffle(cands)
            cases.append((role, known, hidden, cands))

    rows = []  # one per (case, method): role, method, rank, ncand, difficulty
    with use_artifacts(frequency, cooccurrence):
        for role, known, hidden, rand_order in cases:
            profile = learner_from_skills(role, known)
            full = ranking(profile)
            with no_similarity():
                nosim = ranking(profile)
            pop = popularity_ranking(role, known, frequency, aliases, skills)
            for method, order in (
                ("popularity", pop),
                ("formula_no_similarity", nosim),
                ("full", full),
                ("random", rand_order),
            ):
                rows.append((role, method, rank_of(hidden, order), len(order), catalog.CATALOG[hidden].difficulty))
    return rows


def loo_tables(rows):
    metrics = []
    for role in [*ROLES, "GLOBAL"]:
        for method in METHODS:
            sel = [r for r in rows if r[1] == method and (role == "GLOBAL" or r[0] == role)]
            ranks = [r[2] for r in sel]
            metrics.append(
                {
                    "role": role,
                    "method": method,
                    "n": len(ranks),
                    "hit_at_5": hit_at_k(ranks, 5),
                    "hit_at_10": hit_at_k(ranks, 10),
                    "mrr": mrr(ranks),
                    "mean_rank": statistics.fmean(ranks),
                    "median_rank": float(statistics.median(ranks)),
                    "mean_candidates": statistics.fmean(r[3] for r in sel),
                }
            )
    by_diff = []
    for d in range(1, 6):
        for method in METHODS:
            ranks = [r[2] for r in rows if r[1] == method and r[4] == d]
            if not ranks:
                continue
            by_diff.append(
                {
                    "difficulty": d,
                    "method": method,
                    "n": len(ranks),
                    "hit_at_10": hit_at_k(ranks, 10),
                    "mrr": mrr(ranks),
                    "mean_rank": statistics.fmean(ranks),
                }
            )
    return metrics, by_diff


# --------------------------------------------------------------------------
# Step 3: bias (deployed artifacts)
# --------------------------------------------------------------------------

def synthetic_profiles(role: str) -> list[list[str]]:
    """Empty profile, the 5 most frequent Catalog Skills alone, and their 10 pairs."""
    table = catalog.FREQUENCY[role]
    top = sorted(
        catalog.CATALOG,
        key=lambda n: (-table.get(normalize_skill(n, catalog.ALIASES), 0.0), n),
    )[:5]
    return [[], *[[s] for s in top], *[list(p) for p in combinations(sorted(top), 2)]]


def bias_rankings(cases_src, aliases):
    """role -> group -> list of (ranking_experienced, ranking_entry) for deployed artifacts."""
    similarity.get_model.cache_clear()
    out: dict[str, dict[str, list]] = {}
    for role in ROLES:
        groups = {"offers": [], "synthetic": []}
        for group, known_sets in (
            ("offers", [present for _, present in cases_src[role]]),
            ("synthetic", synthetic_profiles(role)),
        ):
            for known in known_sets:
                exp = ranking(learner_from_skills(role, known, "experienced"))
                ent = ranking(learner_from_skills(role, known, "entry"))
                groups[group].append((exp, ent))
        groups["all"] = groups["offers"] + groups["synthetic"]
        out[role] = groups
    return out


def exposure(rankings: list[list[str]], k: int, skills: list[str]) -> dict[str, float]:
    """Share of the top-k slots taken by each Skill (sums to 1)."""
    counts = Counter(s for r in rankings for s in r[:k])
    total = sum(counts.values())
    return {s: counts.get(s, 0) / total if total else 0.0 for s in skills}


def bias_tables(bias, aliases):
    skills = sorted(catalog.CATALOG)
    concentration, by_category, cov, never, by_diff, vs_freq = [], [], [], [], [], []
    comparison, shifts = [], []
    categories = sorted({s.category for s in catalog.CATALOG.values()})
    for k in KS:
        # Global rows (pooled over Roles) are added as role "GLOBAL".
        for group in GROUPS:
            pooled_exposed: set[str] = set()
            pooled_rank_lists: list[list[str]] = []
            for role in [*ROLES, "GLOBAL"]:
                lists = (
                    pooled_rank_lists if role == "GLOBAL" else [e for e, _ in bias[role][group]]
                )
                if role != "GLOBAL":
                    pooled_rank_lists = pooled_rank_lists + lists
                exp = exposure(lists, k, skills)
                vec = [exp[s] for s in skills]
                concentration.append(
                    {
                        "role": role, "group": group, "k": k, "profiles": len(lists),
                        "top5_share": top_share(vec, 5), "top10_share": top_share(vec, 10),
                        "gini": gini(vec), "norm_entropy": normalized_entropy(vec),
                    }
                )
                for cat in categories:
                    members = [s for s in skills if catalog.CATALOG[s].category == cat]
                    by_category.append(
                        {
                            "role": role, "group": group, "k": k, "category": cat,
                            "catalog_skills": len(members),
                            "catalog_share": len(members) / len(skills),
                            "exposure_share": sum(exp[s] for s in members),
                        }
                    )
                for d in range(1, 6):
                    members = [s for s in skills if catalog.CATALOG[s].difficulty == d]
                    if not members:
                        continue
                    by_diff.append(
                        {
                            "role": role, "group": group, "k": k, "difficulty": d,
                            "catalog_skills": len(members),
                            "catalog_share": len(members) / len(skills),
                            "exposure_share": sum(exp[s] for s in members),
                        }
                    )
                shown = {s for s in skills if exp[s] > 0}
                cov.append(
                    {
                        "role": role, "group": group, "k": k, "skills_shown": len(shown),
                        "coverage": coverage(shown, skills),
                    }
                )
                if k == 10 and group == "all":
                    for s in skills:
                        if s not in shown:
                            never.append({"role": role, "skill": s,
                                          "category": catalog.CATALOG[s].category,
                                          "difficulty": catalog.CATALOG[s].difficulty})
                if role != "GLOBAL":
                    table = catalog.FREQUENCY[role]
                    freqs = [table.get(normalize_skill(s, aliases), 0.0) for s in skills]
                    rho = stats.spearmanr(vec, freqs).statistic
                    vs_freq.append({"role": role, "group": group, "k": k, "spearman": float(rho)})

    # Entry-level vs experienced (same profiles).
    for role in ROLES:
        for group in GROUPS:
            pairs = bias[role][group]
            for k in KS:
                jac = [jaccard(e[:k], n[:k]) for e, n in pairs]
                taus, rhos = [], []
                for e, n in pairs:
                    order = sorted(e)
                    re_ = {s: i for i, s in enumerate(e)}
                    rn_ = {s: i for i, s in enumerate(n)}
                    a = [re_[s] for s in order]
                    b = [rn_[s] for s in order]
                    taus.append(stats.kendalltau(a, b).statistic)
                    rhos.append(stats.spearmanr(a, b).statistic)
                comparison.append(
                    {
                        "role": role, "group": group, "k": k, "profiles": len(pairs),
                        "mean_jaccard": statistics.fmean(jac),
                        "mean_kendall_tau": statistics.fmean(taus),
                        "mean_spearman": statistics.fmean(rhos),
                    }
                )
        pairs = bias[role]["all"]
        exp10 = exposure([e for e, _ in pairs], 10, skills)
        ent10 = exposure([n for _, n in pairs], 10, skills)
        for s in skills:
            pos_e = [e.index(s) + 1 for e, _ in pairs if s in e]
            pos_n = [n.index(s) + 1 for _, n in pairs if s in n]
            me = statistics.fmean(pos_e) if pos_e else float("nan")
            mn = statistics.fmean(pos_n) if pos_n else float("nan")
            shifts.append(
                {
                    "role": role, "skill": s,
                    "exposure10_experienced": exp10[s], "exposure10_entry": ent10[s],
                    "exposure10_delta": ent10[s] - exp10[s],
                    "mean_rank_experienced": me, "mean_rank_entry": mn,
                    "mean_rank_delta": mn - me,
                }
            )
    shifts.sort(key=lambda r: (ROLES.index(r["role"]), -r["exposure10_delta"], r["skill"]))
    return {
        "concentration": concentration, "by_category": by_category, "coverage": cov,
        "never": never, "by_difficulty": by_diff, "vs_freq": vs_freq,
        "comparison": comparison, "shifts": shifts,
    }


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def write_all(out: Path, summary_rows, metrics, loo_diff, b) -> None:
    write_csv(out / "partition_summary.csv", list(summary_rows[0]), summary_rows)
    write_csv(out / "loo_metrics.csv", list(metrics[0]), metrics)
    write_csv(out / "loo_by_difficulty.csv", list(loo_diff[0]), loo_diff)
    write_csv(out / "exposure_concentration.csv", list(b["concentration"][0]), b["concentration"])
    write_csv(out / "exposure_by_category.csv", list(b["by_category"][0]), b["by_category"])
    write_csv(out / "exposure_by_difficulty.csv", list(b["by_difficulty"][0]), b["by_difficulty"])
    write_csv(out / "coverage.csv", list(b["coverage"][0]), b["coverage"])
    write_csv(out / "never_recommended.csv", ["role", "skill", "category", "difficulty"], b["never"])
    write_csv(out / "entry_vs_experienced.csv", list(b["comparison"][0]), b["comparison"])
    write_csv(out / "entry_vs_experienced_shifts.csv", list(b["shifts"][0]), b["shifts"])
    write_csv(out / "exposure_vs_frequency.csv", list(b["vs_freq"][0]), b["vs_freq"])


def print_summary(summary_rows, metrics, loo_diff, b) -> None:
    print("\n== Partición ==")
    for r in summary_rows:
        print(
            f"{r['role']}: {r['offers_total']} Offers, train {r['train']}, test {r['test']} "
            f"(elegibles {r['test_eligible']}, muestreadas {r['test_sampled']}); "
            f"fuga por job_skills idéntico: {r['test_identical_skills_in_train']} "
            f"(con hash de job_link sería {r['test_identical_skills_in_train_if_link_hash']})"
        )
    print("\n== Leave-one-skill-out ==")
    print(f"{'role':18}{'method':24}{'n':>5}{'hit@5':>8}{'hit@10':>8}{'MRR':>8}{'mean':>7}{'median':>7}")
    for m in metrics:
        print(
            f"{m['role']:18}{m['method']:24}{m['n']:>5}{m['hit_at_5']:>8.3f}{m['hit_at_10']:>8.3f}"
            f"{m['mrr']:>8.3f}{m['mean_rank']:>7.1f}{m['median_rank']:>7.1f}"
        )
    print("\nhit@10 por Difficulty de la Skill oculta (global)")
    for d in range(1, 6):
        row = {r["method"]: r for r in loo_diff if r["difficulty"] == d}
        if row:
            print(f"  D{d} (n={row['full']['n']}): " + ", ".join(f"{m}={row[m]['hit_at_10']:.3f}" for m in METHODS))
    print("\n== Sesgo (artefactos desplegados), K=10, grupo 'all' ==")
    for c in b["concentration"]:
        if c["k"] == 10 and c["group"] == "all":
            cv = next(x for x in b["coverage"] if (x["role"], x["group"], x["k"]) == (c["role"], "all", 10))
            print(
                f"{c['role']:18} top5={c['top5_share']:.3f} top10={c['top10_share']:.3f} "
                f"gini={c['gini']:.3f} H={c['norm_entropy']:.3f} cobertura={cv['coverage']:.3f}"
            )
    for role in ROLES:
        nev = [r["skill"] for r in b["never"] if r["role"] == role]
        print(f"  nunca recomendadas ({role}): {', '.join(nev) or '-'}")
    for c in b["comparison"]:
        if c["k"] == 10 and c["group"] == "all":
            print(
                f"  inicial vs experiencia {c['role']}: Jaccard@10={c['mean_jaccard']:.3f} "
                f"tau={c['mean_kendall_tau']:.3f} spearman={c['mean_spearman']:.3f}"
            )
    for role in ROLES:
        sh = [r for r in b["shifts"] if r["role"] == role]
        up = ", ".join(f"{r['skill']} ({r['exposure10_delta']:+.3f})" for r in sh[:3])
        down = ", ".join(f"{r['skill']} ({r['exposure10_delta']:+.3f})" for r in sh[::-1][:3])
        print(f"  {role}: sube con nivel inicial: {up}; baja: {down}")
    for v in b["vs_freq"]:
        if v["k"] == 10 and v["group"] == "all":
            print(f"  Spearman exposición-Frequency {v['role']}: {v['spearman']:.3f}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datos", type=Path, default=DATOS_DIR)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--sample-per-role", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--test-fraction", type=float, default=0.2)
    args = p.parse_args(argv)

    t0 = time.time()
    before = {path: sha1_file(path) for path in (FREQUENCY_CSV, COOCCURRENCE_CSV)}
    aliases = load_aliases(ALIASES_CSV)
    exclusions = load_exclusions(EXCLUSIONS_TXT)
    by_normalized = {normalize_skill(n, aliases): n for n in catalog.CATALOG}

    frequency, cooccurrence, cases_src, summary_rows, _ = prepare(args, aliases, exclusions, by_normalized)
    rows = run_loo(args, frequency, cooccurrence, cases_src, aliases)
    metrics, loo_diff = loo_tables(rows)
    bias = bias_rankings(cases_src, aliases)
    b = bias_tables(bias, aliases)
    write_all(args.out, summary_rows, metrics, loo_diff, b)
    print_summary(summary_rows, metrics, loo_diff, b)

    after = {path: sha1_file(path) for path in before}
    if before != after:
        raise SystemExit("ERROR: los artefactos versionados de catalog/ cambiaron durante la evaluación")
    print(f"\nArtefactos de catalog/ intactos. CSV escritos en {args.out}. {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
