# Evaluación y métricas de sesgo

Este documento explica cómo se evaluó SkillPath y qué sesgos tiene. Está escrito para quien apenas empieza con sistemas recomendadores: no hace falta saber nada previo, solo leer los términos de `GLOSSARY.md`. Sirve de base para el punto 2.3 del taller (evaluación) y para la Parte 3 (3.1, qué mide la evaluación, y 3.2, sesgos). El código está en `skillpath/evaluate.py` y sus pruebas en `tests/test_evaluate.py` y `tests/test_personas.py`; todo es determinista y sin LLM (ADR 0003). Las cifras salen de ejecutar el código y de los CSV de `reports/`; ninguna está estimada a mano, salvo donde se dice.

## Resumen

- **Evaluación leave-one-skill-out** (se oculta una Skill de cada Offer de prueba y se mide si el sistema la recupera): 1.500 casos, 500 por Role, con Frequency y co-ocurrencia recalculadas solo con Offers de entrenamiento.
- **El sistema completo es muy superior al azar:** hit@10 global 0.670 frente a 0.173 del azar; MRR 0.362 frente a 0.080.
- **Pero no supera claramente a la línea base de Frequency pura (popularity):** empatan en hit@5 global (0.496), el sistema completo gana 1 punto en hit@10 (0.670 frente a 0.660) y pierde en MRR (0.362 frente a 0.374). Con 1.500 casos, diferencias de 1 punto están dentro del ruido.
- **La similitud aporta una mejora modesta** sobre la fórmula sin similitud: +1.4 puntos en hit@5, +2.0 en hit@10 y +0.024 de MRR (global).
- **Por Difficulty se ve la causa:** el Effort hunde las Skills de Difficulty 4-5 (hit@10 0.223 y 0.000 frente a 0.451 y 0.222 de la línea base) y favorece las de Difficulty 1-2. Es esperable: el sistema prioriza lo que conviene aprender primero, no solo lo que la Offer pide.
- **Sesgos medidos:** con K = 10, cada Role cubre solo el 34-44 % del Catalog y 16 de las 64 Skills no aparecen en ningún Role (incluyen `deep learning`, `scikit-learn`, `pytorch`, `tensorflow` y `airflow`); la categoría machine learning recibe 4.7 % de la exposición incluso en Data Scientist; la Difficulty 4-5 casi no se expone; la exposición sigue de cerca a la Frequency (Spearman 0.76-0.85).
- **Nivel inicial frente a con experiencia:** los Learning paths se parecen mucho (Jaccard@10 de 0.75 a 0.82), así que el complemento de nivel inicial cambia poco. Hay una subida dudosa de `sas` en Data Scientist inicial (muestra de 47 Offers de arshkon, detección por texto).
- **Seis Learner profiles de prueba:** cumplen sus propiedades salvo tres expectativas que resultaron erróneas (P4, P5 y P6) y se documentan. Los Learning paths esperados los escribió un agente y **están pendientes de revisión humana**.

## Cómo reproducir

```
.venv/bin/python -m skillpath.evaluate
```

Opciones: `--datos DIR`, `--out reports/`, `--sample-per-role 500`, `--seed 42`, `--test-fraction 0.2`. Tarda unos 18 s y es determinista: dos ejecuciones dieron CSV idénticos byte a byte. Requiere `datos/` (no se versiona; ver `datos/README.md`). El comando no modifica `catalog/frequency_by_role.csv` ni `catalog/cooccurrence.csv`: calcula el hash de ambos antes y después y aborta si cambian.

| Archivo en `reports/` | Qué contiene |
|---|---|
| `partition_summary.csv` | Tamaños de la partición por Role, Offers elegibles y muestreadas, y cifras de fuga. |
| `loo_metrics.csv` | hit@5, hit@10, MRR, rango medio y mediano por Role (y `GLOBAL`) y por método. |
| `loo_by_difficulty.csv` | hit@10, MRR y rango medio según la Difficulty de la Skill oculta. |
| `exposure_concentration.csv` | Concentración de la exposición: top-5, top-10, Gini y entropía normalizada. |
| `exposure_by_category.csv` | Exposición por categoría del Catalog frente a su peso en el Catalog. |
| `exposure_by_difficulty.csv` | Exposición por Difficulty frente a su peso en el Catalog. |
| `coverage.csv` | Cuántas Skills del Catalog aparecen al menos una vez en el top K. |
| `never_recommended.csv` | Skills que no aparecen en ningún top 10 (K = 10, grupo `all`), por Role y `GLOBAL`. |
| `exposure_vs_frequency.csv` | Correlación de Spearman entre exposición y Frequency. |
| `entry_vs_experienced.csv` | Jaccard, Kendall tau y Spearman entre el Learning path inicial y el de con experiencia. |
| `entry_vs_experienced_shifts.csv` | Skills que más suben o bajan al pasar de con experiencia a inicial. |

## Metodología leave-one-skill-out

### La idea

Un recomendador se puede evaluar escondiéndole una respuesta y viendo si la encuentra. Aquí: se toma una Offer de prueba, se esconde una de sus Skills del Catalog, se construye un Learner simulado que domina las demás y se mira en qué puesto del Learning path aparece la Skill escondida. Si el sistema entiende qué se pide junto con qué, la escondida debería salir arriba.

### Partición entrenamiento / prueba (80/20)

Frequency y co-ocurrencia salen de las mismas Offers que se usarían para evaluar; si no se separan, el sistema "vería" la respuesta. Por eso las Offers de cada Role se parten en 80 % entrenamiento y 20 % prueba con un hash estable (sha1, no el `hash()` de Python, que cambia entre ejecuciones).

