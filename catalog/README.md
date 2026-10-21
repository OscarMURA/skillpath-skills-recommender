# catalog/

Datos versionados que alimentan la Frequency real por Role. Los datasets originales viven en `datos/` y no se versionan.

## Archivos

| Archivo | Qué es |
|---|---|
| `frequency_by_role.csv` | Frequency de cada Skill por Role. Columnas: `role, skill, offers_with_skill, role_offers, frequency`. Se genera; no se edita a mano. |
| `aliases.csv` | Tabla de alias (`alias,skill`) que unifica variantes de una misma Skill. Ambos lados se normalizan al cargar. |
| `exclusions.txt` | Habilidades blandas y genéricas que se descartan. Una por línea; `#` inicia un comentario. |
| `cooccurrence.csv` | Co-ocurrencia de Skills del Catalog en las Offers de cada Role. Columnas: `role, skill_a, skill_b, offers_together, closeness`. Se genera; no se edita a mano. Ver la sección Co-ocurrencia. |
| `frequency_entry_by_role.csv` | Frequency de nivel inicial por Role, detectada en el texto de arshkon. Mismas columnas que `frequency_by_role.csv`. Se genera; no se edita a mano. |
| `detection_calibration.csv` | Calibración del detector de Skills contra asaniczka. Se genera. |
| `skills.csv` | Catalog curado de 64 Skills con categoría, descripción, Difficulty y Prerequisites. Se edita a mano (ver la sección Catalog). |

## Cómo se calcula

Cada Skill de `job_skills` se normaliza (minúsculas, espacios colapsados, puntuación de borde eliminada), se le aplica el alias (un solo paso, sin encadenar) y después se descartan las exclusiones.

**Frequency = 100 × Offers del Role que mencionan la Skill / Offers del Role con `job_skills` no vacío.** Las Offers con `job_skills` vacío no entran al denominador. Cada Offer cuenta una sola vez por Skill, aunque repita variantes ("python" y "python3").

Un dataset equivale a un Role: Data Analyst, Software Engineer y Data Scientist (carpetas `asaniczka_*` de `datos/`).

## Cómo regenerar

```
.venv/bin/python -m skillpath.build_frequency
```

Opciones: `--datos DIR`, `--out PATH`, `--min-frequency 1.0`, `--top N` (imprime las N Skills más frecuentes por Role, útil para revisar alias y exclusiones) y `--raw` (ignora alias y exclusiones y no escribe el CSV).

Umbral: solo se guardan Skills con Frequency >= 1.0 % (`--min-frequency`) para que el archivo sea pequeño. Excepción: las Skills del Catalog siempre se incluyen, aunque estén por debajo del umbral (con el Catalog de 64 Skills, varias quedan por debajo del 1 % en algún Role, sobre todo en Data Analyst). Una Skill del Catalog sin ninguna Offer en un Role no tiene fila ahí y el recomendador le asigna Frequency 0.0.

## Frequency de nivel inicial (`frequency_entry_by_role.csv`)

Complemento para estudiantes y recién graduados (ADR 0002). arshkon no trae Skills técnicas, así que las Skills del Catalog se detectan por diccionario en `description` (`skillpath/skill_detection.py`: regex por Skill con nombre, alias de `aliases.csv` y sinónimos de texto; reglas especiales para ambiguos como `r`, `go`, `excel`, `spark`, `rest api`).

- **Role:** por título, `data analyst`, `data scientist` o `software (engineer|developer|development engineer)`. Un título que coincide con más de un Role se descarta.
- **Nivel inicial = `Entry level` + `Internship`.** `Associate` no entra: asaniczka, la base, ya se compone de Offers Associate y Mid senior, y meterlo diluiría el contraste. Se cambia con `--levels`.
- **Deduplicación:** arshkon repite Offers (por ejemplo "Online Data Analyst" 20 veces con el mismo texto), lo que inflaba la Frequency. Se deduplica por Role con el texto exacto de `description` (strip, espacios colapsados, sin distinguir mayúsculas): cada texto cuenta una vez.
- **Tamaño de muestra** (`role_offers`, igual para todas las filas de un Role), Offers antes -> después de deduplicar, por nivel:

