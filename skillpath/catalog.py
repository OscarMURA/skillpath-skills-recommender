"""Mini Catalog (placeholder) and real Frequency per Role.

PLACEHOLDER: the 5-Skill Catalog below is still hand-written; ticket 03
replaces it with the curated Catalog. Ticket 02 replaced the invented Frequency
with the real one, read from catalog/frequency_by_role.csv.
"""

from skillpath.frequency import (
    ALIASES_CSV,
    FREQUENCY_CSV,
    ROLES,
    load_aliases,
    load_frequency_table,
)
from skillpath.models import Skill

__all__ = ["CATALOG", "FREQUENCY", "ALIASES", "ROLES"]

CATALOG: dict[str, Skill] = {
    s.name: s
    for s in [
        Skill("SQL", "Datos", "Lenguaje para consultar bases de datos relacionales.", 2),
        Skill("Excel", "Herramientas", "Hojas de cálculo para analizar y resumir datos.", 1),
        Skill("Python", "Lenguajes", "Lenguaje de programación de propósito general.", 2),
        Skill("Pandas", "Librerías", "Librería de Python para manipular datos tabulares.", 3, ("Python",)),
        Skill("Tableau", "Visualización", "Herramienta para crear tableros de visualización.", 2),
    ]
}

# Frequency (% of the Role's Offers mentioning the Skill), read once from the
# versioned table. Empty if the table has not been generated yet (the build
# command imports this module before writing it).
FREQUENCY: dict[str, dict[str, float]] = (
    load_frequency_table(FREQUENCY_CSV) if FREQUENCY_CSV.exists() else {}
)

# Skill name aliases, used to look Catalog names up in the Frequency table.
ALIASES: dict[str, str] = load_aliases(ALIASES_CSV)
