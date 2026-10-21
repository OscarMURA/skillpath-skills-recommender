# Similitud entre Skills

Este documento explica, para quien empieza con sistemas recomendadores, cómo SkillPath decide que una Skill se parece a lo que el Learner ya sabe o le interesa. Sirve de base para el punto 2.3 del taller (criterio de similitud claro). La implementación está en `skillpath/similarity.py` y `skillpath/cooccurrence.py`; es determinista y no usa LLM (ADR 0003). Todos los números de este documento salen de ejecuciones reales (Role Data Scientist salvo que se diga otra cosa).

## Idea en una frase

Cada Skill del Catalog se convierte en un texto corto; dos Skills son parecidas si sus textos comparten palabras importantes. Un Learner se resume con el mismo tipo de vector (su "ancla"), y las Skills candidatas más parecidas al ancla suben en el Learning path.

## Cómo se representa cada Skill

Para cada Skill se arma un documento con estas piezas:

| Pieza | Cuántas veces entra | Para qué |
|---|---|---|
| Su propio nombre como una sola palabra (`machine learning` pasa a `machine_learning`) | 3 | Que otras Skills que la mencionan se le parezcan. |
| Su categoría (`cat_programación`) | 2 | Señal gruesa de "mismo tipo de Skill". |
| La descripción del Catalog, sin palabras vacías en español (lista corta y explícita) | 1 por palabra | Qué es la Skill. |
| Skills del Catalog mencionadas en la descripción (por ejemplo "Python" en la de `pandas`) | 2 copias extra del nombre | Es una relación escrita por quien curó el Catalog. |
| Sus 8 Skills más cercanas por co-ocurrencia en las Offers del Role | de 1 a 4, proporcional a la cercanía (`max(1, round(4 × cercanía / mejor cercanía))`) | Qué Skills pide el mercado junto con ella. |

Los nombres de varias palabras se convierten en una sola palabra (`machine_learning`) para que `machine` y `learning` no se separen y se confundan con otras palabras. `c++`, `c#`, `.net`, `node.js` y `ci/cd` se conservan tal cual.

### Co-ocurrencia

`catalog/cooccurrence.csv` cuenta, por Role, en cuántas Offers aparecen juntas dos Skills del Catalog (solo las tres bases de asaniczka). La cercanía es `offers_together / sqrt(offers_a × offers_b)`, entre 0 y 1. Por ejemplo, en Data Scientist `python` y `sql` tienen cercanía 0.738.

- **Por Role y no global.** La cercanía depende del mercado de cada Role, y el Learner siempre tiene un Role objetivo. Costo: 3.906 filas, unos 163 KB, que es pequeño. Se genera con `.venv/bin/python -m skillpath.build_cooccurrence` (misma salida byte a byte al regenerar).
- **Ochiai en vez de Jaccard.** Con Jaccard, `pandas` (7.6 % de las Offers de Data Scientist) casi no se parecía a `python` (muy frecuente), porque el denominador crece con la Skill frecuente. Ochiai es el coseno entre las dos columnas "aparece en la Offer i" y trata mejor ese caso.
- Se descartan pares con menos de 5 Offers juntas para que el archivo sea pequeño y no pesen coincidencias casuales.

## Qué mide el coseno

TF-IDF da a cada palabra un peso: sube si la palabra aparece mucho en el documento de la Skill (TF) y baja si aparece en casi todos los documentos (IDF; `datos` pesa menos que `pandas`). Cada documento queda como un vector de pesos (64 documentos y 153 palabras en Data Scientist; solo se conservan palabras que están en al menos dos documentos, porque una palabra única no puede acercar nada). La **similitud del coseno** es el coseno del ángulo entre dos vectores: 1 si apuntan igual (mismas palabras con pesos proporcionales), 0 si no comparten ninguna. Como los pesos nunca son negativos, el resultado queda en [0, 1].

El modelo (`TfidfVectorizer`) se ajusta solo con los 64 documentos del Catalog, sin datos externos ni azar. La similitud no usa embeddings ni LLM (ADR 0003).

## Ejemplo real: las 5 Skills más cercanas

Data Scientist. "Palabras compartidas" son las que más aportan al coseno entre las dos Skills.

