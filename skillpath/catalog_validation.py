"""Validation of the Catalog as data (reusable by tests and scripts)."""

from skillpath.models import Skill

CATEGORIES = (
    "programación",
    "bases de datos",
    "análisis de datos",
    "visualización",
    "nube",
    "DevOps",
    "machine learning",
    "ingeniería de datos",
    "desarrollo web",
    "ingeniería de software",
    "herramientas",
)


def find_cycle(prerequisites: dict[str, tuple[str, ...]]) -> list[str] | None:
    """Return a cycle as a list of names (first == last), or None if acyclic.

    Prerequisites naming Skills absent from the dict are ignored.
    """
    done: set[str] = set()
    on_stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in on_stack:
            return on_stack[on_stack.index(node):] + [node]
        if node in done:
            return None
        on_stack.append(node)
        for nxt in prerequisites.get(node, ()):
            if nxt in prerequisites:
                cycle = visit(nxt)
                if cycle:
                    return cycle
        on_stack.pop()
        done.add(node)
        return None

    for start in prerequisites:
        cycle = visit(start)
        if cycle:
            return cycle
    return None


def validate_catalog(
    catalog: dict[str, Skill], frequency: dict[str, dict[str, float]]
) -> list[str]:
    """Return error messages (empty list if the Catalog is valid)."""
    errors: list[str] = []
    in_frequency = {s for table in frequency.values() for s in table}
    for name, skill in catalog.items():
        if skill.category not in CATEGORIES:
            errors.append(f"{name}: categoría fuera de la lista cerrada ({skill.category!r})")
        if not skill.description.strip():
            errors.append(f"{name}: descripción vacía")
        if not 1 <= skill.difficulty <= 5:
            errors.append(f"{name}: Difficulty fuera de rango ({skill.difficulty})")
        for p in skill.prerequisites:
            if p == name:
                errors.append(f"{name}: es su propio Prerequisite")
            elif p not in catalog:
                errors.append(f"{name}: Prerequisite inexistente ({p})")
        if name not in in_frequency:
            errors.append(f"{name}: no aparece en la tabla de Frequency")
    cycle = find_cycle({n: s.prerequisites for n, s in catalog.items()})
    if cycle:
        errors.append("ciclo de Prerequisites: " + " -> ".join(cycle))
    return errors
