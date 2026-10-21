"""Deterministic recommendation logic (no LLM, no randomness)."""

from skillpath import catalog, similarity
from skillpath.frequency import normalize_skill
from skillpath.models import (
    EXPERIENCE_LEVELS,
    MASTERED_LEVELS,
    LearnerProfile,
    LearningPath,
    LearningPathItem,
)


# Entry-level Frequency is blended with the base one as if the base had
# ENTRY_PRIOR_OFFERS fictitious Offers: w = n / (n + K). See docs/entry-level-complement.md.
ENTRY_PRIOR_OFFERS = 100
# Below this many entry-level Offers the sample is too small: no blend (w = 0).
MIN_ENTRY_OFFERS = 30


def entry_weight(sample_size: int) -> float:
    """Weight of the entry-level Frequency in the blend for a sample of n Offers."""
    if sample_size < MIN_ENTRY_OFFERS:
        return 0.0
    return sample_size / (sample_size + ENTRY_PRIOR_OFFERS)


def _missing_prerequisites(skill_name: str, mastered: set[str]) -> list[str]:
    """Direct Prerequisites of a Skill that the Learner has not mastered."""
    return [p for p in catalog.CATALOG[skill_name].prerequisites if p not in mastered]


def _missing_closure(skill_name: str, mastered: set[str]) -> set[str]:
    """All missing Prerequisites of a Skill, direct and transitive, no duplicates.

    The walk stops at mastered Skills: mastering X assumes its foundations.
    """
    seen: set[str] = set()
    stack = _missing_prerequisites(skill_name, mastered)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(_missing_prerequisites(name, mastered))
    return seen


def recommend(learner_profile: LearnerProfile) -> LearningPath:
    """Return the Learning path for a Learner profile.

    Skills the Learner has mastered (intermediate or advanced) are excluded;
    basic Mastery level does not count as mastered, so the Skill stays a
    candidate and counts as a missing Prerequisite for the Skills that need it.

    Effort = Difficulty + number of distinct missing Prerequisites, transitive
    (the walk stops at mastered Skills). Priority = Frequency * (1 + similarity)
    / Effort, where similarity in [0, 1] is the TF-IDF cosine between the
    candidate and the Learner's known Skills and interests (0 with none).
    Order: priority descending, ties by higher Frequency, then name ascending;
    then a stable topological adjustment so every Skill comes after all its
    missing Prerequisites. See docs/priority-formula.md.

    ``cold_start`` is True when the profile has no known Skill in the Catalog
    (with a valid Mastery level) and no recognized interest; the Learning path
    then comes from Frequency and Effort alone, and ``most_frequent()`` gives the
    Role's most frequent Skills. See docs/cold-start.md.

    ``experience_level="entry"`` (student or recent graduate) mixes the base
    Frequency with the entry-level one (arshkon): Frequency = w * entry +
    (1 - w) * base, w = n / (n + ENTRY_PRIOR_OFFERS); Skills absent from the
    entry-level table (unreliable detection) and samples smaller than
    MIN_ENTRY_OFFERS use the base only. The priority formula does not change.
    See docs/entry-level-complement.md.

    Raises ValueError if the Role or the experience level is unknown.
    """
    role = learner_profile.role
    if role not in catalog.FREQUENCY:
        raise ValueError(
            f"Role desconocido: {role!r}. Roles disponibles: {sorted(catalog.FREQUENCY)}"
        )
    level = learner_profile.experience_level
    if level not in EXPERIENCE_LEVELS:
        raise ValueError(
            f"Nivel de experiencia desconocido: {level!r}. Valores válidos: {list(EXPERIENCE_LEVELS)}"
        )
    skills = catalog.CATALOG
    role_table = catalog.FREQUENCY[role]
    # Catalog Skills missing from the Role's table get Frequency 0.0.
    known = {
        name: normalize_skill(name, catalog.ALIASES) in role_table for name in skills
    }
    frequencies = {
        name: role_table.get(normalize_skill(name, catalog.ALIASES), 0.0)
        for name in skills
    }
    # Frequency source per Skill: None (default level) | "mix" | "excluded" | "small" | "nodata".
    sources: dict[str, str | None] = {name: None for name in skills}
    weight, sample = 0.0, None
    if level == "entry":
        entry_table = catalog.ENTRY_FREQUENCY.get(role)
        sample = catalog.ENTRY_SAMPLE_SIZE.get(role)
        if entry_table is None or sample is None:
            sources = {name: "nodata" for name in skills}
            sample = None
        else:
            weight = entry_weight(sample)
            for name in skills:
                norm = normalize_skill(name, catalog.ALIASES)
                if norm not in entry_table:
                    sources[name] = "excluded"
                elif weight == 0.0:
                    sources[name] = "small"
                else:
                    sources[name] = "mix"
                    frequencies[name] = (
                        weight * entry_table[norm] + (1 - weight) * frequencies[name]
                    )
    mastered = {
        name
        for name, lvl in learner_profile.known_skills.items()
        if lvl in MASTERED_LEVELS
    }
    candidates = [name for name in skills if name not in mastered]

    closures = {name: _missing_closure(name, mastered) for name in candidates}
    efforts = {name: skills[name].difficulty + len(closures[name]) for name in candidates}
    sim = similarity.compute_similarity(
        role, learner_profile.known_skills, learner_profile.interests, candidates
    )
    priorities = {
        name: frequencies[name] * (1 + sim.scores[name]) / efforts[name] for name in candidates
    }
    pending = sorted(
        candidates, key=lambda n: (-priorities[n], -frequencies[n], n)
    )

    # Stable topological adjustment: take the best-ranked Skill whose direct
    # missing Prerequisites are already placed (so, by induction, all the
    # transitive ones too).
    ordered: list[str] = []
    while pending:
        placed = set(ordered)
        for name in pending:
            if all(p in placed for p in _missing_prerequisites(name, mastered)):
                ordered.append(name)
                pending.remove(name)
                break
        else:  # cycle in Prerequisites: avoid an infinite loop
            ordered.extend(pending)
            break

    items = [
        LearningPathItem(
            skill=name,
            frequency=frequencies[name],
            effort=efforts[name],
            explanation=_explain(
                name, role, frequencies[name], known[name], efforts[name], mastered,
                closures[name], sim.relations[name], sim.has_anchor,
                sources[name], weight, sample,
            ),
            similarity=sim.scores[name],
        )
        for name in ordered
    ]
    return LearningPath(
        role=role,
        items=items,
        unrecognized_interests=sim.unrecognized_interests,
        cold_start=not sim.has_anchor,
        experience_level=level,
        entry_sample_size=sample,
        entry_weight=weight,
    )


