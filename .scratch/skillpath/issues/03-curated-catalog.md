# 03: Catalog de ~60 Skills

**What to build:** Un Catalog curado de unas 60 Skills técnicas, las más frecuentes entre los tres Roles, cada una con categoría, descripción, Difficulty (1 a 5) y Prerequisites. Un agente redacta el borrador y **los humanos lo revisan y corrigen** antes de darlo por bueno. El Learning path ya solo recomienda Skills del Catalog.

**Blocked by:** 02

**Status:** done

- [x] El borrador cubre unas 60 Skills técnicas, sin habilidades blandas
- [x] Toda Skill tiene Difficulty en rango, categoría y descripción
- [x] Todo Prerequisite existe en el propio Catalog y no hay ciclos (validado por pruebas como datos)
- [x] **Compuerta humana:** Oscar o Gabriel revisan los Prerequisites y la Difficulty y lo registran en la sección Handoff
- [x] El punto de entrada recomienda solo Skills del Catalog

## Handoff

**Qué se hizo (2026-10-20, líder Opus, trabajadores Sonnet):**

- `catalog/skills.csv`: borrador del Catalog con 64 Skills (columnas `name,category,description,difficulty,prerequisites,reviewed`; Prerequisites separados por `;`; `reviewed=false` en todas). Los nombres coinciden con los normalizados de `frequency_by_role.csv`. Incluye `sql`, `excel`, `python`, `pandas`, `tableau`.
- `catalog/README.md`: sección "Catalog (`skills.csv`)" con la escala de Difficulty, criterios de selección y de Prerequisites (solo directos; necesario o claramente conveniente), proceso de revisión humana y decisiones dudosas.
- `catalog/frequency_by_role.csv`: regenerado con `python -m skillpath.build_frequency` para incluir las Skills del Catalog bajo el umbral del 1 % (solo filas añadidas; 669 filas de datos).
- `skillpath/models.py` (`Skill.reviewed`), `skillpath/frequency.py` (`SKILLS_CSV`), `skillpath/catalog.py` (`load_catalog`; sin placeholder), `skillpath/catalog_validation.py` (`find_cycle`, `validate_catalog`, `CATEGORIES`). `recommend` no cambió: ya recomienda solo Skills del Catalog con la Frequency real.
- Pruebas: `tests/test_catalog.py` (Catalog como datos, incluye grafos de fixture con ciclo y autoreferencia), `tests/test_app.py` (AppTest en los tres Roles), `tests/test_recommend.py` adaptado (nombres en minúscula; listas fijas de 5 Skills -> `sorted(CATALOG)`; `all(frequency > 0)` -> mayoría; "tableau último" -> después de toda Skill con Frequency > 0 que no dependa de ella) y dos pruebas nuevas de orden por Prerequisites. Verificado por el líder: `53 passed`.
- Conteos: por categoría programación 10, ingeniería de datos 9, análisis de datos 8, bases de datos 6, machine learning 6, ingeniería de software 6, desarrollo web 6, visualización 4, nube 3, herramientas 3, DevOps 3. Skills del Catalog con Frequency >= 1 %: Data Analyst 36, Software Engineer 43, Data Scientist 57 (todas tienen Frequency > 0 en los tres Roles).

**Para revisar (Gabriel u Oscar): Difficulty y Prerequisites**

Escala: 1 introductoria, 2 básica, 3 intermedia, 4 avanzada, 5 especializada (detalle en `catalog/README.md`).

