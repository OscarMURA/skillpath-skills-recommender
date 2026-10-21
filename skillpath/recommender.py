"""Deterministic recommendation logic (no LLM, no randomness)."""

from skillpath import catalog
from skillpath.catalog import CATALOG
from skillpath.frequency import normalize_skill
from skillpath.models import (
    MASTERED_LEVELS,
    LearnerProfile,
    LearningPath,
    LearningPathItem,
)


def _missing_prerequisites(skill_name: str, mastered: set[str]) -> list[str]:
    return [p for p in CATALOG[skill_name].prerequisites if p not in mastered]


def recommend(learner_profile: LearnerProfile) -> LearningPath:
    """Return the Learning path for a Learner profile.

    Skills the Learner has mastered (intermediate or advanced) are excluded;
    basic Mastery level keeps a Skill as a candidate.

    Placeholder scoring: score = Frequency / Effort, where
    Effort = Difficulty + number of missing Prerequisites.
    Ordered by score descending, ties by name, then adjusted so every Skill
    comes after its missing Prerequisites.

    Raises ValueError if the Role is unknown.
    """
    role = learner_profile.role
    if role not in catalog.FREQUENCY:
        raise ValueError(
            f"Role desconocido: {role!r}. Roles disponibles: {sorted(catalog.FREQUENCY)}"
        )
    role_table = catalog.FREQUENCY[role]
    # Catalog Skills missing from the Role's table get Frequency 0.0.
    known = {
        name: normalize_skill(name, catalog.ALIASES) in role_table for name in CATALOG
    }
    frequencies = {
        name: role_table.get(normalize_skill(name, catalog.ALIASES), 0.0)
        for name in CATALOG
    }
    mastered = {
        name
        for name, level in learner_profile.known_skills.items()
        if level in MASTERED_LEVELS
    }
    candidates = [name for name in CATALOG if name not in mastered]

    efforts = {
        name: CATALOG[name].difficulty + len(_missing_prerequisites(name, mastered))
        for name in candidates
    }
    scores = {name: frequencies[name] / efforts[name] for name in candidates}
    pending = sorted(candidates, key=lambda n: (-scores[n], n))

    # Stable topological adjustment: take the best-scored Skill whose missing
    # Prerequisites are already placed.
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
            explanation=_explain(name, role, frequencies[name], known[name], efforts[name], mastered),
        )
        for name in ordered
    ]
    return LearningPath(role=role, items=items)


def _explain(
    name: str, role: str, frequency: float, has_data: bool, effort: int, mastered: set[str]
) -> str:
    if has_data:
        text = f"Aparece en el {frequency:.1f}% de las ofertas de {role}; esfuerzo estimado {effort}."
    else:
        text = f"No aparece en las ofertas de {role} analizadas. Esfuerzo estimado {effort}."
    missing = _missing_prerequisites(name, mastered)
    if missing:
        text += f" Conviene aprender antes: {', '.join(missing)}."
    elif CATALOG[name].prerequisites:
        text += f" Ya dominas sus prerrequisitos: {', '.join(CATALOG[name].prerequisites)}."
    return text
