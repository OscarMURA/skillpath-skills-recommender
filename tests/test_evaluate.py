"""Fast tests for skillpath.evaluate (small in-memory fixtures; no datos/, no full run)."""

import math

import pytest

from skillpath import catalog, similarity
from skillpath.evaluate import (
    build_training_artifacts,
    coverage,
    gini,
    hit_at_k,
    is_test,
    jaccard,
    mrr,
    no_similarity,
    normalized_entropy,
    partition_key,
    popularity_ranking,
    rank_of,
    split_offers,
    stable_bucket,
    top_share,
    use_artifacts,
)
from skillpath.frequency import compute_frequency
from skillpath.models import LearnerProfile
from skillpath.recommender import recommend

ALIASES: dict[str, str] = {}
EXCLUSIONS: set[str] = set()


def offers(n: int, template: str = "a{i}, python, sql") -> tuple[list[str], list[str]]:
    links = [f"link-{i}" for i in range(n)]
    values = [template.format(i=i) for i in range(n)]
    return links, values


def test_stable_bucket_is_deterministic_and_in_range():
    assert stable_bucket("x") == stable_bucket("x")
    assert all(0 <= stable_bucket(str(i)) < 1 for i in range(200))
    # Known sha1 prefix: protects against switching to Python's randomized hash().
    assert stable_bucket("abc") == int("a9993e364706", 16) / 16**12


def test_split_is_deterministic_disjoint_and_complete():
    links, values = offers(500)
    t1, s1 = split_offers(links, values, ALIASES, EXCLUSIONS, 0.2)
    t2, s2 = split_offers(links, values, ALIASES, EXCLUSIONS, 0.2)
    assert (t1, s1) == (t2, s2)
    assert not set(t1) & set(s1)
    assert sorted(t1 + s1) == list(range(500))
    assert 60 < len(s1) < 140  # about 20 %


def test_identical_offers_fall_on_the_same_side():
    # 40 Offers with the same Skill set (different order, case and links) + 200 distinct ones.
    links = [f"d{i}" for i in range(40)] + [f"u{i}" for i in range(200)]
    values = [("Python, SQL" if i % 2 else "sql,python ") for i in range(40)]
    values += [f"python, tool{i}" for i in range(200)]
    train, test = split_offers(links, values, ALIASES, EXCLUSIONS, 0.2)
    sides = {i in set(test) for i in range(40)}
    assert len(sides) == 1


def test_partition_key_ignores_exclusions_order_and_aliases():
    aliases = {"py": "python"}
    k1 = partition_key("l1", "py, SQL, teamwork", aliases, {"teamwork"})
    k2 = partition_key("l2", "sql,python", aliases, {"teamwork"})
    assert k1 == k2
    assert partition_key("l3", None, aliases, set()) == "link:l3"
    assert is_test(k1, 1.0) and not is_test(k1, 0.0)


def test_training_artifact_excludes_test_offers():
    links, values = offers(300)
    # "rustonly" appears only in test Offers.
    train_idx, test_idx = split_offers(links, values, ALIASES, EXCLUSIONS, 0.2)
    values = list(values)
    for i in test_idx:
        values[i] += ", rustonly"
    train_values = [values[i] for i in train_idx]
    cat = {"python": None, "sql": None, "rustonly": None}
    freq, cooc = build_training_artifacts({"R": train_values}, ALIASES, EXCLUSIONS, cat)
    assert "rustonly" not in freq["R"]
    assert all("rustonly" not in (a, b) for a in cooc["R"] for b in cooc["R"][a])
    assert "rustonly" not in cooc["R"]
    # Counts match a computation made from the training Offers alone.
    ref = compute_frequency({"R": train_values}, ALIASES, EXCLUSIONS)
    ref = ref[ref["skill"] == "python"].iloc[0]
    assert ref["role_offers"] == len(train_idx)
    assert freq["R"]["python"] == round(ref["frequency"], 2) == 100.0
    # sql and python co-occur in every training Offer; Ochiai closeness is 1.
    assert cooc["R"]["python"]["sql"] == 1.0