**La clave del hash no es el `job_link`.** Es el conjunto de Skills normalizadas de la Offer (mismos alias y exclusiones que la Frequency); para una Offer sin Skills, el `job_link`. Razón: hay muchas Offers casi idénticas (plantillas con el mismo conjunto de Skills). Con un hash de `job_link`, una Offer de prueba podría tener una copia idéntica en entrenamiento y el sistema la "recordaría". Con la clave por conjunto de Skills, las copias caen siempre del mismo lado.

| Role | Offers | Entrenamiento | Prueba | Prueba elegible | Muestreadas | Fuga (clave por Skills) | Fuga si se hubiera usado `job_link` |
|---|---|---|---|---|---|---|---|
| Data Analyst | 12.894 | 10.321 | 2.573 | 1.257 | 500 | 0 | 18 |
| Software Engineer | 9.380 | 7.523 | 1.857 | 1.580 | 500 | 0 | 41 |
| Data Scientist | 4.342 | 3.438 | 904 | 774 | 500 | 0 | 7 |

(`partition_summary.csv`.) "Fuga" cuenta Offers de prueba cuyo conjunto de Skills es idéntico al de alguna Offer de entrenamiento. El grupo más grande de Offers con el mismo conjunto de Skills tiene 4, 5 y 7 Offers por Role. La fuga alternativa es chica en términos absolutos (66 Offers en total), pero con la clave por Skills es exactamente cero y eso se puede afirmar sin matices.

Una cifra distinta, y esperable: de las 500 Offers muestreadas, 299 (Data Analyst), 188 (Software Engineer) y 135 (Data Scientist) tienen un conjunto de Skills **del Catalog** que también aparece en alguna Offer de entrenamiento (`sampled_catalog_set_seen_in_train`). No es fuga de la misma Offer: con solo 64 Skills en el Catalog, muchas Offers distintas se reducen al mismo subconjunto (por ejemplo, `sql` y `excel`), aunque su `job_skills` completo sea distinto.

### Recalcular Frequency y co-ocurrencia solo con entrenamiento

Con las Offers de entrenamiento se recalculan, en memoria, con los mismos parámetros que los artefactos de producción:

- **Frequency:** se guardan las Skills con Frequency de al menos 1 % o que pertenezcan al Catalog, redondeadas a 2 decimales (igual que `build_frequency`).
- **Co-ocurrencia:** Ochiai con `min_offers = 5` (igual que `build_cooccurrence`; ver `docs/similarity.md`).

Estas tablas se inyectan en `recommend` con un administrador de contexto (`use_artifacts`) que sustituye temporalmente la Frequency del Catalog y el cargador de co-ocurrencia, limpia el caché del modelo de similitud y lo restaura todo al salir, incluso si hay un error. **Los archivos versionados de `catalog/` no se tocan.** `tests/test_evaluate.py` lo comprueba: una Offer de prueba no cambia las tablas de entrenamiento (`test_training_artifact_excludes_test_offers`), las Skills del Catalog se conservan aunque estén bajo el umbral (`test_training_artifact_keeps_catalog_skills_below_threshold`) y `recommend`, la Frequency y la co-ocurrencia quedan restauradas, también tras una excepción (`test_use_artifacts_restores_frequency_cooccurrence_and_recommend`, `test_use_artifacts_restores_on_exception`). Además el comando compara el hash de los dos CSV antes y después.

### El Learner simulado

Para cada Offer de prueba elegible:

- **Elegible** = tiene al menos 2 Skills del Catalog (si no, al esconder una no queda nada que declarar). Las Offers con `job_skills` vacío o con menos de 2 Skills del Catalog se descartan (por ejemplo, en Data Analyst, de las 2.573 Offers de prueba, 40 tienen `job_skills` vacío y 1.276 tienen menos de 2 Skills del Catalog).
- **Muestra:** hasta 500 Offers elegibles por Role, con semilla (42).
- **Skill oculta:** una de las Skills del Catalog de la Offer, elegida con un generador aleatorio con semilla.
- **Learner profile:** Role de la Offer; las demás Skills del Catalog de la Offer, todas en Mastery level intermedio (es decir, dominadas); sin intereses; con experiencia (`experienced`).

### Métricas

Para cada caso, la "posición" es el puesto de la Skill oculta en el Learning path, empezando en 1. Hay en promedio unas 59 candidatas (las del Catalog que el Learner no domina). Ejemplo sencillo con tres casos donde la Skill oculta salió en los puestos 2, 8 y 30:

| Métrica | Qué mide | Ejemplo |
|---|---|---|
| hit@5 | Proporción de casos con la Skill oculta entre los 5 primeros. | Solo el puesto 2: 1/3 = 0.33 |
| hit@10 | Ídem con los 10 primeros. | Puestos 2 y 8: 2/3 = 0.67 |
| MRR | Promedio de 1/puesto: premia mucho los primeros puestos. | (1/2 + 1/8 + 1/30) / 3 = 0.22 |
| Rango medio | Promedio de los puestos (menor es mejor). | (2 + 8 + 30) / 3 = 13.3 |
| Rango mediano | El puesto del medio (menos sensible a casos muy malos). | 8 |

Referencia: con 59 candidatas, un orden aleatorio acierta hit@10 con probabilidad 10/59 = 0.17, que es lo que se observa para el método aleatorio (0.173).

## Los cuatro métodos comparados

| Método (nombre en los CSV) | Qué hace | Para qué sirve en la comparación |
|---|---|---|
| Línea base de Frequency pura (`popularity`) | Ordena las candidatas por la Frequency del Role en las Offers de entrenamiento, desempate alfabético. No mira Effort, Prerequisites ni similitud. | Es la línea base inteligente: lo que haría quien solo mirase "qué piden más las Offers". Lo que no supere esto no aporta sobre la Frequency. |
| Fórmula firmada sin similitud (`formula_no_similarity`) | `Frequency / Effort` con desempates y ajuste topológico por Prerequisites (`docs/priority-formula.md`); similitud forzada a 0. | Aísla el efecto del Effort y de los Prerequisites. |
| Sistema completo (`full`) | La fórmula `Frequency × (1 + similitud) / Effort` con ajuste topológico, tal como se entrega. | Lo que realmente recibe un Learner. |
| Aleatorio (`random`) | Orden aleatorio de las candidatas, con semilla. | Piso: cualquier método útil debe superarlo por mucho. |