| Role | Entry level | Internship | Associate (no usado) | Nivel inicial usado (antes -> después) |
|---|---|---|---|---|
| Data Analyst | 116 -> 78 | 2 -> 2 | 39 -> 37 | 118 -> 80 |
| Software Engineer | 217 -> 208 | 8 -> 8 | 84 -> 76 | 225 -> 216 |
| Data Scientist | 56 -> 46 | 1 -> 1 | 13 -> 11 | 57 -> 47 |

  Las cifras por nivel deduplican dentro de cada nivel; la última columna deduplica sobre Entry + Internship juntos. El comando imprime esta tabla. Muestras pequeñas: úsese con cautela y como complemento de la Frequency base.
- **Frequency** = 100 × Offers del Role (nivel inicial) cuya descripción menciona la Skill / `role_offers`, redondeada a 2 decimales; cada Offer cuenta una vez por Skill.
- **Contrato:** hay una fila por cada Role y cada Skill fiable del Catalog, también con 0 Offers. **Una Skill ausente** de este archivo está excluida por no fiable (ver calibración): el recomendador debe usar solo la Frequency base para ella. Una Skill presente con `frequency` 0 significa que sí se pudo medir y no apareció.

```
.venv/bin/python -m skillpath.build_entry_frequency
```

Opciones: `--datos DIR`, `--out PATH`, `--levels "Entry level" "Internship"`, `--calibration-out PATH`, `--skip-calibration` (usa la calibración guardada, tarda unos 7 s en vez de unos 2,3 min), `--top N`. La salida es determinista (byte a byte) y arshkon se lee por trozos de 2.000 filas con solo 3 columnas.

## Calibración del detector (`detection_calibration.csv`)

Se aplica el mismo detector a `job_summary` de todas las Offers de asaniczka con `job_summary` y `job_skills` no vacíos (12.705, 9.367 y 4.336 Offers) y se compara, sobre las MISMAS Offers, con la Frequency de `job_skills` (con alias y exclusiones de siempre). Columnas: `role, skill, text_frequency, skills_frequency, reference_frequency` (la de `frequency_by_role.csv`), `diff` (puntos), `ratio` (`text/skills`, vacío si `skills_frequency` es 0) y `reliable` (igual para los tres Roles de una Skill).

La calibración no deduplica `job_summary`: asaniczka también tiene textos exactos repetidos (12.705 -> 11.021 distintos en Data Analyst, 9.367 -> 7.743 en Software Engineer, 4.336 -> 3.450 en Data Scientist), dato solo informativo.

**Regla de fiabilidad:** una Skill es no fiable si en cualquier Role `|diff| > 10` puntos, o si en un Role con `skills_frequency >= 2` el `ratio` queda fuera de [0.5, 2.0]. Las no fiables se excluyen de `frequency_entry_by_role.csv`.

Antes de excluir se revisaron falsos positivos reales y se ajustó el detector: `statistics` ya no cuenta "statistical", `azure` no cuenta "Azure DevOps", `oracle` no cuenta Oracle ERP/Fusion/Cloud ERP, `ci/cd` no cuenta "continuous integration", `object-oriented programming` solo cuenta "object-oriented programming/languages" y `OOP`, y `algorithms` no cuenta "machine learning algorithms".

**Excluidas hoy:** `algorithms`, `big data`, `microservices`, `statistics`. El desvío es sobre todo ruido de `job_skills` (extracción que omite Skills realmente mencionadas en el texto), no error del detector: los falsos positivos revisados eran menciones reales. Aun así no hay forma de saber cuál de las dos fuentes se acerca más a la verdad, así que se excluyen por prudencia.

## Co-ocurrencia (`cooccurrence.csv`)

