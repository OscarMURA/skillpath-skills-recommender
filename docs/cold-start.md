# Arranque en frío (cold start)

Este documento responde al punto 2.1 del taller. Está escrito para quien apenas empieza con sistemas recomendadores. La lógica está en `skillpath/recommender.py` (`recommend`), `skillpath/models.py` (`LearningPath.most_frequent`, `LearningPath.cold_start`) y el formulario en `app/streamlit_app.py`. Todo es determinista y sin LLM (ADR 0003). Las cifras de abajo salen de ejecutar el código, no de estimaciones.

## Qué es el arranque en frío

Un recomendador aprende de lo que sabe: lo que una persona ya hizo, lo que otras hicieron. El **arranque en frío** es el momento en que todavía no sabe nada. Ejemplo sencillo: una librería en línea recomienda libros según los que compraste antes; el primer día que entras no hay compras, y la pregunta es qué mostrar. Hay dos casos:

- **Persona nueva:** no hay historial de quien recibe la recomendación.
- **Ítem nuevo:** llega un libro que nadie ha comprado, y por eso un recomendador basado en compras jamás lo mostraría.

## En SkillPath

**Learner nuevo: sí aplica.** Un Learner que llega por primera vez no ha dicho su Role, ni qué Skills domina, ni qué le interesa. Hasta que lo diga, el Learner profile está vacío y la recomendación no puede personalizarse.

**Skill nueva: casi no aplica.** Una Skill que se agrega al Catalog ya trae descripción, categoría, Difficulty y Prerequisites, y su Frequency sale de las Offers, no de lo que hagan los Learners. Con eso se puede calcular su Effort, su similitud con otras Skills y, en cuanto aparezca en las Offers, su Frequency.

**Por qué el problema es menor.** SkillPath no guarda ni usa historial de interacciones de Learners (no hay "los que aprendieron X también aprendieron Y"; no es filtrado colaborativo). Las señales vienen del mercado (Frequency, co-ocurrencia en las Offers) y de atributos curados del Catalog. Un Learner o una Skill nuevos no dejan ningún hueco en esos datos; solo el Learner profile tiene que irse llenando.

## Estrategias y cómo contribuye cada una

### 1. Formulario inicial corto

Pide, en este orden: Role (único obligatorio); Skills conocidas con su Mastery level; intereses opcionales. Para que marcar sea rápido, la app muestra como casillas las 8 Skills más frecuentes del Role (se marcan con nivel intermedio, ajustable). Contribución: con una sola Skill marcada el perfil deja de estar vacío (`cold_start` pasa a False) y la similitud empieza a personalizar el orden. Existe también «Empezar sin datos», que ignora Skills e intereses y muestra el resultado del perfil vacío, de modo que nunca aparece una pantalla vacía.

### 2. Caída al perfil vacío: dos vistas del mismo resultado

Con perfil vacío (`cold_start` True: ninguna Skill conocida del Catalog con Mastery level válido y ningún interés reconocido) `recommend` entrega todo en una sola llamada:

- **Learning path** por la fórmula firmada (`docs/priority-formula.md`): prioridad = Frequency / Effort, con desempates y ajuste por Prerequisites. No se modificó.
- **Las más frecuentes en las Offers del Role** (`path.most_frequent(10)`): Skills ordenadas por Frequency pura, desempate por nombre, sin las de Frequency 0.

Por qué mostrar ambas: la fórmula respeta Prerequisites y Effort (empieza por lo que es útil y alcanzable), pero su orden no es el de Frequency pura y cuesta explicarlo en una frase; la lista por Frequency cumple de forma directa "las Skills de mayor Frequency del Role" y se entiende al instante, pero ignora cuánto cuesta aprender cada Skill. Diferencias reales con perfil vacío (Skill, Frequency %, Effort):

| Role | Top 5 del Learning path (fórmula) | Top 5 más frecuentes (Frequency pura) |
|---|---|---|
| Data Analyst | sql 33.51 (2), excel 26.29 (2), agile 11.03 (1), data visualization 18.06 (2), tableau 16.93 (2) | sql 33.51 (2), excel 26.29 (2), power bi 18.42 (3), data visualization 18.06 (2), tableau 16.93 (2) |
| Software Engineer | agile 33.86 (1), python 37.90 (2), html 14.05 (1), sql 23.96 (2), java 33.88 (3) | python 37.90 (2), java 33.88 (3), agile 33.86 (1), javascript 28.75 (4), aws 27.83 (3) |
| Data Scientist | python 65.04 (2), sql 55.07 (2), data visualization 24.79 (2), agile 10.61 (1), r 29.59 (3) | python 65.04 (2), sql 55.07 (2), machine learning 42.99 (6), r 29.59 (3), data visualization 24.79 (2) |