Nota: `popularity` es el nombre técnico del método; en este documento se llama "línea base de Frequency pura" porque en SkillPath Frequency es el término del glosario.

## Resultados de leave-one-skill-out

### Por Role y global

`loo_metrics.csv`, 500 casos por Role y 1.500 globales. Las columnas hit@5, hit@10 y MRR: más alto es mejor; rango medio y mediano: más bajo es mejor.

| Role | Método | hit@5 | hit@10 | MRR | Rango medio | Rango mediano |
|---|---|---|---|---|---|---|
| Data Analyst | Frequency pura | 0.604 | 0.754 | 0.443 | 7.42 | 3 |
| Data Analyst | Fórmula sin similitud | 0.622 | 0.742 | 0.416 | 7.77 | 4 |
| Data Analyst | Sistema completo | 0.632 | 0.756 | 0.455 | 7.30 | 3 |
| Data Analyst | Aleatorio | 0.074 | 0.134 | 0.074 | 32.29 | 32.5 |
| Software Engineer | Frequency pura | 0.398 | 0.622 | 0.292 | 10.46 | 8 |
| Software Engineer | Fórmula sin similitud | 0.386 | 0.620 | 0.244 | 11.04 | 8 |
| Software Engineer | Sistema completo | 0.392 | 0.644 | 0.262 | 10.67 | 7 |
| Software Engineer | Aleatorio | 0.076 | 0.174 | 0.075 | 31.24 | 32 |
| Data Scientist | Frequency pura | 0.486 | 0.604 | 0.386 | 12.30 | 6 |
| Data Scientist | Fórmula sin similitud | 0.438 | 0.588 | 0.354 | 12.79 | 7 |
| Data Scientist | Sistema completo | 0.464 | 0.610 | 0.370 | 11.93 | 6 |
| Data Scientist | Aleatorio | 0.108 | 0.210 | 0.092 | 27.83 | 26 |
| **GLOBAL** | Frequency pura | 0.496 | 0.660 | 0.374 | 10.06 | 6 |
| **GLOBAL** | Fórmula sin similitud | 0.482 | 0.650 | 0.338 | 10.53 | 6 |
| **GLOBAL** | **Sistema completo** | **0.496** | **0.670** | **0.362** | **9.97** | **6** |
| **GLOBAL** | Aleatorio | 0.086 | 0.173 | 0.080 | 30.45 | 30 |

### Por Difficulty de la Skill oculta

`loo_by_difficulty.csv`, hit@10 global. `n` es el número de casos cuya Skill oculta tiene esa Difficulty.

| Difficulty | n | Frequency pura | Fórmula sin similitud | Sistema completo | Aleatorio |
|---|---|---|---|---|---|
| 1 | 98 | 0.602 | 0.969 | 0.949 | 0.184 |
| 2 | 653 | 0.848 | 0.893 | 0.902 | 0.158 |
| 3 | 525 | 0.533 | 0.501 | 0.528 | 0.192 |
| 4 | 206 | 0.451 | 0.165 | 0.223 | 0.165 |
| 5 | 18 | 0.222 | 0.000 | 0.000 | 0.167 |

### Interpretación honesta

1. **El sistema completo es muy superior al azar** en los tres Roles (hit@10 de 0.61 a 0.76 frente a 0.13-0.21). Recupera la Skill escondida mucho mejor de lo que daría la suerte.
2. **No supera claramente a la línea base de Frequency pura.** Globalmente empata en hit@5 (0.496), gana 1 punto en hit@10 y pierde en MRR (0.362 frente a 0.374). Por Role es mixto: gana en Data Analyst (hit@5 0.632 frente a 0.604; MRR 0.455 frente a 0.443) y en hit@10 de los tres Roles, pero pierde en hit@5 y MRR de Software Engineer y Data Scientist. Con 500 casos por Role y 1.500 globales, el error de un hit@10 de ~0.67 ronda ±1.2 puntos (cálculo binomial a mano, no medido), por lo que diferencias de 1 punto no se pueden distinguir del ruido.
3. **La similitud mejora algo la fórmula sin similitud** en casi todo: global +1.4 puntos en hit@5, +2.0 en hit@10, +0.024 en MRR. Es una mejora modesta, coherente con que los pesos de la similitud no se ajustaron con datos (ver Limitaciones).
4. **La tabla por Difficulty explica por qué.** El Effort suma la Difficulty al denominador, así que el sistema empuja hacia arriba las Skills de Difficulty 1-2 (hit@10 0.949 y 0.902, frente a 0.602 y 0.848 de la línea base) y hunde las de Difficulty 4-5 (0.223 y 0.000, frente a 0.451 y 0.222). En Difficulty 4 el sistema completo apenas supera al azar (0.223 frente a 0.165). Difficulty 5 tiene solo 18 casos: es una indicación, no una cifra firme.
5. **Esto es esperable y no es necesariamente un defecto.** La evaluación mide si el sistema recupera lo que una Offer pide. El sistema tiene otro objetivo: proponer qué conviene aprender primero, y por eso penaliza lo que cuesta mucho. Una Skill de Difficulty 5 que aparece en una Offer "debería" recuperarse según esta prueba, pero no necesariamente aprenderse primero. Ninguna métrica offline mide si el Learner aprende mejor.

## Personas de prueba

> **Rutas esperadas escritas por un agente: pendientes de revisión humana.**