Alimenta la similitud entre Skills (`docs/similarity.md`). Para cada Role y cada par de Skills del Catalog que aparecen en la misma Offer (con la misma normalización, alias y exclusiones que la Frequency) se guarda `offers_together` y `closeness = offers_together / sqrt(offers_a × offers_b)` (coeficiente de Ochiai, entre 0 y 1). Cada par aparece una vez, con `skill_a < skill_b` en orden alfabético. Es por Role porque la cercanía entre Skills cambia según el mercado (por ejemplo, `python` con `pandas` frente a `python` con `java`).

Se descartan los pares con menos de 5 Offers juntas (`--min-offers`) para mantener el archivo pequeño: 3.906 filas, unos 163 KB. Solo se usan las Offers de los tres datasets de asaniczka, no arshkon ni rajatraj0502.

```
.venv/bin/python -m skillpath.build_cooccurrence
```

Opciones: `--datos DIR`, `--out PATH`, `--min-offers 5`. La salida es determinista: regenerar produce un archivo idéntico byte a byte.

## Criterios

- **Alias:** solo variantes claras de la MISMA Skill (ortografía, abreviatura, nombre completo o comercial). No se fusionan Skills distintas (`sql` y `mysql` quedan separadas; `data visualization` no es `tableau`).
- **Exclusión:** no es una Skill técnica concreta que se pueda aprender como lenguaje, herramienta, framework o concepto: habilidades blandas, gestión genérica, títulos y áreas de estudio. Ante la duda se deja la Skill.

## Limitaciones

- Un dataset = un Role; no hay Offers que pertenezcan a varios Roles.
- Las Offers son de LinkedIn, en inglés y principalmente de EE. UU.
- `job_skills` viene ya extraído (no se leyó el texto de la Offer), con ruido propio del dataset.
- La normalización solo quita puntuación de borde sobrante (comillas, paréntesis, guiones sueltos, y punto, coma, punto y coma o dos puntos finales); conserva `.net`, `c++`, `c#`, `node.js` y `ci/cd`.

## Casos dudosos para revisión humana

- Se conservaron como conceptos técnicos: `data analysis`, `statistics`, `machine learning`, `data science`, `agile`, `data visualization`, `software engineering`, `programming`, `troubleshooting`, `mathematics`, `documentation`.
- Se conservaron áreas de dominio, no técnicas en sentido estricto: `accounting`, `finance`, `financial analysis`, `budgeting`, `forecasting`, `risk management`, `compliance`, `business analysis`.
- `.net`: `dotnet` y `dot net` se unifican en `.net`. `asp.net`, `.net core` y `.net framework` quedan como Skills distintas (podrían revisarse).
- Alias discutibles: `rest` -> `rest api`; `ai` -> `artificial intelligence`; `scrum master` -> `scrum`; `agile development`/`agile practices`/`agile methodology` -> `agile` (inflan `agile`, sobre todo en Software Engineer); `html5` -> `html`; `golang` -> `go`; `vue` -> `vue.js`.
- No se fusionaron (podrían unirse): `data analytics` con `data analysis`, `statistical analysis` con `statistics`, `pyspark` con `spark`, `databases` con `relational databases`, `c/c++` con `c` y `c++`, `ci/cd` con `continuous integration`.
- Se excluyeron `research`, `training`, `customer service`, `stakeholder management`, `process improvement` y `change management` por ser genéricas; revisar si alguna se considera Skill.
- Se excluyeron áreas de estudio (`computer science`, `economics`, `engineering`) y el rótulo `business analyst`.

## Catalog (`skills.csv`)

Catalog redactado por un agente (ADR 0001) y aprobado por un humano (Oscar). Tiene 64 Skills; toda fila nace con `reviewed=false` hasta que un humano la revisa y hoy están todas en `true`.

### Columnas y formato

CSV en UTF-8, separado por comas, con encabezado: `name,category,description,difficulty,prerequisites,reviewed`.

