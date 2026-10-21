# 05: Similitud con co-ocurrencia y explicaciones

**What to build:** El sistema usa TF-IDF y similitud del coseno sobre la descripción de cada Skill, su categoría y las Skills con que co-ocurre en las Offers, para favorecer Skills cercanas a las que el Learner ya sabe o le interesan. Cada recomendación incluye una explicación simple de por qué se sugiere.

**Blocked by:** 04

**Status:** done

- [x] La similitud ajusta la prioridad y su criterio está descrito con claridad en un documento corto
- [x] Una prueba muestra que un Learner con una Skill dada recibe Skills relacionadas por delante de otras no relacionadas
- [x] Cada elemento del Learning path trae una explicación (Frequency en el Role, Skills relacionadas que ya domina, Prerequisites cubiertos)
- [x] Los intereses indicados por el Learner influyen en el resultado

## Handoff

**Fecha:** 2026-10-20. **Líder:** Opus. **Trabajador:** Sonnet.

### Qué se hizo

- `skillpath/cooccurrence.py`: `compute_cooccurrence` (función pura) y `load_cooccurrence`. `skillpath/build_cooccurrence.py`: comando `.venv/bin/python -m skillpath.build_cooccurrence` (`--datos`, `--out`, `--min-offers 5`). Genera `catalog/cooccurrence.csv` (3.906 filas, 163 KB; columnas `role, skill_a, skill_b, offers_together, closeness`). Regenerado dos veces: archivo idéntico byte a byte.
- `skillpath/similarity.py`: TF-IDF + coseno, un modelo por Role (se ajusta solo con los 64 documentos del Catalog, con caché). Ancla del Learner, intereses, no reconocidos y relaciones más cercanas por candidata.
- `skillpath/recommender.py`: `Prioridad = Frequency × (1 + similitud) / Effort`; explicaciones con relación y aviso sin ancla. `skillpath/models.py`: `LearningPathItem.similarity` (default 0.0) y `LearningPath.unrecognized_interests`.
- `app/streamlit_app.py`: multiselect de intereses (Skills y categorías), texto libre separado por comas, columna "Similitud" y aviso de intereses no reconocidos.
- `docs/similarity.md` (criterio, ejemplos con números reales, alternativas y limitaciones), `docs/priority-formula.md` (sección nueva "Extensión con similitud (ticket 05)" DESPUÉS de la firma; lo firmado no se tocó), `catalog/README.md` (co-ocurrencia y comando).
- Pruebas: `tests/test_similarity.py` (nuevo; comportamiento solo vía `recommend` más funciones puras de co-ocurrencia con fixtures y consistencia del CSV) y 4 pruebas nuevas en `tests/test_app.py` (tres Roles con intereses y aviso de interés no reconocido). Las 87 anteriores pasan sin cambios. `.venv/bin/pytest -q`: 118 passed.

### Decisiones (revisar)

- **Por Role y no global:** la cercanía depende del mercado del Role; el archivo sigue pequeño (163 KB). Pares con menos de 5 Offers juntas se descartan.
- **Cercanía = Ochiai** (`together / sqrt(a × b)`), no Jaccard: con Jaccard `pandas` casi no se acercaba a `python`.
- **Documento por Skill:** nombre propio x3, categoría x2, descripción, menciones de otras Skills en la descripción (2 copias extra), 8 vecinos por co-ocurrencia con 1 a 4 repeticiones. Nombres de varias palabras en una sola palabra. `min_df=2`, tf sin suavizar, stopwords en español (lista corta explícita).
- **Ancla:** Mastery level básico 0.5, intermedio 0.75, avanzado 1.0; intereses 1.0. Skill conocida en básico: se quita su propio vector del ancla al calcular su similitud; un interés que la nombra sí cuenta.
- **Intereses:** Skill del Catalog (con alias) -> su vector; categoría -> promedio; otro texto -> palabras clave con el vectorizador; vector cero -> no reconocido (se informa y se ignora).
- **Umbral de explicación:** coseno > 0.05, máximo 3 relaciones. Sin ancla: "Sin habilidades ni intereses reconocidos, el orden usa solo frecuencia y esfuerzo." (se escribió "reconocidos" y no "declarados" porque un interés no reconocido no cuenta).
- Pesos y repeticiones son decisiones razonables, no ajustadas con datos. Las Skills muy frecuentes elevan la similitud de fondo (0.3 a 0.7); el efecto en el orden es moderado.

### Pendiente de acuse humano

- La extensión de la fórmula, escrita en `docs/priority-formula.md` (sección nueva tras la Firma, marcada como pendiente). La viñeta de Limitaciones "Todavía no hay similitud..." queda superada pero no se editó.

### Qué sigue

Los tickets 06 (arranque en frío) y 07 (complemento junior con arshkon) pueden empezar. El 08 (evaluación y métricas de sesgo) depende del 05 y del 07.

Nada está en commit: revisar y hacer commit a mano.

### Acuse humano

Oscar reconoció la extensión de la fórmula con similitud el 2026-10-20, sin cambios.
