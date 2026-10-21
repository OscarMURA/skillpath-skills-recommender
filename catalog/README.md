# catalog/

Datos versionados que alimentan la Frequency real por Role. Los datasets originales viven en `datos/` y no se versionan.

## Archivos

| Archivo | Qué es |
|---|---|
| `frequency_by_role.csv` | Frequency de cada Skill por Role. Columnas: `role, skill, offers_with_skill, role_offers, frequency`. Se genera; no se edita a mano. |
| `aliases.csv` | Tabla de alias (`alias,skill`) que unifica variantes de una misma Skill. Ambos lados se normalizan al cargar. |
| `exclusions.txt` | Habilidades blandas y genéricas que se descartan. Una por línea; `#` inicia un comentario. |

## Cómo se calcula

Cada Skill de `job_skills` se normaliza (minúsculas, espacios colapsados, puntuación de borde eliminada), se le aplica el alias (un solo paso, sin encadenar) y después se descartan las exclusiones.

**Frequency = 100 × Offers del Role que mencionan la Skill / Offers del Role con `job_skills` no vacío.** Las Offers con `job_skills` vacío no entran al denominador. Cada Offer cuenta una sola vez por Skill, aunque repita variantes ("python" y "python3").

Un dataset equivale a un Role: Data Analyst, Software Engineer y Data Scientist (carpetas `asaniczka_*` de `datos/`).

## Cómo regenerar

```
.venv/bin/python -m skillpath.build_frequency
```

Opciones: `--datos DIR`, `--out PATH`, `--min-frequency 1.0`, `--top N` (imprime las N Skills más frecuentes por Role, útil para revisar alias y exclusiones) y `--raw` (ignora alias y exclusiones y no escribe el CSV).

Umbral: solo se guardan Skills con Frequency >= 1.0 % (`--min-frequency`) para que el archivo sea pequeño. Excepción: las Skills del Catalog siempre se incluyen, aunque estén por debajo del umbral (hoy Pandas en Data Analyst y Software Engineer, y Excel y Tableau en Software Engineer).

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