Seis Learner profiles realistas que cubren los tres Roles y los niveles inicial y con experiencia. Las expectativas son propiedades (no un orden exacto), formuladas antes de ejecutar `recommend`, a partir del razonamiento de dominio y de la fórmula firmada `Frequency × (1 + similitud) / Effort`, con Effort = Difficulty + Prerequisites faltantes. Los perfiles están en `tests/test_personas.py` (40 pruebas verifican las propiedades); las tablas de top 10 salen de ejecutar `recommend` con esos perfiles, no están escritas a mano. Comunes a todas: Learning path sin duplicados con todo el Catalog menos lo dominado; determinista; cada Skill después de sus Prerequisites faltantes.

### P1. Data Analyst (inicial)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Estudiante sin Skills declaradas que apunta a Data Analyst (nivel inicial).

- Role: Data Analyst; experience_level: `entry`
- Skills conocidas (Mastery level): ninguna
- Intereses: ninguno; `cold_start`: True

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | sql | 38.1 | 2 | 0.00 |
| 2 | excel | 32.4 | 2 | 0.00 |
| 3 | agile | 11.7 | 1 | 0.00 |
| 4 | python | 22.1 | 2 | 0.00 |
| 5 | tableau | 18.3 | 2 | 0.00 |
| 6 | data visualization | 17.8 | 2 | 0.00 |
| 7 | power bi | 19.7 | 3 | 0.00 |
| 8 | r | 10.3 | 3 | 0.00 |
| 9 | jira | 2.7 | 1 | 0.00 |
| 10 | data cleaning | 5.1 | 2 | 0.00 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| Perfil vacío: `cold_start` es verdadero y el orden usa solo Frequency y Effort. | sí |
| `sql` y `excel` (Frequency alta, Difficulty 2, sin Prerequisites) están en el top 5. | sí |
| Al menos 5 de las 10 Skills más frecuentes del Role están en el top 10. | sí |
| `python` antes de `pandas`, `excel` antes de `power bi`, `sql` antes de `looker`. | sí |
| `deep learning`, `tensorflow`, `pytorch` y `kubernetes` fuera del top 10 (Effort alto, rara vez en Offers de Data Analyst). | sí |

### P2. Data Analyst (con experiencia)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Analista con experiencia que domina `sql` (avanzado), `excel` y `tableau` (intermedio).

- Role: Data Analyst; experience_level: `experienced`
- Skills conocidas (Mastery level): sql (advanced), excel (intermediate), tableau (intermediate)
- Intereses: ninguno; `cold_start`: False

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | power bi | 18.4 | 2 | 0.80 |
| 2 | data visualization | 18.1 | 2 | 0.75 |
| 3 | python | 16.9 | 2 | 0.61 |
| 4 | agile | 11.0 | 1 | 0.07 |
| 5 | jira | 4.9 | 1 | 0.09 |
| 6 | r | 9.6 | 3 | 0.55 |
| 7 | data modeling | 6.6 | 3 | 0.49 |
| 8 | statistics | 5.6 | 3 | 0.57 |
| 9 | data mining | 7.4 | 4 | 0.54 |
| 10 | data cleaning | 3.1 | 2 | 0.60 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| Ninguna Skill dominada aparece en el Learning path. | sí |
| `power bi` (necesita excel, dominada) y `data visualization` (muy cercana a tableau) están en el top 10. | sí |
| `python` en el top 10 (frecuente para analistas, Difficulty 2). | sí |
| `deep learning`, `tensorflow`, `pytorch`, `kubernetes`, `angular`, `hadoop` fuera del top 10. | sí |

### P3. Software Engineer (inicial)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Recién graduado de Software Engineer con `python`, `java` y `git` en Mastery level básico (nivel inicial).

- Role: Software Engineer; experience_level: `entry`
- Skills conocidas (Mastery level): python (basic), java (basic), git (basic)
- Intereses: ninguno; `cold_start`: False

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | agile | 35.4 | 1 | 0.66 |
| 2 | python | 35.7 | 2 | 0.58 |
| 3 | java | 42.0 | 3 | 0.59 |
| 4 | html | 17.1 | 1 | 0.15 |
| 5 | sql | 23.4 | 2 | 0.55 |
| 6 | git | 22.5 | 2 | 0.26 |
| 7 | aws | 25.6 | 3 | 0.55 |
| 8 | linux | 15.8 | 2 | 0.52 |
| 9 | javascript | 32.8 | 4 | 0.33 |
| 10 | jira | 6.3 | 1 | 0.60 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| Las tres Skills básicas siguen siendo candidatas (básico no es dominada). | sí |
| `python` y `java` en el top 10; `git` en el top 15. | sí |
| Las Skills básicas cuentan como Prerequisites faltantes: `java` < `object-oriented programming` < `unit testing`; `git` < `ci/cd`; `python` < `data structures` < `algorithms`. | sí |
| `agile` o `html` en el top 5; `tensorflow`, `pytorch`, `hadoop`, `scala` fuera del top 10. | sí |

### P4. Software Engineer (con experiencia)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Desarrollador con experiencia que domina `java`, `git` (avanzado), `javascript` y `sql` (intermedio).

- Role: Software Engineer; experience_level: `experienced`
- Skills conocidas (Mastery level): java (advanced), javascript (intermediate), sql (intermediate), git (advanced)
- Intereses: ninguno; `cold_start`: False

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | agile | 33.9 | 1 | 0.68 |
| 2 | python | 37.9 | 2 | 0.64 |
| 3 | html | 14.1 | 1 | 0.34 |
| 4 | jira | 9.8 | 1 | 0.59 |
| 5 | aws | 27.8 | 3 | 0.55 |
| 6 | linux | 15.0 | 2 | 0.38 |
| 7 | react | 19.4 | 3 | 0.43 |
| 8 | c# | 19.2 | 3 | 0.37 |
| 9 | typescript | 15.6 | 3 | 0.56 |
| 10 | go | 14.9 | 3 | 0.56 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| `python` y `html` en el top 10. | sí |
| Al menos 4 de {typescript, node.js, react, docker, ci/cd, rest api} en el top 15 y `react`, `typescript` en el top 10 (expectativa corregida, ver discrepancias). | sí |
| Ninguna Skill dominada ni `tensorflow`, `pytorch`, `sas`, `hadoop`, `deep learning` en el top 10. | sí |
| `docker` < `kubernetes`, `typescript` < `angular`, `object-oriented programming` < `unit testing`. | sí |