- `name`: nombre normalizado, idéntico a la columna `skill` de `frequency_by_role.csv`. Toda Skill del Catalog existe en la tabla de al menos un Role.
- `category`: lista cerrada: `programación`, `bases de datos`, `análisis de datos`, `visualización`, `nube`, `DevOps`, `machine learning`, `ingeniería de datos`, `desarrollo web`, `ingeniería de software`, `herramientas`.
- `description`: una o dos frases en español; va entre comillas dobles si contiene comas.
- `difficulty`: entero de 1 a 5 (escala abajo).
- `prerequisites`: nombres de otras Skills del Catalog separados por `;` sin espacios (por ejemplo `machine learning;pandas`). Vacío si no tiene.
- `reviewed`: `true` o `false`.

### Escala de Difficulty

Difficulty es la complejidad intrínseca de adquirir la Skill, sin contar los Prerequisites que falten (eso lo cubre el Effort).

| Nivel | Significado | Ejemplos del Catalog |
|---|---|---|
| 1 | Introductoria: se maneja en horas o pocos días, sin base previa. | `html`, `agile`, `jira` |
| 2 | Básica: unas semanas de práctica para trabajar con soltura. | `sql`, `excel`, `python`, `git`, `tableau` |
| 3 | Intermedia: requiere varios meses y conceptos propios. | `pandas`, `statistics`, `java`, `aws`, `react`, `etl` |
| 4 | Avanzada: conceptos exigentes o sistemas con muchas piezas. | `machine learning`, `spark`, `kubernetes`, `microservices`, `c++` |
| 5 | Especializada: base matemática o conceptual fuerte y años para dominarla. | `deep learning`, `natural language processing` |

### Criterios de selección

- Fuente: la Frequency de los tres Roles en `frequency_by_role.csv`. Se tomaron las Skills técnicas más frecuentes de cada Role, no solo del Role con más datos.
- Equilibrio: las unas 15 Skills técnicas concretas más frecuentes de cada Role están incluidas. Skills del Catalog con Frequency >= 1 %: Data Analyst 36, Software Engineer 43 y Data Scientist 57 (con la tabla regenerada, las 64 tienen Frequency > 0 en los tres Roles, pero muchas quedan por debajo del 1 % fuera de su Role natural). Data Analyst queda más bajo porque sus Offers mencionan más herramientas de dominio y ofimática que Skills técnicas distintas.
- Solo Skills técnicas concretas que se pueden aprender: lenguajes, herramientas, frameworks, plataformas y conceptos técnicos bien definidos.
- Se excluyeron:
  - habilidades blandas (ya en `exclusions.txt`);
  - rótulos paraguas: `data analysis`, `data analytics`, `analytics`, `data science`, `software engineering`, `software development`, `programming`, `reporting`, `testing`, `documentation`, `troubleshooting`, `business analysis`, `business intelligence`, `data management`, `cloud computing`, `artificial intelligence`;
  - áreas de dominio: `accounting`, `finance`, `financial analysis`, `budgeting`, `forecasting`, `risk management`, `compliance`;
  - paquetes ofimáticos genéricos: `microsoft office`, `word`, `powerpoint`;
  - duplicados o mezclas: `c/c++` (quedan `c++` y no `c`), `pyspark` (se conserva `spark`), `statistical analysis` (se conserva `statistics`), `continuous integration` (se conserva `ci/cd`), `data warehouse` y `databases`.
- Frente a un empate se prefirió la Skill con más Frequency y más aprendible por sí sola. Quedaron fuera por cupo, aunque son defendibles: `jenkins`, `terraform`, `mongodb`, `scrum`, `data engineering`, `data governance`, `c`, `kotlin`, `matlab`, `bash`, `redshift`, `databricks`, `dbt`, `elasticsearch`.

### Criterios de Prerequisites