def test_training_artifact_keeps_catalog_skills_below_threshold():
    values = ["python"] * 199 + ["python, sql"]  # sql = 0.5 % < 1 %
    freq, _ = build_training_artifacts({"R": values}, ALIASES, EXCLUSIONS, {"python": None, "sql": None})
    assert freq["R"]["sql"] == 0.5


def test_use_artifacts_restores_frequency_cooccurrence_and_recommend():
    profile = LearnerProfile("Data Analyst", {"python": "intermediate"})
    similarity.get_model.cache_clear()
    before = [(i.skill, i.frequency, i.similarity) for i in recommend(profile).items]
    original_freq = catalog.FREQUENCY
    original_loader = similarity.load_cooccurrence
    fake_freq = {"Data Analyst": {"sql": 90.0}}
    fake_cooc = {"Data Analyst": {"sql": {"excel": 0.9}, "excel": {"sql": 0.9}}}
    with use_artifacts(fake_freq, fake_cooc):
        assert catalog.FREQUENCY is fake_freq
        assert similarity.load_cooccurrence(None) is fake_cooc
        inside = recommend(profile).items
        assert next(i for i in inside if i.skill == "sql").frequency == 90.0
    assert catalog.FREQUENCY is original_freq
    assert similarity.load_cooccurrence is original_loader
    after = [(i.skill, i.frequency, i.similarity) for i in recommend(profile).items]
    assert before == after


def test_use_artifacts_restores_on_exception():
    original = catalog.FREQUENCY
    with pytest.raises(RuntimeError):
        with use_artifacts({"Data Analyst": {}}, {}):
            raise RuntimeError("boom")
    assert catalog.FREQUENCY is original


def test_no_similarity_zeroes_scores_and_restores():
    profile = LearnerProfile("Data Analyst", {"python": "intermediate"})
    original = similarity.compute_similarity
    with no_similarity():
        items = recommend(profile).items
        assert all(i.similarity == 0.0 for i in items)
    assert similarity.compute_similarity is original
    assert any(i.similarity > 0 for i in recommend(profile).items)


def test_popularity_ranking_orders_by_frequency_then_name_and_drops_known():
    freq = {"R": {"b": 10.0, "a": 10.0, "c": 50.0}}
    assert popularity_ranking("R", ["c"], freq, ALIASES, ["a", "b", "c", "d"]) == ["a", "b", "d"]


def test_hit_and_mrr_by_hand():
    ranks = [1, 2, 5, 10, 20]
    assert hit_at_k(ranks, 5) == pytest.approx(3 / 5)
    assert hit_at_k(ranks, 10) == pytest.approx(4 / 5)
    assert mrr(ranks) == pytest.approx((1 + 1 / 2 + 1 / 5 + 1 / 10 + 1 / 20) / 5)
    assert rank_of("c", ["a", "b", "c"]) == 3


def test_gini_entropy_share_coverage_jaccard_by_hand():
    assert gini([1, 1, 1, 1]) == pytest.approx(0.0)
    assert gini([0, 0, 0, 4]) == pytest.approx(0.75)
    assert gini([0, 0]) == 0.0
    assert normalized_entropy([1, 1, 1, 1]) == pytest.approx(1.0)
    assert normalized_entropy([0, 0, 5, 0]) == pytest.approx(0.0)
    assert normalized_entropy([1, 1, 0, 0]) == pytest.approx(math.log(2) / math.log(4))
    assert top_share([5, 3, 1, 1], 2) == pytest.approx(0.8)
    assert coverage(["a", "b", "z"], ["a", "b", "c", "d"]) == pytest.approx(0.5)
    assert jaccard(["a", "b", "c"], ["b", "c", "d"]) == pytest.approx(2 / 4)
    assert jaccard([], []) == 1.0
