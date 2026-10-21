# 07: Complemento junior con arshkon

**What to build:** La demanda considera también ofertas de nivel inicial. Se usan las Offers Entry/Associate de arshkon, detectando las Skills del Catalog por búsqueda de términos en su descripción, y el Learner indica su nivel de experiencia para que la Frequency refleje lo que piden a quien empieza.

**Blocked by:** 03

**Status:** done

- [x] Se calcula la Frequency para ofertas de nivel inicial por Role mediante búsqueda por diccionario
- [x] El tamaño de la muestra por Role queda registrado y se advierte que es pequeña
- [x] El Learner puede indicar su nivel de experiencia y el resultado cambia en consecuencia (prueba)
- [x] Solo se usan las ofertas de arshkon cuyo título corresponde a uno de los tres Roles (Data Analyst, Software Engineer, Data Scientist)

## Handoff

**Fecha:** 2026-10-21. **Líder:** Opus. **Trabajadores:** Sonnet (A: detector, comando y calibración; B: recomendador, app, documento y pruebas).

### Qué se hizo

- `skillpath/skill_detection.py`: detector por diccionario (`build_patterns`, `detect_skills`). Busca nombres y alias del Catalog, con límites de palabra que admiten símbolos (`c++`, `c#`, `ci/cd`) y reglas para los ambiguos (`r`, `go`, `excel` como verbo, `spark`, `rest`, `java` frente a `javascript`, `sql` frente a `mysql`).
- `skillpath/entry_frequency.py` y `skillpath/build_entry_frequency.py`: comando `.venv/bin/python -m skillpath.build_entry_frequency`. Lee arshkon por trozos, asigna el Role por título, filtra el nivel inicial, deduplica por texto de `description`, detecta Skills y calibra contra asaniczka. Tarda unos 2 min 20 s (unos 7 s con `--skip-calibration`).
- Archivos generados:
  - `catalog/frequency_entry_by_role.csv`: 180 filas, 6 KB, mismas columnas que la base; `role_offers` es el tamaño de muestra.
  - `catalog/detection_calibration.csv`: 192 filas.
  - Regenerados por el líder: salen idénticos byte a byte (sha1 `e52ecb49…` y `e39bf55f…`).
- `skillpath/models.py`: `LearnerProfile.experience_level` (`"experienced"` por defecto, o `"entry"`) y, en `LearningPath`, `experience_level`, `entry_sample_size` y `entry_weight`.
- `skillpath/catalog.py`: `ENTRY_FREQUENCY` y `ENTRY_SAMPLE_SIZE`.
- `skillpath/recommender.py`: mezcla la Frequency para Learners de nivel inicial y explica la mezcla con el tamaño de muestra y el aviso de "muestra pequeña". La fórmula firmada no cambia.
- `app/streamlit_app.py`: radio «Nivel de experiencia» y `st.warning` con el tamaño de muestra del Role.
- Documentos:
  - `docs/entry-level-complement.md` (nuevo).
  - `catalog/README.md`: secciones de nivel inicial y de calibración.
  - `docs/priority-formula.md`: sección nueva al final, pendiente de acuse humano. Lo firmado no se tocó.
  - `docs/cold-start.md`: un enlace.
- Pruebas nuevas:
  - `tests/test_skill_detection.py`: falsos positivos y verdaderos positivos con fixtures, título del Role, deduplicación y consistencia de los CSV.
  - `tests/test_entry_level.py`: vía `recommend`.
  - `tests/test_app_entry_level.py`: AppTest en los tres Roles.
- Ninguna prueba existente se modificó. `.venv/bin/pytest -q`: 246 passed.

### Decisiones (revisar)

- **Nivel inicial = Entry level + Internship.** Associate no entra porque la base de asaniczka ya está hecha de Offers Associate y Mid senior. Se cambia con `--levels`.
- **Muestra tras deduplicar.** El líder detectó Offers repetidas; por ejemplo, "Online Data Analyst" aparece 20 veces con el mismo texto.

  | Role | Antes de deduplicar | Después |
  |---|---|---|
  | Data Analyst | 118 | 80 |
  | Software Engineer | 225 | 216 |
  | Data Scientist | 57 | 47 |

  Associate, que no se usa, tiene 37, 76 y 11.
- **Role por título.** `data analyst`, `data scientist` y `software (engineer|developer|development engineer)`. Un título que coincide con más de un Role se descarta.
- **Calibración.** Sobre las mismas Offers de asaniczka (12.705, 9.367 y 4.336), se compara la Frequency detectada en `job_summary` con la de `job_skills`. Una Skill es no fiable si en algún Role `|diff| > 10` o si su cociente queda fuera de [0,5, 2,0] donde `job_skills` da al menos 2 %.
  - Se excluyeron `algorithms`, `big data`, `microservices` y `statistics`; usan solo la base.
  - Los desvíos van casi siempre del texto por encima de `job_skills`, y los ejemplos revisados eran menciones reales: hay ruido en `job_skills`.
  - Entre las Skills fiables, el mayor desvío es 6,2 (Data Analyst), 7,3 (Software Engineer) y 9,1 (Data Scientist) puntos.
- **Mezcla.** `w = n/(n+100)`, sin mezcla si `n < 30`. Pesos: Data Analyst 0,44, Software Engineer 0,68 y Data Scientist 0,32. K = 100 y el mínimo de 30 son decisiones de diseño, no ajustadas con datos.
- **`git`** cuenta también GitHub, GitLab y Bitbucket.
- **Limitación conocida.** Plantillas casi idénticas sobreviven a la deduplicación exacta. `machine learning` queda en 22,5 % en Data Analyst de nivel inicial (18 de 80), probablemente inflada.
- asaniczka también repite `job_summary` exactos. No se tocó la base; solo queda anotado en `catalog/README.md`.

### Pendiente de acuse humano

La sección "Fuente de la Frequency para Learners de nivel inicial (ticket 07)" de `docs/priority-formula.md`.

### Qué sigue

- El 08 (evaluación y métricas de sesgo) depende del 05 y del 07, ambos hechos, así que puede empezar. `docs/entry-level-complement.md` sirve para la Parte 3.
- El 09 (app completa) depende del 05 y del 06, ya hechos.

Nada está en commit: revisar y hacer commit a mano.

### Acuse humano

Oscar aceptó el 2026-10-21 que el nivel inicial sea Entry level + Internship (sin Associate), y reconoció la sección nueva de docs/priority-formula.md.
