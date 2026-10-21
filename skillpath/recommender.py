"""Deterministic recommendation logic (no LLM, no randomness)."""

from skillpath import catalog
from skillpath.frequency import normalize_skill
from skillpath.models import (
    MASTERED_LEVELS,
    LearnerProfile,
    LearningPath,
    LearningPathItem,
)


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
    (the walk stops at mastered Skills). Priority = Frequency / Effort.
    Order: priority descending, ties by higher Frequency, then name ascending;
    then a stable topological adjustment so every Skill comes after all its
    missing Prerequisites. See docs/priority-formula.md.

    Raises ValueError if the Role is unknown.
    """
    role = learner_profile.role
    if role not in catalog.FREQUENCY:
        raise ValueError(
            f"Role desconocido: {role!r}. Roles disponibles: {sorted(catalog.FREQUENCY)}"
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
    mastered = {
        name
        for name, level in learner_profile.known_skills.items()
        if level in MASTERED_LEVELS
    }
    candidates = [name for name in skills if name not in mastered]

    closures = {name: _missing_closure(name, mastered) for name in candidates}
    efforts = {name: skills[name].difficulty + len(closures[name]) for name in candidates}
    priorities = {name: frequencies[name] / efforts[name] for name in candidates}
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
                name, role, frequencies[name], known[name], efforts[name], mastered, closures[name]
            ),
        )
        for name in ordered
    ]
    return LearningPath(role=role, items=items)


def _explain(
    name: str,
    role: str,
    frequency: float,
    has_data: bool,
    effort: int,
    mastered: set[str],
    closure: set[str],
) -> str:
    if has_data:
        text = f"Aparece en el {frequency:.1f}% de las ofertas de {role}; esfuerzo estimado {effort}."
    else:
        text = f"No aparece en las ofertas de {role} analizadas. Esfuerzo estimado {effort}."
    missing = _missing_prerequisites(name, mastered)
    prerequisites = catalog.CATALOG[name].prerequisites
    if missing:
        text += f" Conviene aprender antes: {', '.join(missing)}."
        if len(closure) > len(missing):
            text += f" El esfuerzo incluye {len(closure)} prerrequisitos pendientes en total."
    elif prerequisites:
        text += f" Ya dominas sus prerrequisitos: {', '.join(prerequisites)}."
    return text