**`python`** (sus vecinos principales por cercanía son `sql` 0.738, `machine learning` 0.703, `r` 0.656, `aws` 0.498, `spark` 0.490):

| Skill | Coseno | Cercanía por co-ocurrencia | Palabras compartidas que más aportan |
|---|---|---|---|
| statistics | 0.70 | 0.408 | `machine_learning`, `r`, `data_visualization` |
| sql | 0.69 | 0.738 | `machine_learning`, `r`, `data_visualization` |
| r | 0.66 | 0.656 | `machine_learning`, `r`, `data_visualization` |
| a/b testing | 0.63 | 0.231 | `machine_learning`, `r`, `data_visualization` |
| data visualization | 0.56 | 0.464 | `machine_learning`, `r`, `data_visualization` |

**`sql`**:

| Skill | Coseno | Cercanía por co-ocurrencia | Palabras compartidas que más aportan |
|---|---|---|---|
| a/b testing | 0.69 | 0.260 | `data_visualization`, `r`, `tableau` |
| python | 0.69 | 0.738 | `machine_learning`, `r`, `data_visualization` |
| data visualization | 0.63 | 0.509 | `tableau`, `r`, `power_bi` |
| looker | 0.59 | 0.168 | `tableau`, `power_bi`, `data_visualization` |
| statistics | 0.57 | 0.372 | `machine_learning`, `r`, `data_visualization` |

**Cómo leerlo.** Dos Skills se parecen porque piden junto a ellas las mismas Skills (`python` y `sql` comparten vecinos como `machine learning`, `r` y `data visualization`), no solo porque co-ocurran entre sí. Por eso el coseno y la cercanía directa no coinciden: `a/b testing` tiene cercanía directa baja con `python` (0.231) pero un coseno alto (0.63) porque tiene los mismos vecinos. Efecto secundario honesto: las Skills muy frecuentes (`python`, `sql`, `r`, `machine learning`) aparecen como vecinas de casi todo y generan una similitud de fondo alta (0.3 a 0.7) entre Skills de datos. Las Skills de nicho se separan mejor: las más cercanas a `pandas` son `numpy` 0.79, `scikit-learn` 0.76, `pytorch` 0.60 y `tensorflow` 0.59, mientras que `python` y `pandas` solo llegan a 0.135.

## Cómo entra el Learner

La **ancla** del Learner es la suma de los vectores de sus elementos, cada uno multiplicado por un peso:

- **Skills conocidas**, según el Mastery level: básico 0.5, intermedio 0.75, avanzado 1.0. Quien domina más una Skill orienta más la recomendación; el básico cuenta menos porque esa Skill todavía es candidata. Son valores elegidos por simplicidad, no ajustados con datos.
- **Intereses**, peso 1.0 (declarar un interés es una señal explícita).

La similitud de cada candidata es el coseno entre su vector y el ancla, entre 0 y 1. Sin ancla vale 0 para todas y el resultado es idéntico al anterior (Frequency / Effort).

**Skill conocida en nivel básico.** Sigue siendo candidata. Para calcular su propia similitud se quita su vector del ancla; si no, parecería idéntica a sí misma (coseno 1) solo por declararla. Si es el único elemento del ancla su similitud es 0. Un interés que nombra a la candidata sí cuenta: es un deseo explícito (`tableau` como interés da similitud 1.0 a `tableau`).

### Intereses (texto libre)

Cada interés se resuelve en este orden:

1. **Es una Skill del Catalog** (tras minúsculas y alias, por ejemplo `Machine Learning`): se usa el vector de esa Skill.
2. **Es una categoría** (`visualización`, `DevOps`, `nube`...): se usa el promedio de los vectores de las Skills de la categoría.
3. **Otro texto** (`análisis`, `dashboards`): se transforma como palabras clave con el mismo vectorizador. Funciona para palabras que aparecen en las descripciones del Catalog.
4. **Si el vector sale en cero** (ninguna palabra conocida, o solo palabras vacías): el interés se ignora y se informa como no reconocido (`LearningPath.unrecognized_interests`); la app muestra un aviso. Un perfil con solo intereses no reconocidos da el mismo resultado que sin intereses (comprobado en las pruebas).

## Extensión de la prioridad

```
Prioridad = Frequency × (1 + similitud) / Effort
```

