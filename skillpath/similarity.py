"""Similarity between Skills, Learner profile and candidates (TF-IDF + cosine).

Each Catalog Skill becomes a small text document (tokens, not prose):

* its own name token (``machine learning`` -> ``machine_learning``), x2;
* its category token (``cat_<category>``), x2;
* the words of its Catalog description (Spanish stopwords removed; mentions of
  other Catalog Skills collapse to their name token);
* the name tokens of its top-K neighbours by co-occurrence closeness in the
  Role's Offers, each repeated ``max(1, round(N * closeness / best_closeness))``.

One TfidfVectorizer per Role is fitted ONLY on those 64 documents (sublinear tf,
l2 norm), so the result is deterministic and needs no external model (ADR 0003).
See docs/similarity.md.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from skillpath import catalog as _catalog
from skillpath.cooccurrence import COOCCURRENCE_CSV, load_cooccurrence
from skillpath.frequency import normalize_skill

# Mastery level -> weight of the known Skill inside the Learner anchor.
MASTERY_WEIGHTS = {"basic": 0.5, "intermediate": 0.75, "advanced": 1.0}
INTEREST_WEIGHT = 1.0
TOP_K_NEIGHBOURS = 8
NEIGHBOUR_REPEATS = 4
OWN_NAME_REPEATS = 3
CATEGORY_REPEATS = 2
# Extra copies of the name token of another Catalog Skill mentioned in a description.
MENTION_EXTRA_REPEATS = 2
# Relations at or below this cosine are not shown in explanations.
EXPLANATION_THRESHOLD = 0.05
MAX_RELATIONS = 3

STOPWORDS = frozenset(
    "de la el en y a los las del un una unos unas con para por que se es al lo como su sus "
    "más mas o e entre sin sobre también muy ya son está ser usa usado usada usados usadas "
    "hasta desde cada este esta estos estas otro otra otros otras así pero si no le les "
    "tiene tienen puede pueden permite hacer sirve cuando donde mediante través".split()
)
_PUNCT = re.compile(r"[,;:()¿?¡!\"'«»]")


@dataclass(frozen=True)
class Relation:
    """One anchor element (known Skill or interest) close to a candidate."""

    label: str
    kind: str  # "skill" or "interest"
    cosine: float


@dataclass(frozen=True)
class SimilarityResult:
    scores: dict[str, float]  # candidate -> cosine with the anchor, in [0, 1]
    relations: dict[str, list[Relation]]  # candidate -> closest anchor elements
    unrecognized_interests: list[str]
    has_anchor: bool


def skill_token(name: str) -> str:
    return name.replace(" ", "_")


class SimilarityModel:
    """TF-IDF representation of the Catalog for one Role."""

    def __init__(self, catalog, aliases, neighbours):
        self.aliases = aliases
        self.names = sorted(catalog)
        self.categories = {n: catalog[n].category for n in self.names}
        multiword = sorted((n for n in self.names if " " in n), key=len, reverse=True)
        self._phrase_patterns = [
            (re.compile(r"(?<![\w+#.])" + re.escape(n) + r"(?![\w+#])"), skill_token(n))
            for n in multiword
        ]
        self._skill_tokens = {skill_token(n) for n in self.names}
        docs = [self._document(catalog[n], neighbours.get(n, {})) for n in self.names]
        self.vectorizer = TfidfVectorizer(
            analyzer=self.tokenize, min_df=2, sublinear_tf=False, norm="l2", dtype=np.float64
        )
        self.matrix = self.vectorizer.fit_transform(docs).toarray()
        self.index = {n: i for i, n in enumerate(self.names)}
        self._by_normalized = {normalize_skill(n, aliases): n for n in self.names}
        self._by_category: dict[str, list[str]] = {}
        for n in self.names:
            self._by_category.setdefault(self.categories[n].lower(), []).append(n)

    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        for pattern, token in self._phrase_patterns:
            text = pattern.sub(token, text)
        tokens = []
        for raw in _PUNCT.sub(" ", text).split():
            tok = raw.rstrip(".")
            if tok not in STOPWORDS and (len(tok) > 1 or tok == "r"):  # "r" is a Skill
                tokens.append(tok)
        return tokens

    def _document(self, skill, neighbours: dict[str, float]) -> str:
        parts = [skill_token(skill.name)] * OWN_NAME_REPEATS
        parts += ["cat_" + skill.category.lower().replace(" ", "_")] * CATEGORY_REPEATS
        parts.append(skill.description)
        for token in self.tokenize(skill.description):
            if token in self._skill_tokens and token != skill_token(skill.name):
                parts += [token] * MENTION_EXTRA_REPEATS
        top = sorted(neighbours.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_K_NEIGHBOURS]
        if top:
            best = top[0][1]
            for other, closeness in top:
                parts += [skill_token(other)] * max(1, round(NEIGHBOUR_REPEATS * closeness / best))
        return " ".join(parts)

    def vector(self, skill: str) -> np.ndarray:
        return self.matrix[self.index[skill]]

    def resolve_interest(self, interest: str) -> np.ndarray | None:
        """Vector for a free-text interest, or None if it is not recognized.

        1. A Catalog Skill (after normalization and aliases): that Skill's vector.
        2. A Catalog category: the normalized mean of the category's Skills.
        3. Otherwise: keywords transformed with the fitted vectorizer; an all-zero
           vector means the interest is unrecognized.
        """
        name = self._by_normalized.get(normalize_skill(interest, self.aliases))
        if name is not None:
            return self.vector(name)
        members = self._by_category.get(interest.strip().lower())
        if members:
            return _unit(np.mean([self.vector(m) for m in members], axis=0))
        vec = self.vectorizer.transform([interest]).toarray()[0]
        return vec if np.any(vec) else None


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


@lru_cache(maxsize=None)
def get_model(role: str) -> SimilarityModel:
    """Fitted model for a Role (cached). Roles without co-occurrence data get none.

    The Catalog is read from ``skillpath.catalog`` at call time, so a test can
    swap it (clear this cache with ``get_model.cache_clear()`` before and after).
    """
    table = load_cooccurrence(COOCCURRENCE_CSV) if COOCCURRENCE_CSV.exists() else {}
    return SimilarityModel(_catalog.CATALOG, _catalog.ALIASES, table.get(role, {}))


def compute_similarity(
    role: str,
    known_skills: dict[str, str],
    interests: list[str],
    candidates: list[str],
) -> SimilarityResult:
    """Cosine of each candidate with the Learner anchor.

    The anchor is the sum of the known Skills' vectors (weighted by Mastery
    level) and the interests' vectors (weight 1). For a candidate that is itself
    a known Skill (basic level), its own vector is left out of the anchor, so
    knowing a Skill a little does not make it look maximally similar to itself.
    An interest that names the candidate does count (explicit wish).
    Known Skills outside the Catalog are ignored. With no anchor all scores are 0.
    """
    model = get_model(role)
    elements: list[tuple[str, str, np.ndarray, float, str | None]] = []
    for skill in sorted(known_skills):
        if skill in model.index and known_skills[skill] in MASTERY_WEIGHTS:
            elements.append((skill, "skill", model.vector(skill), MASTERY_WEIGHTS[known_skills[skill]], skill))
    unrecognized: list[str] = []
    for interest in interests:
        if not interest or not interest.strip():
            continue
        vec = model.resolve_interest(interest)
        if vec is None:
            unrecognized.append(interest)
        else:
            elements.append((interest.strip(), "interest", vec, INTEREST_WEIGHT, None))

    zero = {c: 0.0 for c in candidates}
    if not elements:
        return SimilarityResult(zero, {c: [] for c in candidates}, unrecognized, False)

    total = sum(w * v for _, _, v, w, _ in elements)
    scores: dict[str, float] = {}
    relations: dict[str, list[Relation]] = {}
    for cand in candidates:
        if cand not in model.index:
            scores[cand], relations[cand] = 0.0, []
            continue
        cv = model.vector(cand)
        anchor = total.copy()
        rels = []
        for label, kind, vec, weight, own in elements:
            if own == cand:
                anchor = anchor - weight * vec
                continue
            cos = float(np.clip(_unit(vec) @ cv, 0.0, 1.0))
            if cos > EXPLANATION_THRESHOLD:
                rels.append(Relation(label, kind, cos))
        norm = np.linalg.norm(anchor)
        scores[cand] = float(np.clip(cv @ anchor / norm, 0.0, 1.0)) if norm > 1e-12 else 0.0
        rels.sort(key=lambda r: (-r.cosine, r.label))
        relations[cand] = rels[:MAX_RELATIONS]
    return SimilarityResult(scores, relations, unrecognized, True)