### P5. Data Scientist (con experiencia)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Data Scientist con experiencia que domina `python`, `sql`, `pandas` (avanzado) y `statistics` (intermedio), con interés en "deep learning".

- Role: Data Scientist; experience_level: `experienced`
- Skills conocidas (Mastery level): python (advanced), sql (advanced), statistics (intermediate), pandas (advanced)
- Intereses: deep learning; `cold_start`: False

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | data visualization | 24.8 | 2 | 0.62 |
| 2 | machine learning | 43.0 | 4 | 0.63 |
| 3 | r | 29.6 | 3 | 0.65 |
| 4 | tableau | 19.1 | 2 | 0.48 |
| 5 | agile | 10.6 | 1 | 0.32 |
| 6 | aws | 22.1 | 3 | 0.20 |
| 7 | data mining | 13.2 | 3 | 0.62 |
| 8 | java | 15.2 | 3 | 0.17 |
| 9 | azure | 14.9 | 3 | 0.17 |
| 10 | git | 10.0 | 2 | 0.12 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| `machine learning` en el top 5 (sus dos Prerequisites dominados). | sí |
| Orden de Prerequisites: `machine learning` < `deep learning` < `tensorflow`/`pytorch`; `machine learning` < `scikit-learn`. | sí |
| El interés sube `deep learning` respecto a no declararlo. | sí |
| (Expectativa original, no cumplida) `deep learning` en el top 15. | NO |
| `c#`, `c++`, `angular`, `jira`, `vba` fuera del top 10. | sí |

### P6. Data Scientist (inicial)

> Rutas esperadas escritas por un agente: pendientes de revisión humana.

**Learner profile.** Data Scientist inicial que domina `python` y `sql` (intermedio).

- Role: Data Scientist; experience_level: `entry`
- Skills conocidas (Mastery level): python (intermediate), sql (intermediate)
- Intereses: ninguno; `cold_start`: False

**Learning path real (top 10)**

| # | Skill | Frequency (%) | Effort | Similitud |
|---|---|---|---|---|
| 1 | r | 37.8 | 3 | 0.66 |
| 2 | data visualization | 22.3 | 2 | 0.65 |
| 3 | agile | 9.9 | 1 | 0.35 |
| 4 | tableau | 17.1 | 2 | 0.54 |
| 5 | statistics | 15.4 | 3 | 0.69 |
| 6 | machine learning | 53.1 | 5 | 0.52 |
| 7 | aws | 17.8 | 3 | 0.25 |
| 8 | sas | 12.9 | 3 | 0.55 |
| 9 | excel | 9.2 | 2 | 0.37 |
| 10 | power bi | 13.0 | 3 | 0.54 |

**Propiedades esperadas y resultado**

| Propiedad | Cumple |
|---|---|
| `statistics` en el top 5 y antes de `machine learning`; `machine learning` en el top 10. | sí |
| (Expectativa original, no cumplida) `pandas` en el top 10. | NO |
| `tensorflow`, `pytorch`, `kubernetes`, `angular` fuera del top 10, y `machine learning` < `deep learning` < `tensorflow`. | sí |

### Discrepancias entre expectativa y resultado

1. **P4, `docker`/`node.js`/`rest api` fuera del top 10.** Esperado: al menos 3 de {typescript, node.js, react, docker, ci/cd, rest api} en el top 10. Real: solo `react` (7) y `typescript` (9) están en el top 10; `rest api` (11), `node.js` (13) y `docker` (14) quedan justo fuera. Explicación: la expectativa original era errónea. `docker` necesita `linux` (no dominada), así que su Effort es 4, y `node.js` y `rest api` tienen menos Frequency que `aws`, `c#` o `go`. Prueba corregida a "al menos 4 en el top 15 y react/typescript en el top 10".
2. **P5, `deep learning` en el puesto 34, no en el top 15.** Esperado: el interés "deep learning" lo sube al top 15. Real: sube respecto a no declarar el interés, pero queda en el puesto 34. Explicación: el multiplicador `(1 + similitud)` vale como máximo 2; con Frequency 6.9 % y Effort 6 (Difficulty 5 + `machine learning` faltante) la prioridad no compite con Skills frecuentes y baratas. Expectativa errónea; la prueba exige solo mejora relativa y que quede antes de `tensorflow`. Observación de diseño para el líder: un interés explícito pesa poco frente a la Frequency; es una decisión de la fórmula firmada, no un bug.
3. **P6, `pandas` en el puesto 28, no en el top 10.** Esperado: con `python` dominada su Effort es 3 y debería estar entre las primeras. Real: puesto 28 con Frequency 5.2 %. Explicación: en las Offers de Data Scientist `pandas` se menciona poco (la gente escribe "Python" sin citar la biblioteca), así que la Frequency es baja. Expectativa de dominio errónea frente a los datos. Es un posible sesgo de medición para la Parte 3 (Skills implícitas en otras) y se documenta, no se corrige.
4. Observación sin discrepancia formal: en P5 y P6 el Learning path abre con `data visualization`, `r`, `tableau` y `agile`, antes que Skills de machine learning; es coherente con la fórmula (Frequency / Effort) pero poco intuitivo para un Data Scientist. Lo mismo ocurre con `aws` y `java` en P5.