Detalle y ejemplo en `docs/priority-formula.md`, sección "Extensión con similitud (ticket 05)" (pendiente de aprobación humana). Ejemplo real, Data Scientist con `python` avanzado (Frequency en %):

| Skill | Frequency | Effort | Similitud | Prioridad antes | Prioridad después | Puesto antes → después |
|---|---|---|---|---|---|---|
| sql | 55.07 | 2 | 0.69 | 27.54 | 46.53 | 1 → 1 |
| data visualization | 24.79 | 2 | 0.56 | 12.39 | 19.39 | 2 → 2 |
| r | 29.59 | 3 | 0.66 | 9.86 | 16.37 | 4 → 3 |
| agile | 10.61 | 1 | 0.39 | 10.61 | 14.75 | 3 → 4 |
| tableau | 19.14 | 2 | 0.43 | 9.57 | 13.68 | 5 → 5 |

Otro ejemplo, Data Analyst sin Skills conocidas y con el interés `visualización`: `data visualization` pasa del puesto 4 al 3 (similitud 0.88) y `tableau` del 5 al 4 (0.91); `agile`, con similitud 0.08, baja del 3 al 6. Con el mismo perfil más un interés no reconocido (`zzz qqq`) el aviso aparece y el orden es el de siempre.

El efecto es moderado a propósito: la Frequency y el Effort siguen mandando, y la similitud mueve sobre todo a las Skills con Frequency y Effort parecidos.

## Explicaciones

Cada elemento del Learning path trae un texto en español con: la Frequency en el Role, hasta tres elementos del perfil cercanos con su coseno (solo si superan 0.05) y los Prerequisites cubiertos o pendientes. Ejemplos reales:

- "Aparece en el 43.0% de las ofertas de Data Scientist; esfuerzo estimado 5. Se relaciona con lo que ya sabes: python (0.52). Conviene aprender antes: statistics."
- "Aparece en el 16.9% de las ofertas de Data Analyst; esfuerzo estimado 2. Se relaciona con tus intereses: visualización (0.91)."
- Sin perfil: "Aparece en el 33.5% de las ofertas de Data Analyst; esfuerzo estimado 2. Sin habilidades ni intereses reconocidos, el orden usa solo frecuencia y esfuerzo."

## Alternativas descartadas

- **Solo co-ocurrencia (sin texto).** Se parecería a un filtrado por "quien pide X pide Y": trata igual a Skills sustitutas que rara vez se piden juntas (por ejemplo dos lenguajes alternativos) y cubre mal las Skills con pocas Offers (razonamiento, no medido). El texto aporta categoría y descripción.
- **Embeddings o LLM.** Podrían captar mejor el significado, pero no son deterministas ni se explican con claridad en el taller (ADR 0003).
- **Jaccard sobre los Prerequisites.** Los Prerequisites ya entran en el Effort y el ajuste topológico; usarlos también como similitud contaría dos veces la misma información.
- **Jaccard como cercanía de co-ocurrencia.** Probado: `pandas` casi no se acercaba a `python` (ver arriba).
- **Ponderación solo multiplicativa (`Frequency × sim / Effort`).** Descartada por razonamiento, no medida: anularía la prioridad de toda Skill sin relación.

## Limitaciones

- La co-ocurrencia refleja el mercado de LinkedIn en EE. UU., en inglés, y los datos de asaniczka (ver `catalog/README.md`).
- Los documentos son cortos (64 Skills, 152 a 153 palabras según el Role): el IDF es muy ruidoso y un cambio en una descripción mueve resultados.
- Las descripciones están en español y los nombres de Skill en inglés; un interés en inglés que no sea una Skill (`dashboard`) no se reconoce si no aparece en las descripciones.
- Las Skills muy frecuentes actúan como "hubs" y elevan la similitud de fondo entre Skills de datos (ver tablas): la similitud ordena, pero no demuestra relación causal.
- Los pesos (Mastery level, repeticiones, 8 vecinos, umbral 0.05) son decisiones razonables, no valores ajustados con datos.
- Por Role: un Role sin filas en `cooccurrence.csv` usaría solo texto y categoría.
- La evaluación (ticket 08) debe medir si la similitud mejora el Learning path; aquí solo se comprueba su comportamiento.