Lectura: en Data Scientist, `machine learning` es la tercera más frecuente (42.99 %) pero queda en el puesto 9 del Learning path, porque su Effort es 6 (Difficulty más Prerequisites pendientes). En Software Engineer, `agile` (Effort 1) encabeza el Learning path aunque sea la tercera por Frequency, y `javascript` (Effort 4) baja al puesto 10. En ambos casos la fórmula antepone lo que se aprende rápido.

### 3. Atributos propios de cada Skill

- **Similitud** por descripción y categoría (`docs/similarity.md`): una Skill nueva se relaciona con otras sin necesitar historial.
- **Effort** por Difficulty y Prerequisites, que están en el Catalog.
- **Frequency** recalculable: no depende de Learners. Basta volver a ejecutar `python -m skillpath.build_frequency` sobre las Offers para que una Skill nueva obtenga la suya (la función pura `compute_frequency` está probada con Offers de juguete).

## Ejemplo real: una Skill nueva

Se agrega al Catalog una Skill ficticia `sqlmesh` (categoría `bases de datos`, Difficulty 2, Prerequisite `sql`, descripción "Herramienta para la transformación de datos con sql dentro del almacén de datos, con pruebas y documentación."), sin Frequency y sin co-ocurrencia. Se eligió un nombre que no está en las Offers analizadas (`dbt` sí aparece en las de Data Scientist).

```python
import dataclasses
from skillpath import LearnerProfile, catalog, recommend
from skillpath.similarity import get_model

new = dataclasses.replace(
    catalog.CATALOG["sql"], name="sqlmesh", difficulty=2, prerequisites=("sql",),
    description="Herramienta para la transformación de datos con sql dentro del almacén de datos, con pruebas y documentación.",
)
catalog.CATALOG = {**catalog.CATALOG, "sqlmesh": new}   # solo para la demostración
get_model.cache_clear()
path = recommend(LearnerProfile("Data Analyst", interests=["sqlmesh"]))
```

Resultados (Data Analyst):

| Perfil | Puesto | Frequency | Effort | Similitud |
|---|---|---|---|---|
| vacío | 65 de 65 (sql: 1) | 0.0 | 3 (2 + `sql` pendiente) | 0.00 |
| interés `sqlmesh` | 65 de 65 | 0.0 | 3 | 1.00 |
| interés `bases de datos` | 65 de 65 | 0.0 | 3 | 0.53 |
| `sql` intermedio | 64 de 64 | 0.0 | 2 | 0.33 |

Explicación con perfil vacío: "No aparece en las ofertas de Data Analyst analizadas. Frequency 0 %, así que va al final de la ruta; esfuerzo estimado 3. Sin habilidades ni intereses reconocidos, el orden usa solo frecuencia y esfuerzo. Conviene aprender antes: sql."
Con `sql` intermedio: "... esfuerzo estimado 2. Se relaciona con lo que ya sabes: sql (0.33). Ya dominas sus prerrequisitos: sql."

La Skill se recomienda sin fallar, queda después de `sql`, su Effort baja cuando el Learner domina `sql` y un interés que la nombra (o nombra su categoría) se reconoce.

## Limitaciones

- Un perfil vacío ve lo mismo que cualquier otro Learner vacío del Role: no hay personalización hasta que se complete el formulario.
- Una Skill nueva sin Frequency queda al final hasta recalcular la Frequency. La similitud no la sube porque multiplica a una Frequency 0 (ver `docs/priority-formula.md`: Prioridad = Frequency × (1 + similitud) / Effort). Es coherente con la fórmula firmada, pero oculta una Skill que quizá el mercado ya pide.
- El formulario depende de que el Learner declare bien sus niveles; una Skill declarada avanzada sin serlo recorta Prerequisites y Effort.
- Las sugerencias por Role refuerzan lo que ya es frecuente y pueden dejar fuera nichos.
- "Las más frecuentes" excluye Skills con Frequency 0 y, en un perfil con Skills dominadas, solo cuenta las que faltan.
- No se midió cuánto mejora la experiencia con el formulario; es una decisión de diseño, no un resultado evaluado.

Ver también: `docs/priority-formula.md` y `docs/similarity.md`.

Ver también: `docs/entry-level-complement.md` (Frequency para Learners de nivel inicial).