## Métricas de sesgo

### Qué se midió y con qué Learner profiles

La evaluación de sesgo responde otra pregunta: no si el sistema acierta, sino **qué le muestra a cada Learner y qué deja fuera**. Se mide sobre el sistema tal como se entrega (artefactos de producción de `catalog/`, con Frequency y co-ocurrencia de todas las Offers), no sobre las tablas de entrenamiento, porque lo que interesa es el comportamiento que verá un Learner real.

Se usan 516 Learner profiles por Role (grupo `all` en los CSV):

- **500 perfiles de Offers de prueba:** las 500 Offers muestreadas, cada una con **todas** sus Skills del Catalog como dominadas (aquí no se esconde ninguna, a diferencia de leave-one-skill-out). Representan mercado real.
- **16 perfiles sintéticos:** el perfil vacío (arranque en frío), las 5 Skills más frecuentes del Role de a una y sus 10 pares. Cubren perfiles muy cortos que las Offers casi no producen.

Los CSV traen también los grupos `offers` y `synthetic` por separado; las tablas de abajo usan `all` y K = 10 (los 10 primeros puestos de cada Learning path), salvo que se diga otra cosa. "Exposición" de una Skill es la fracción de los puestos del top K, sumados sobre todos los perfiles, que ocupa esa Skill. Las filas `GLOBAL` juntan los tres Roles.

### Concentración de la exposición

Pregunta: ¿pocas Skills acaparan los puestos del top? Si es así, un Learner nunca verá Skills de nicho aunque le convengan.

| Role | Top-5 Skills | Top-10 Skills | Gini | Entropía normalizada |
|---|---|---|---|---|
| Data Analyst | 0.436 | 0.763 | 0.798 | 0.661 |
| Software Engineer | 0.398 | 0.720 | 0.773 | 0.697 |
| Data Scientist | 0.405 | 0.737 | 0.777 | 0.693 |
| GLOBAL | 0.299 | 0.541 | 0.666 | 0.798 |

(`exposure_concentration.csv`, K = 10.) "Top-5" y "Top-10" son la fracción de los puestos que se llevan las 5 o las 10 Skills más expuestas de un total de 64. El **Gini** va de 0 (exposición pareja) a casi 1 (una sola Skill lo acapara todo); la **entropía normalizada** va de 0 (una sola Skill) a 1 (todas por igual).

**Lectura:** en un Role, 5 de las 64 Skills se llevan 4 de cada 10 puestos y 10 Skills se llevan 7 de cada 10. Con K = 5 es peor: las 10 Skills más expuestas ocupan el 97.5 %, 96.5 % y 93.3 % de los puestos en Data Analyst, Software Engineer y Data Scientist. Un Gini cercano a 0.8 indica una exposición muy desigual: la mayor parte del Catalog queda en la cola. La cifra global es más baja porque cada Role concentra Skills distintas.

### Cobertura del Catalog

Pregunta: ¿cuántas Skills del Catalog llega a mostrar el sistema en el top K?

| Role | Skills mostradas, K = 5 | Cobertura K = 5 | Skills mostradas, K = 10 | Cobertura K = 10 |
|---|---|---|---|---|
| Data Analyst | 17 | 26.6 % | 22 | 34.4 % |
| Software Engineer | 18 | 28.1 % | 28 | 43.8 % |
| Data Scientist | 20 | 31.3 % | 28 | 43.8 % |
| GLOBAL | 35 | 54.7 % | 48 | 75.0 % |

(`coverage.csv`.) Cada Role muestra solo entre el 34 % y el 44 % del Catalog con K = 10, aun con 516 perfiles distintos. Parte de esto es esperable (un Software Engineer no necesita `tableau`), pero el total global dice más: **16 de las 64 Skills no aparecen en ningún top 10 de ningún Role** (`never_recommended.csv`, fila `GLOBAL`):

`a/b testing`, `airflow`, `algorithms`, `data structures`, `deep learning`, `hadoop`, `kafka`, `looker`, `microservices`, `natural language processing`, `numpy`, `object-oriented programming`, `pytorch`, `scikit-learn`, `tensorflow`, `vba`.

En Data Scientist, por ejemplo, `deep learning`, `pytorch`, `tensorflow`, `scikit-learn` y `natural language processing` nunca llegan al top 10. Si el Catalog tiene una Skill, pero ningún Learner la ve jamás, para efectos prácticos esa Skill no está en el sistema. (Por Role, `never_recommended.csv` lista 42, 36 y 36 Skills que no se muestran en Data Analyst, Software Engineer y Data Scientist; muchas son ajenas al Role.)

### Exposición por categoría

Pregunta: ¿alguna categoría del Catalog recibe menos exposición de la que tiene en el Catalog?

| Categoría | Skills en el Catalog | Peso en el Catalog | Exposición Data Analyst | Exposición Software Engineer | Exposición Data Scientist |
|---|---|---|---|---|---|
| machine learning | 6 | 9.4 % | 1.1 % | 0.0 % | 4.7 % |
| análisis de datos | 8 | 12.5 % | 30.4 % | 0.0 % | 16.2 % |
| visualización | 4 | 6.3 % | 19.6 % | 0.0 % | 17.7 % |
| ingeniería de datos | 9 | 14.1 % | 9.0 % | 0.0 % | 6.0 % |
| programación | 10 | 15.6 % | 15.2 % | 32.3 % | 17.6 % |
| herramientas | 3 | 4.7 % | 9.4 % | 24.1 % | 8.3 % |
| nube | 3 | 4.7 % | 0.1 % | 9.5 % | 17.0 % |
| bases de datos | 6 | 9.4 % | 5.2 % | 8.6 % | 3.7 % |
| ingeniería de software | 6 | 9.4 % | 8.6 % | 6.6 % | 8.8 % |
| desarrollo web | 6 | 9.4 % | 1.4 % | 16.3 % | 0.0 % |
| DevOps | 3 | 4.7 % | 0.0 % | 2.7 % | 0.0 % |