def _explain(
    name: str,
    role: str,
    frequency: float,
    has_data: bool,
    effort: int,
    mastered: set[str],
    closure: set[str],
    relations: list[similarity.Relation],
    has_anchor: bool,
    source: str | None = None,
    weight: float = 0.0,
    sample: int | None = None,
) -> str:
    note = _explain_source(source, weight, sample)
    if has_data or source == "mix":
        text = f"Aparece en el {frequency:.1f}% de las Offers de {role}{note}; Effort {effort}."
    else:
        text = (
            f"No aparece en las Offers de {role} analizadas (Frequency 0 %), así que va "
            f"al final del Learning path; Effort {effort}."
        )
    text += " " + _explain_similarity(relations, has_anchor)
    missing = _missing_prerequisites(name, mastered)
    prerequisites = catalog.CATALOG[name].prerequisites
    if missing:
        text += f" Conviene aprender antes: {', '.join(missing)}."
        if len(closure) > len(missing):
            text += f" El Effort incluye {len(closure)} Prerequisites pendientes en total."
    elif prerequisites:
        text += f" Ya dominas sus Prerequisites: {', '.join(prerequisites)}."
    return text


def _explain_source(source: str | None, weight: float, sample: int | None) -> str:
    """Parenthetical about where the Frequency comes from (entry-level Learners only)."""
    if source == "mix":
        return (
            f" (mezcla: {weight:.0%} de {sample} Offers de nivel inicial de arshkon, una muestra "
            f"pequeña, y {1 - weight:.0%} de las Offers base)"
        )
    if source == "excluded":
        return " (solo Offers base: la detección en el texto no fue fiable para esta Skill)"
    if source == "small":
        return (
            f" (solo Offers base: hay apenas {sample} Offers de nivel inicial, menos del mínimo "
            f"de {MIN_ENTRY_OFFERS})"
        )
    if source == "nodata":
        return " (solo Offers base: no hay datos de nivel inicial para este Role)"
    return ""


def _explain_similarity(relations: list[similarity.Relation], has_anchor: bool) -> str:
    if not has_anchor:
        return "Sin Skills ni intereses reconocidos, el orden usa solo Frequency y Effort."
    if not relations:
        return "Sin relación clara con lo que sabes ni con tus intereses."
    parts = []
    for kind, intro in (("skill", "lo que ya sabes"), ("interest", "tus intereses")):
        group = [f"{r.label} ({r.cosine:.2f})" for r in relations if r.kind == kind]
        if group:
            parts.append(f"Se relaciona con {intro}: {', '.join(group)}.")
    return " ".join(parts)
