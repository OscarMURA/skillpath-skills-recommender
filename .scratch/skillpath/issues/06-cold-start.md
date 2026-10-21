# 06: Arranque en frío

**What to build:** Un Learner nuevo recibe recomendaciones desde la primera sesión: un formulario inicial corto crea su Learner profile, y si lo deja vacío ve las Skills más frecuentes de su Role.

**Blocked by:** 03

**Status:** `done`

- [x] El formulario inicial pide Role, Skills conocidas y niveles
- [x] Con perfil vacío, el resultado son las Skills de mayor Frequency del Role (prueba)
- [x] Una Skill añadida al Catalog se recomienda sin necesitar historial
- [x] El comportamiento queda descrito para el punto 2.1 del taller

## Handoff

**Fecha:** 2026-10-20. **Líder:** Opus. **Trabajador:** Sonnet.

### Qué se hizo

- `skillpath/models.py`: `LearningPath.cold_start` (default False) y `LearningPath.most_frequent(n=10)` (Frequency pura descendente, desempate por nombre, sin Skills de Frequency 0). Todo sale del seam único `recommend`.
- `skillpath/recommender.py`: `cold_start = not sim.has_anchor` (ninguna Skill conocida del Catalog con Mastery level válido ni interés reconocido). Explicación de Skill sin Frequency: "No aparece en las ofertas de {role} analizadas. Frequency 0 %, así que va al final de la ruta; esfuerzo estimado N." La fórmula firmada no cambió.
- `skillpath/similarity.py`: `get_model` lee `catalog.CATALOG` y `catalog.ALIASES` al llamarse, para poder probar con un Catalog temporal (limpiar `get_model.cache_clear()`).
- `app/streamlit_app.py`: explicación breve arriba, casilla «Empezar sin datos» (key `start_empty`), 8 sugerencias del Role como casillas (nivel intermedio por defecto), `st.info` de arranque en frío y segunda tabla "Las más frecuentes en las ofertas de {role}" siempre visible. Índices de widgets de las pruebas anteriores intactos.
- Pruebas: `tests/test_cold_start.py` (nuevo) y casos nuevos en `tests/test_app.py` (tres Roles con «Empezar sin datos» y con perfil mínimo). No se modificó ninguna prueba existente. `.venv/bin/pytest -q`: 149 passed.
- `docs/cold-start.md` (punto 2.1): concepto, Learner vs. Skill, estrategias, ejemplos reales y limitaciones. El líder volvió a ejecutar las cifras y coinciden.

### Decisiones (revisar)

- **Frequency pura vs. fórmula:** con perfil vacío se muestran las dos vistas del mismo resultado. El Learning path sigue la fórmula firmada (respeta Prerequisites y Effort). `most_frequent` cumple de forma directa y verificable "las Skills de mayor Frequency del Role". Difieren: p. ej., en Data Scientist `machine learning` es 3.ª por Frequency y 9.ª en el Learning path (Effort 6).
- **Skill nueva sin Frequency** (prueba con `sqlmesh` ficticia, Prerequisite `sql`): Frequency 0, Effort por Difficulty y Prerequisites, similitud por descripción y categoría, interés por nombre o categoría reconocido. Queda al final del Learning path porque la prioridad multiplica a Frequency 0. Es coherente con lo firmado, no se cambió. Su Frequency se obtiene volviendo a ejecutar `build_frequency`, sin Learners.
- La explicación mezcla "Frequency" con texto en español y usa "ruta" (la UI ya decía "Tu ruta de aprendizaje"). Puede pulirse en el ticket 09.

### Qué sigue

El ticket 07 puede empezar. El 09 (app completa) depende del 05 y del 06, ya hechos.

Nada está en commit: revisar y hacer commit a mano.