(`exposure_by_category.csv`, K = 10, grupo `all`; "Peso en el Catalog" es la fracción de las 64 Skills.) Que Software Engineer no vea Skills de análisis de datos es coherente con su Role. Lo llamativo es otra cosa: **machine learning pesa 9.4 % del Catalog y recibe solo 4.7 % de la exposición en Data Scientist (el Role donde debería importar más)**, 1.1 % en Data Analyst y 0 % en Software Engineer. Ahí el sistema favorece categorías de Skills frecuentes y baratas (programación, herramientas, visualización) sobre una categoría cuya Skill base (`machine learning`) tiene Effort alto y cuyas Skills derivadas (`deep learning`, `scikit-learn`, `tensorflow`, `pytorch`) cuestan aún más.

### Exposición por Difficulty

| Difficulty | Skills en el Catalog | Peso en el Catalog | Exposición Data Analyst | Exposición Software Engineer | Exposición Data Scientist |
|---|---|---|---|---|---|
| 1 | 3 | 4.7 % | 19.4 % | 23.2 % | 9.8 % |
| 2 | 13 | 20.3 % | 42.7 % | 30.5 % | 36.6 % |
| 3 | 32 | 50.0 % | 36.4 % | 44.7 % | 48.5 % |
| 4 | 14 | 21.9 % | 1.5 % | 1.7 % | 5.2 % |
| 5 | 2 | 3.1 % | 0.0 % | 0.0 % | 0.0 % |

(`exposure_by_difficulty.csv`, K = 10, grupo `all`.) Las Skills de Difficulty 4 y 5 son el 25 % del Catalog (16 de 64) y reciben entre 1.5 % y 5.2 % de la exposición (la Difficulty 5, nada). Las de Difficulty 1-2, que son el 25 %, reciben del 46 % al 62 %. Es el mismo efecto que se vio en leave-one-skill-out: el Effort protege al Learner de lo difícil, pero también le oculta lo avanzado, incluso cuando su perfil ya lo permitiría.

### Correlación entre exposición y Frequency

| Role | Spearman (K = 5) | Spearman (K = 10) |
|---|---|---|
| Data Analyst | 0.751 | 0.818 |
| Software Engineer | 0.723 | 0.855 |
| Data Scientist | 0.774 | 0.758 |

(`exposure_vs_frequency.csv`, grupo `all`.) Spearman compara el orden de las Skills por exposición con el orden por Frequency: 1 = mismo orden, 0 = sin relación. Valores de 0.72 a 0.86 significan que **lo que el sistema muestra es, en gran parte, lo que ya es frecuente en las Offers**. Es esperable (la Frequency está en la fórmula), pero implica que el sistema refuerza la Frequency en vez de equilibrarla: una Skill rara pero valiosa (por ejemplo, una que diferencia a un candidato) casi no tiene vía para aparecer.

### Nivel inicial frente a con experiencia

Se calculó el Learning path de cada perfil con `experience_level` experienced y con entry (complemento de nivel inicial, `docs/entry-level-complement.md`) y se compararon.

| Role | Jaccard@5 | Jaccard@10 | Kendall tau | Spearman |
|---|---|---|---|---|
| Data Analyst | 0.844 | 0.746 | 0.828 | 0.950 |
| Software Engineer | 0.743 | 0.817 | 0.893 | 0.975 |
| Data Scientist | 0.836 | 0.749 | 0.863 | 0.966 |

(`entry_vs_experienced.csv`, grupo `all`.) Jaccard@K es el solapamiento de los conjuntos de las K primeras Skills (1 = idénticos; 0.75 equivale a que de 10 Skills comparten unas 8.6). Kendall tau y Spearman comparan el orden completo del Learning path (1 = mismo orden). Con valores de 0.75 a 0.82 en Jaccard@10 y de 0.83 a 0.98 en tau y Spearman, **los Learning paths para nivel inicial y con experiencia son muy parecidos**: el complemento de nivel inicial cambia poco lo que se recomienda.

Skills que más suben y bajan en exposición (K = 10) al pasar a nivel inicial (`entry_vs_experienced_shifts.csv`):

| Role | Suben | Bajan |
|---|---|---|
| Data Analyst | `machine learning` (1.1 % a 7.3 %), `data cleaning` (+3.2 pts), `etl` (+2.4 pts) | `data modeling` (-6.4 pts), `data mining` (-4.7 pts), `html` (-1.4 pts) |
| Software Engineer | `c++` (1.3 % a 7.0 %), `css` (+1.7 pts), `azure` (+1.2 pts) | `go` (-3.8 pts), `rest api` (-3.3 pts), `jira` (-1.0 pt) |
| Data Scientist | `sas` (0.1 % a 8.0 %), `excel` (+2.4 pts), `power bi` (+2.2 pts) | `azure` (-4.7 pts), `java` (-3.0 pts), `etl` (-1.5 pts) |

**Cuidado con la subida de `sas` en Data Scientist inicial.** Su Frequency base es 6.02 % (261 de 4.336 Offers) y la de nivel inicial 27.66 % (13 de 47 Offers de arshkon, detectada por texto, no por `job_skills`); con n = 47 y peso w = 0.32 la mezcla la sube mucho. Con una muestra tan pequeña y un detector de texto puede ser ruido o una plantilla repetida, no una diferencia real entre niveles. Lo mismo se señaló en el ticket 07 para `machine learning` en Data Analyst inicial (22.5 %, 18 de 80), que es una de las subidas de la tabla.

## Limitaciones

