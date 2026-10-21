# Complemento de nivel inicial (arshkon)

Este documento explica cómo SkillPath atiende a estudiantes y recién graduados usando Offers de nivel inicial de arshkon. Está escrito para quien apenas empieza con sistemas recomendadores y sirve de base para la Parte 3 (sesgo de selección). La decisión de fondo está en `docs/adr/0002-arshkon-as-entry-level-complement.md`; los datos están en `catalog/frequency_entry_by_role.csv` y `catalog/detection_calibration.csv` (ver `catalog/README.md`); la mezcla vive en `skillpath/recommender.py`. Todo es determinista y sin LLM (ADR 0003). Las cifras salen de ejecutar el código.

## Por qué hace falta un complemento

La Frequency base sale de asaniczka, que solo tiene Offers de nivel Associate y Mid senior. Un estudiante o recién graduado busca otro tipo de Offers, y lo que se pide a ese nivel puede ser distinto. arshkon sí trae Offers de nivel Entry level e Internship, pero sus "habilidades" son 35 categorías amplias (ACCT, MRKT...) que no sirven para Skills técnicas del Catalog. Por eso arshkon se usa solo como complemento: se buscan las Skills del Catalog en el texto de la descripción y asaniczka sigue siendo la base.

## Cómo se define el nivel inicial

Nivel inicial = **Entry level + Internship**. **Associate no entra**: la base ya está hecha de Offers Associate y Mid senior, y meterlo en el complemento diluiría el contraste. El Role se decide por el título (`data analyst`, `data scientist`, `software engineer|developer|development engineer`); un título que coincide con más de un Role se descarta.

Offers de arshkon por nivel, antes -> después de deduplicar:

| Role | Entry level | Internship | Associate (no usado) | Nivel inicial usado |
|---|---|---|---|---|
| Data Analyst | 116 -> 78 | 2 -> 2 | 39 -> 37 | 118 -> 80 |
| Software Engineer | 217 -> 208 | 8 -> 8 | 84 -> 76 | 225 -> 216 |
| Data Scientist | 56 -> 46 | 1 -> 1 | 13 -> 11 | 57 -> 47 |

Las cifras por nivel deduplican dentro de cada nivel; la última columna deduplica sobre Entry level e Internship juntos.

## Deduplicación

arshkon repite Offers: por ejemplo, "Online Data Analyst" aparece 20 veces con el mismo texto. Sin deduplicar, una sola plantilla inflaría la Frequency de sus Skills. Se deduplica por Role con el texto exacto de `description` (sin espacios sobrantes ni diferencia de mayúsculas): cada texto cuenta una vez. Así Data Analyst pasa de 118 a 80 Offers.

## Cómo detecta Skills el diccionario

`skillpath/skill_detection.py` arma una expresión regular por Skill. Reglas:

- **Nombres y alias.** Cuenta el nombre de la Skill, sus alias de `catalog/aliases.csv` y algunos sinónimos de texto. Ejemplos: "scikit-learn" también por "sklearn"; "node.js" por "nodejs"; "postgresql" por "postgres"; "a/b testing" por "split testing".
- **Límites de palabra.** Un término no puede ir pegado a otras letras o símbolos: "javascript" no cuenta como `java`, y "MySQL", "PostgreSQL" y "NoSQL" no cuentan como `sql`. Los símbolos funcionan: `c++`, `c#`, `ci/cd`.
- **Ambiguos con reglas propias.** `r` solo cuenta como la letra mayúscula en contextos claros ("RStudio", "experience in R or Python", "Python, R") y nunca en "R&D". `go` solo como "Golang", "Go programming" o "Go" en una lista de lenguajes, no el verbo. `excel` es la herramienta ("Microsoft Excel"), no el verbo ("excel in"). `spark` es Apache Spark o PySpark, no la palabra; `react` solo con mayúscula; `rest api` no cuenta la palabra "rest" sola.
- **Acrónimos sensibles a mayúsculas:** "ML", "NLP", "OOP" y "JS" solo cuentan tal cual.

## Validación contra asaniczka

Se aplica el mismo detector al texto (`job_summary`) de todas las Offers de asaniczka que tienen texto y `job_skills`, y se compara, sobre las mismas Offers, con la Frequency que dan sus `job_skills`. Esa comparación está en `catalog/detection_calibration.csv`.

Mayores desvíos entre texto y `job_skills` (puntos de Frequency, `diff` = texto menos `job_skills`):

| Role | Skill | Texto (%) | `job_skills` (%) | diff | Estado |
|---|---|---|---|---|---|
| Data Scientist | algorithms | 21.52 | 3.44 | 18.08 | excluida |
| Data Scientist | statistics | 29.40 | 15.45 | 13.95 | excluida |
| Data Scientist | big data | 17.71 | 7.15 | 10.56 | excluida |
| Data Scientist | etl | 20.69 | 11.60 | 9.09 | fiable |
| Software Engineer | algorithms | 12.21 | 4.26 | 7.95 | excluida |
| Data Scientist | agile | 18.36 | 10.61 | 7.75 | fiable |
| Software Engineer | microservices | 16.27 | 9.88 | 6.39 | excluida |

**Regla:** una Skill es no fiable si en algún Role el desvío supera 10 puntos o, donde `job_skills` da al menos 2 %, el cociente texto/`job_skills` queda fuera de [0.5, 2.0]. **Excluidas hoy:** `algorithms`, `big data`, `microservices` y `statistics`. Para ellas, el Learner de nivel inicial recibe solo la Frequency base.