- Un Prerequisite es una Skill del propio Catalog que es necesaria o claramente conveniente conocer antes de aprender la otra.
- Solo directos, no transitivos: si `pandas` requiere `python` y `scikit-learn` requiere `pandas`, `scikit-learn` no lista `python`. Normalmente son de 0 a 3.
- No hay ciclos.
- Difficulty y Prerequisites son juicio experto (ADR 0001), no dato observado en las Offers. Se documenta como limitación en la Parte 3.

### Proceso de revisión humana

1. Gabriel u Oscar revisan Difficulty y Prerequisites fila por fila (y de paso categoría y descripción).
2. Corrigen directamente `skills.csv`.
3. Cambian `reviewed` a `true` en las filas revisadas.
4. Anotan quién revisó y qué cambió en la sección Handoff del ticket 03.
5. Tras editar, corren `.venv/bin/pytest`: las pruebas validan el Catalog como datos (nombres, rangos, Prerequisites existentes y ausencia de ciclos).
6. Si se agrega una Skill nueva, regenerar la Frequency con `.venv/bin/python -m skillpath.build_frequency` (requiere `datos/`): el build incluye las Skills del Catalog aunque estén por debajo del 1 %, de modo que la Skill nueva obtiene su Frequency en los tres Roles.

### Decisiones dudosas

Categoría o Difficulty defendible de dos maneras:
- `excel` y `sas` están en `análisis de datos`; `excel` también podría ser `herramientas`.
- `numpy` está en `análisis de datos` (podría ser `programación`) y `scikit-learn` en `machine learning`.
- `vba` está en `programación` pero es una herramienta ligada a Excel.
- `linux` y `git` están en `herramientas`; `linux` podría ir en `DevOps` y `git` en `ingeniería de software`.
- `aws`, `azure` y `gcp` tienen Difficulty 3 por igual, aunque el dominio completo de una nube es mucho más amplio.
- `statistics` (3) y `machine learning` (4) dependen de la profundidad esperada; `natural language processing` (5) cambia si se piensa en uso de bibliotecas o en investigación.
- `c++` (4) frente a `java`/`c#` (3): la gestión manual de memoria justifica el nivel, pero es discutible.
- `kafka`, `hadoop` y `spark` están en `ingeniería de datos`.
- `rest api` está en `desarrollo web`; podría ser `ingeniería de software`.

Prerequisites discutibles:
- `power bi` requiere `excel`, pero se puede aprender sin él.
- `object-oriented programming` requiere `java` y `data structures` requiere `python`: son conceptos independientes del lenguaje, y se eligió un lenguaje del Catalog como vehículo.
- `unit testing` requiere `object-oriented programming`, aunque se puede probar código sin objetos.
- `big data`, `nosql` y `rest api` quedaron sin Prerequisites; podrían depender de `sql` o de un lenguaje.
- `hadoop` requiere `linux`; `snowflake` requiere solo `data warehousing` (SQL llega por transitividad); `airflow` requiere `etl` además de `python`.
- `deep learning` no lista `python` (llega por `machine learning`); `tensorflow` y `pytorch` tampoco.
- `scala` requiere `java` por cercanía de la JVM, aunque no es obligatorio.
- `data cleaning` no tiene Prerequisites porque se puede hacer en `excel`, `sql` o `pandas`.

Inclusiones y exclusiones discutibles:
- `agile` y `jira` se incluyeron como excepción metodológica y de herramienta por su alta Frequency en Software Engineer (agile 33,9 %); `agile` es una práctica más que una Skill técnica, y `scrum` quedó fuera.
- `a/b testing` y `data cleaning` son más técnicas aplicadas que herramientas.
- `oracle` se incluye como base de datos y no como ecosistema Oracle completo.
- `looker` y `vba` están con Frequency baja (cerca de 1,5 %) y solo en Data Analyst; se incluyeron para equilibrar ese Role.
- `.net` no se incluyó aunque tiene 8,2 % en Software Engineer; `c#` cubre parte de ese ecosistema.
- `data visualization` es un concepto, distinto de las herramientas `tableau` y `power bi`.
- `business intelligence` se excluyó como rótulo; podría incluirse como concepto.