- **Offers de LinkedIn, en inglés y sobre todo de Estados Unidos (79,8 %; el resto, de Reino Unido, Canadá y Australia, según `search_country`).** Todo lo que el sistema "sabe" del mercado viene de esas Offers. No representa la demanda en otros países ni en español.
- **El Role es el dataset de origen.** Las tres carpetas de `datos/` no son Roles puros: una Offer de Data Analyst puede pedir `machine learning` y una de Software Engineer, `sql`.
- **Las Offers dicen qué piden, no qué es útil aprender.** Que una Skill aparezca mucho no prueba que aprenderla primero sea lo mejor para un Learner.
- **El Learner simulado no es un Learner real.** Es la Offer menos una Skill: todas las Skills en Mastery level intermedio, sin intereses, siempre "con experiencia". Un Learner real tiene huecos, niveles distintos y metas.
- **Muestra de nivel inicial pequeña:** 80, 216 y 47 Offers de arshkon (Data Analyst, Software Engineer, Data Scientist), detectadas por texto.
- **Catalog, Difficulty y Prerequisites son juicio experto**, no medidos. Si un valor está mal, el Effort y todo lo derivado lo arrastra.
- **`job_skills` es ruidoso.** Por ejemplo, `pandas` tiene Frequency 7.63 % en Data Scientist (`catalog/frequency_by_role.csv`) y 5.2 % en la mezcla de nivel inicial del perfil P6: probablemente hay subregistro, porque en las Offers se escribe "Python" sin citar la biblioteca (`docs/entry-level-complement.md` documenta otras desviaciones entre texto y `job_skills`).
- **Un único Catalog de 64 Skills.** La similitud y las métricas de sesgo se calculan sobre él; con otro Catalog los números cambiarían.
- **Los pesos de la similitud no se ajustaron con datos** (`docs/similarity.md`); la mejora modesta sobre la fórmula sin similitud es la que dan esos pesos tal como se fijaron.
- **Los Learning paths esperados de los Learner profiles de prueba los escribió un agente** y están pendientes de revisión humana.
- **La evaluación offline no mide aprendizaje.** Ver la nota para 3.1.

## Evidencia para la Parte 3

Hallazgos que sustentan cada sesgo, con su cifra y archivo de origen.

| Sesgo | Evidencia | Archivo |
|---|---|---|
| **Sesgo hacia lo frecuente (Frequency).** El sistema refuerza lo que ya es frecuente y deja la cola larga sin exposición. | Spearman exposición-Frequency de 0.76 a 0.85 (K = 10); las 10 Skills más expuestas ocupan 93-98 % de los puestos con K = 5 y 72-76 % con K = 10; Gini 0.77-0.80. | `exposure_vs_frequency.csv`, `exposure_concentration.csv` |
| **Skills que nadie ve.** | Cobertura por Role de 34-44 % con K = 10; 16 Skills no aparecen en ningún Role (`deep learning`, `scikit-learn`, `pytorch`, `tensorflow`, `airflow`, `numpy`...). | `coverage.csv`, `never_recommended.csv` |
| **Sesgo de accesibilidad contra Skills avanzadas.** El Effort castiga las Skills difíciles. | Difficulty 4-5 es el 25 % del Catalog y recibe 1.5-5.2 % de la exposición; hit@10 de Difficulty 4 es 0.223 (línea base 0.451) y de Difficulty 5 es 0.000 (0.222); machine learning recibe 4.7 % de la exposición en Data Scientist frente a 9.4 % del Catalog. | `exposure_by_difficulty.csv`, `loo_by_difficulty.csv`, `exposure_by_category.csv` |
| **Sesgo geográfico y de idioma.** | El 79,8 % de las Offers son de EE. UU. y el resto de Reino Unido, Canadá y Australia (`search_country`); todas en inglés (limitación de los datos; no hay medida propia). | descripción de los datasets (`datos/README.md`) |
| **Roles no puros.** | El Role es el dataset de origen; por ejemplo, `machine learning` aparece en 5.65 % de las Offers de Data Analyst y en 22.5 % de las de nivel inicial. | `catalog/frequency_by_role.csv`, `catalog/frequency_entry_by_role.csv` |
| **Poca evidencia de nivel inicial.** | 80, 216 y 47 Offers; Jaccard@10 de 0.75-0.82 entre nivel inicial y con experiencia (el complemento cambia poco); `sas` sube de 0.1 % a 8.0 % en Data Scientist inicial por 13 de 47 Offers. | `entry_vs_experienced.csv`, `entry_vs_experienced_shifts.csv` |
| **Juicio experto.** | Catalog (64 Skills), Difficulty y Prerequisites los definió una persona y el Effort depende de ellos; no hay una medida propia de cuánto error tienen. El efecto del Effort se ve en la tabla por Difficulty. | `loo_by_difficulty.csv` |
| **Ruido de medición.** | `pandas` con Frequency 7.63 % en Data Scientist; en el perfil P6 queda en el puesto 28 (ver Personas). | `catalog/frequency_by_role.csv`, sección Personas |

### Nota para 3.1: qué mide y qué no mide la evaluación

**Mide:** si, dado lo que un Learner simulado ya sabe, el sistema coloca arriba una Skill que la Offer sí pedía (leave-one-skill-out), y cómo se reparte la exposición entre Skills, categorías y Difficulty.

**No mide:** si la Skill recomendada es la que más le conviene aprender; si el Learning path produce mejores resultados laborales; ni cómo reaccionan Learners reales. Una Skill que la Offer pide y que el sistema coloca en el puesto 30 es un "fallo" para esta prueba, pero puede ser exactamente lo que se quiso (aprender antes lo más accesible). Por eso conviene leer juntas la tabla por Difficulty y la de exposición: **la distancia entre la línea base de Frequency pura y el sistema completo no es un error, es el costo de priorizar accesibilidad**. Para saber si ese costo vale la pena se necesitaría una prueba con Learners reales, que está fuera del alcance de este taller.