Aviso: `job_skills` también tiene ruido. Casi todos los desvíos son del texto *por encima* de `job_skills`, y los falsos positivos revisados eran menciones reales, es decir, `job_skills` omite Skills que el texto sí menciona. No sabemos qué fuente se acerca más a la verdad; por eso se excluyen por prudencia en vez de decidir cuál tiene razón. Entre las Skills fiables, el mayor desvío absoluto por Role es 6.21 puntos (Data Analyst), 9.09 (Data Scientist) y 7.30 (Software Engineer).

## Cómo se mezcla con la Frequency base

La fórmula de prioridad **no cambia** (ver `docs/priority-formula.md`); solo cambia de dónde sale la Frequency para un Learner de nivel inicial:

```
w         = n / (n + K)            K = 100, n = Offers de nivel inicial del Role
Frequency = w × entrada + (1 − w) × base
```

`K = 100` equivale a decir "la Frequency base pesa como 100 Offers ficticias": con pocas Offers de nivel inicial manda la base, y con más manda cada vez más el nivel inicial. Reglas:

- Si `n < 30` (`MIN_ENTRY_OFFERS`), no se mezcla (w = 0) y la explicación lo dice.
- Una Skill ausente de la tabla de nivel inicial (las 4 excluidas) usa solo la base.
- Para el Learner con experiencia (valor por defecto) nada cambia.
- `most_frequent` y las sugerencias de la app usan la misma Frequency mezclada.

## Tamaño de muestra y pesos por Role

| Role | n (Offers de nivel inicial) | w = n / (n + 100) |
|---|---|---|
| Data Analyst | 80 | 0.44 |
| Software Engineer | 216 | 0.68 |
| Data Scientist | 47 | 0.32 |

Las tres son muestras pequeñas; la app lo advierte al elegir "Inicial".

## Ejemplo real: top 5 con perfil vacío

Generado con `recommend(LearnerProfile(role, experience_level=...))` (Frequency en %):

| Role | # | Con experiencia | Inicial |
|---|---|---|---|
| Data Analyst | 1 | sql 33.51 | sql 38.06 |
| | 2 | excel 26.29 | excel 32.38 |
| | 3 | agile 11.03 | agile 11.68 |
| | 4 | data visualization 18.06 | python 22.14 |
| | 5 | tableau 16.93 | tableau 18.29 |
| Software Engineer | 1 | agile 33.86 | agile 35.40 |
| | 2 | python 37.90 | python 35.73 |
| | 3 | html 14.05 | html 17.11 |
| | 4 | sql 23.96 | java 42.05 |
| | 5 | java 33.88 | sql 23.41 |
| Data Scientist | 1 | python 65.04 | python 68.74 |
| | 2 | sql 55.07 | sql 56.51 |
| | 3 | data visualization 24.79 | r 37.82 |
| | 4 | agile 10.61 | data visualization 22.31 |
| | 5 | r 29.59 | agile 9.94 |

Lectura: en Data Analyst `python` sube al puesto 4 (de 16.86 % a 22.14 %); en Software Engineer `java` sube al 4 y `sql` baja al 5; en Data Scientist `r` sube al puesto 3. Ejemplo de explicación (Data Analyst, `sql`): "Aparece en el 38.1% de las ofertas de Data Analyst (mezcla: 44% de 80 ofertas de nivel inicial de arshkon, una muestra pequeña, y 56% de las ofertas base); esfuerzo estimado 2."

## Limitaciones

- **Muestra pequeña.** 47 a 216 Offers por Role; una Skill con pocas menciones se mueve mucho con una Offer más o menos. Por eso existe la mezcla y el mínimo de 30.
- **Texto frente a campo de Skills.** La base mide `job_skills` y el complemento mide menciones en el texto; no son la misma cosa, aunque la calibración intenta acotar la diferencia.
- **Offers de EE. UU. y en inglés.** El diccionario busca términos en inglés; no se probó con Offers de otros países o idiomas.
- **Role por título.** Una Offer cuyo título no contiene el nombre del Role (por ejemplo, un cargo equivalente con otro nombre) no se cuenta, y un título que menciona dos Roles se descarta.
- **Plantillas casi idénticas que sobreviven a la deduplicación exacta.** Por ejemplo, "Data Analyst (Korean)", "(Chinese)" y "(Japanese)" tienen texto casi igual, no idéntico, y mencionan "machine learning": esa Skill queda en 22.5 % en Data Analyst de nivel inicial (18 de 80 Offers), probablemente inflada por esas plantillas.
- **Parámetros de la mezcla.** K = 100 y el mínimo de 30 son decisiones de diseño, sin evaluación con Learners reales.

## Nota de sesgo de selección (para la Parte 3)

Las Offers de nivel inicial que vemos no son todas las que existen: son las que se publicaron en LinkedIn, en inglés, y que arshkon capturó. Las empresas que publican Offers de nivel inicial con texto largo y técnico no son representativas de todas; las plantillas repetidas de una sola empresa pesan más de lo que deberían aun tras deduplicar; y las Offers que piden pocas Skills técnicas o no mencionan herramientas casi no aparecen en la Frequency. Además, que una Skill aparezca en una Offer de nivel inicial no significa que sea requisito real para conseguir el puesto. Las Frequency de nivel inicial describen lo que *se publica*, no lo que *se contrata*.