| Skill | Categoría | Difficulty | Prerequisites |
|---|---|---|---|
| `python` | programación | 2 | — |
| `sql` | bases de datos | 2 | — |
| `excel` | análisis de datos | 2 | — |
| `pandas` | análisis de datos | 3 | `python` |
| `tableau` | visualización | 2 | — |
| `power bi` | visualización | 2 | `excel` |
| `looker` | visualización | 3 | `sql` |
| `data visualization` | visualización | 2 | — |
| `r` | programación | 3 | — |
| `sas` | análisis de datos | 3 | — |
| `vba` | programación | 3 | `excel` |
| `statistics` | análisis de datos | 3 | — |
| `a/b testing` | análisis de datos | 3 | `statistics` |
| `data cleaning` | análisis de datos | 2 | — |
| `data mining` | análisis de datos | 3 | `statistics`, `sql` |
| `machine learning` | machine learning | 4 | `python`, `statistics` |
| `scikit-learn` | machine learning | 3 | `machine learning`, `pandas` |
| `numpy` | análisis de datos | 3 | `python` |
| `deep learning` | machine learning | 5 | `machine learning` |
| `natural language processing` | machine learning | 5 | `machine learning` |
| `tensorflow` | machine learning | 4 | `deep learning` |
| `pytorch` | machine learning | 4 | `deep learning` |
| `data modeling` | ingeniería de datos | 3 | `sql` |
| `etl` | ingeniería de datos | 3 | `sql` |
| `data warehousing` | ingeniería de datos | 4 | `data modeling` |
| `big data` | ingeniería de datos | 3 | — |
| `spark` | ingeniería de datos | 4 | `big data`, `sql` |
| `hadoop` | ingeniería de datos | 4 | `big data`, `linux` |
| `snowflake` | ingeniería de datos | 3 | `data warehousing` |
| `airflow` | ingeniería de datos | 4 | `python`, `etl` |
| `kafka` | ingeniería de datos | 4 | `big data` |
| `aws` | nube | 3 | — |
| `azure` | nube | 3 | — |
| `gcp` | nube | 3 | — |
| `linux` | herramientas | 2 | — |
| `git` | herramientas | 2 | — |
| `docker` | DevOps | 3 | `linux` |
| `kubernetes` | DevOps | 4 | `docker` |
| `ci/cd` | DevOps | 3 | `git` |
| `jira` | herramientas | 1 | — |
| `agile` | ingeniería de software | 1 | — |
| `java` | programación | 3 | — |
| `javascript` | programación | 3 | `html` |
| `typescript` | programación | 3 | `javascript` |
| `c#` | programación | 3 | — |
| `c++` | programación | 4 | — |
| `go` | programación | 3 | — |
| `scala` | programación | 4 | `java` |
| `html` | desarrollo web | 1 | — |
| `css` | desarrollo web | 2 | `html` |
| `react` | desarrollo web | 3 | `javascript` |
| `angular` | desarrollo web | 4 | `typescript` |
| `node.js` | desarrollo web | 3 | `javascript` |
| `rest api` | desarrollo web | 3 | — |
| `microservices` | ingeniería de software | 4 | `rest api`, `docker` |
| `object-oriented programming` | ingeniería de software | 3 | `java` |
| `data structures` | ingeniería de software | 3 | `python` |
| `algorithms` | ingeniería de software | 4 | `data structures` |
| `unit testing` | ingeniería de software | 2 | `object-oriented programming` |
| `postgresql` | bases de datos | 2 | `sql` |
| `mysql` | bases de datos | 2 | `sql` |
| `sql server` | bases de datos | 3 | `sql` |
| `oracle` | bases de datos | 3 | `sql` |
| `nosql` | bases de datos | 3 | — |

**Decisiones dudosas (detalle en `catalog/README.md`):**

- Prerequisites: `power bi` <- `excel`; `object-oriented programming` <- `java` y `data structures` <- `python` (conceptos independientes del lenguaje); `unit testing` <- `object-oriented programming`; `scala` <- `java`; `hadoop` <- `linux`; `big data`, `nosql`, `rest api`, `data cleaning` sin Prerequisites.
- Difficulty: `aws`/`azure`/`gcp` todas 3; `c++` 4 frente a `java`/`c#` 3; `natural language processing` 5; `statistics` 3; `agile` y `jira` 1.
- Categoría: `excel` (análisis de datos o herramientas), `numpy`, `vba`, `linux`, `git`, `rest api`.
- Selección: `agile` y `jira` incluidas por su Frequency en Software Engineer (`scrum` fuera); `looker` y `vba` incluidas para equilibrar Data Analyst; fuera `.net` (8,2 % en SE), `jenkins`, `terraform`, `mongodb`, `c`, `kotlin`, `bash`, `databricks`, `dbt`; `data visualization` incluida como concepto; `business intelligence` excluida.

**Procedimiento de revisión:**

1. Revisar la tabla anterior (o `catalog/skills.csv`) fila por fila y corregir el CSV.
2. Cambiar `reviewed` a `true` en cada fila revisada.
3. Correr `.venv/bin/pytest`; las pruebas validan rangos, Prerequisites existentes y ausencia de ciclos.
4. Anotar aquí quién revisó y qué cambió, marcar el criterio de la compuerta humana y pasar el Status a `done`.

**Revisión humana:** _pendiente (Gabriel u Oscar)._

Nada está en commit: revisar y hacer commit a mano.

## Revisión humana (compuerta)

Oscar aprobó el borrador **tal cual**, sin cambios, el 2026-10-20: todas las filas de `catalog/skills.csv` pasaron a `reviewed=true`. No hubo correcciones a la Difficulty ni a los Prerequisites. Las dudas listadas arriba (Prerequisites discutibles, Difficulty de `c++`, `natural language processing`, `agile` y `jira`, categorías ambiguas) quedan abiertas para que Gabriel las revise si quiere. Status: `done`.
