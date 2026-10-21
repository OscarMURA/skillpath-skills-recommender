# Fórmula de prioridad del Learning path

Este documento explica cómo SkillPath decide en qué orden recomienda las Skills. Está pensado para quien empieza con sistemas recomendadores: no hace falta saber nada previo, solo leer los términos de `GLOSSARY.md`. La implementación está en `skillpath/recommender.py` (función `recommend`) y es determinista: sin LLM y sin azar (ADR 0003).

## La idea en una frase

Una Skill debe subir en el Learning path si **aparece mucho en las Offers del Role** y **cuesta poco aprenderla para este Learner**. Por eso se divide la Frequency entre el Effort.

## Fórmula

Para una Skill `s` que el Learner aún no domina, con Role objetivo `r`:

```
Effort(s)    = Difficulty(s) + |Faltantes*(s)|
Prioridad(s) = Frequency(s, r) / Effort(s)
```

| Término | Qué es | De dónde sale |
|---|---|---|
| `Frequency(s, r)` | Porcentaje de las Offers del Role que mencionan la Skill. Es 0 si la Skill no aparece en el Role. | `catalog/frequency_by_role.csv` |
| `Difficulty(s)` | Complejidad intrínseca de la Skill, de 1 a 5. | `catalog/skills.csv` |
| `Faltantes*(s)` | Conjunto, sin duplicados, de **todos** los Prerequisites de `s` (directos y de los Prerequisites de sus Prerequisites, etc.) que el Learner todavía no domina. | grafo de Prerequisites de `skills.csv` + Learner profile |
| `Effort(s)` | Costo estimado para este Learner. Crece con la Difficulty y con cada Prerequisite pendiente. | calculado |
| `Prioridad(s)` | Frequency por unidad de Effort. Más alta = va antes. | calculado |

El Effort es **personal**: la misma Skill cuesta menos a quien ya domina sus bases. Por eso aparece el Learner profile en la fórmula.

### Orden final

1. **Orden por prioridad**, de mayor a menor.
2. **Desempate explícito** cuando dos Skills tienen la misma prioridad: gana la de mayor Frequency; si también empatan, gana el nombre alfabético ascendente. Así el resultado nunca depende del orden de inserción de ningún diccionario.
3. **Ajuste topológico estable.** El orden por prioridad puede poner una Skill antes de sus Prerequisites (por ejemplo, `tensorflow` con Frequency alta y `deep learning` con Frequency baja). El ajuste recorre la lista y va colocando, en cada paso, la Skill mejor ordenada cuyos Prerequisites directos pendientes **ya estén colocados**. Como esos Prerequisites ya cumplen lo mismo, por inducción toda Skill queda después de todos sus Faltantes*, también los transitivos. "Estable" significa que no se mueve nada que no haga falta mover. Si algún día hubiera un ciclo de Prerequisites (hoy las pruebas validan que no lo hay), el código no se cuelga: agrega el resto en el orden que ya tenía.

### Mastery level

- `intermediate` y `advanced`: la Skill está **dominada**. No se recomienda y no cuenta como faltante.
- `basic`: la Skill **no** está dominada. Sigue siendo candidata (se recomienda para profundizar) y cuenta como Prerequisite faltante para las Skills que la necesitan.

## Decisiones

### Faltantes transitivos, con recorrido detenido en Skills dominadas

Si `tensorflow` requiere `deep learning`, que requiere `machine learning`, que requiere `python` y `statistics`, aprender `tensorflow` desde cero implica cuatro Prerequisites pendientes, no uno. Contar solo los directos subestima las Skills profundas.

El recorrido del grafo **se detiene** al llegar a una Skill dominada: si el Learner domina `deep learning`, se asume que ya tiene sus bases y no se siguen contando `machine learning`, `python` ni `statistics`. Consecuencia concreta: si el Learner domina `deep learning` pero no `machine learning`, `tensorflow` no exige `machine learning` antes (Effort 4, sin faltantes). Es una suposición razonable (quien domina algo avanzado suele tener lo anterior) y es simple de explicar, pero puede ser optimista si el Learner declaró la Skill avanzada sin tener realmente la base.

### Nivel básico = faltante (y sigue como candidata)

Quien tiene `python` en nivel básico todavía no puede construir sobre esa base: necesita profundizarla antes de `pandas` o `machine learning`. Si `basic` se tratara como "cubierto", las Skills dependientes subirían sin que se repase la base. Ejemplo recalculado (Data Scientist con `python` básico): con la decisión actual `pandas` queda en el puesto 27 con Effort 4; tratando `basic` como cubierto subiría al puesto 21 con Effort 3, delante de más Skills pese a que el Learner aún no domina `python`. `python` sigue siendo la primera de la lista en ambos casos.

## Tres ejemplos reales

Las tablas se generaron ejecutando `recommend` (Frequency en %; prioridad = Frequency / Effort):

```python
from skillpath import LearnerProfile, recommend

path = recommend(LearnerProfile("Data Analyst", {"excel": "intermediate"}))
for i, it in enumerate(path.items[:10], 1):
    print(i, it.skill, f"{it.frequency:.2f}", it.effort, f"{it.frequency / it.effort:.2f}")
```

(Para los otros dos se cambia el perfil.)

### Ejemplo 1: Data Analyst con `excel` intermedio

| # | Skill | Frequency (%) | Effort | Prioridad |
|---|---|---|---|---|
| 1 | sql | 33.51 | 2 | 16.75 |
| 2 | agile | 11.03 | 1 | 11.03 |
| 3 | power bi | 18.42 | 2 | 9.21 |
| 4 | data visualization | 18.06 | 2 | 9.03 |
| 5 | tableau | 16.93 | 2 | 8.46 |
| 6 | python | 16.86 | 2 | 8.43 |
| 7 | jira | 4.94 | 1 | 4.94 |
| 8 | r | 9.60 | 3 | 3.20 |
| 9 | statistics | 5.59 | 3 | 1.86 |
| 10 | data modeling | 6.64 | 4 | 1.66 |

Cálculo de `power bi`: Difficulty 2; su único Prerequisite es `excel`, que el Learner domina, así que Faltantes* = {} y Effort = 2 + 0 = 2. Prioridad = 18.42 / 2 = 9.21. Cálculo de `machine learning` (puesto 17): Difficulty 4; Faltantes* = {`python`, `statistics`} (ninguna dominada), Effort = 4 + 2 = 6; Prioridad = 5.65 / 6 = 0.94.

Posiciones: `machine learning` 17, `deep learning` 56 (Effort 8), `tensorflow` 62; `linux` 23, `docker` 45, `kubernetes` 50. Cada Skill sale después de sus bases. Con Frequency menor a 0.2 % en este Role (`deep learning` 0.19, `tensorflow` 0.09, `pytorch` 0.07) y Effort 8, las Skills de la cadena profunda quedan al final.

### Ejemplo 2: Data Scientist con `python` avanzado

| # | Skill | Frequency (%) | Effort | Prioridad |
|---|---|---|---|---|
| 1 | sql | 55.07 | 2 | 27.54 |
| 2 | data visualization | 24.79 | 2 | 12.39 |
| 3 | agile | 10.61 | 1 | 10.61 |
| 4 | r | 29.59 | 3 | 9.86 |
| 5 | tableau | 19.14 | 2 | 9.57 |
| 6 | aws | 22.14 | 3 | 7.38 |
| 7 | statistics | 15.45 | 3 | 5.15 |
| 8 | machine learning | 42.99 | 5 | 8.60 |
| 9 | java | 15.24 | 3 | 5.08 |
| 10 | git | 9.96 | 2 | 4.98 |

Aquí se ve el ajuste topológico: `machine learning` tiene prioridad 8.60 (mayor que la de `statistics`, 5.15), pero requiere `statistics`, así que sale justo después de ella, en el puesto 8. Cálculo: Difficulty 4; `python` está dominada, `statistics` no, así que Faltantes* = {`statistics`} y Effort = 4 + 1 = 5; Prioridad = 42.99 / 5 = 8.60.

Posiciones: `deep learning` 41 (Effort 7) y `tensorflow` 42 (Effort 7) quedan después de `machine learning` (8); `docker` 26 y `kubernetes` 37 después de `linux` 24.

### Ejemplo 3: Software Engineer sin Skills

| # | Skill | Frequency (%) | Effort | Prioridad |
|---|---|---|---|---|
| 1 | agile | 33.86 | 1 | 33.86 |
| 2 | python | 37.90 | 2 | 18.95 |
| 3 | html | 14.05 | 1 | 14.05 |
| 4 | sql | 23.96 | 2 | 11.98 |
| 5 | java | 33.88 | 3 | 11.29 |
| 6 | jira | 9.82 | 1 | 9.82 |
| 7 | git | 19.12 | 2 | 9.56 |
| 8 | aws | 27.83 | 3 | 9.28 |
| 9 | linux | 14.97 | 2 | 7.49 |
| 10 | javascript | 28.75 | 4 | 7.19 |

Cálculo de `javascript`: Difficulty 3 y su Prerequisite `html` no está dominado, así que Effort = 3 + 1 = 4; Prioridad = 28.75 / 4 = 7.19. Cálculo de `kubernetes`: Difficulty 4; Faltantes* = {`docker`, `linux`}, Effort = 4 + 2 = 6; Prioridad = 17.65 / 6 = 2.94, puesto 22.

Posiciones: `linux` 9, `docker` 17, `kubernetes` 22 (cada una después de su base); `machine learning` 48 (Frequency 7.16, pero espera a `statistics`, puesto 47, que tiene Frequency baja en este Role), `deep learning` 56 (Effort 8) y `tensorflow` 57 (Effort 8), estas dos con Frequency menor a 1 % en este Role.

## Alternativas descartadas

Se compararon cuatro variantes con scripts sobre el Catalog real. "Aditivo" = Difficulty + faltantes; "multiplicativo" = Difficulty × (1 + faltantes). Todas con el mismo ajuste topológico.

| Variante | Ventajas | Desventajas |
|---|---|---|
| (a) Aditivo, solo faltantes directos (la versión anterior) | Muy simple. Effort acotado (máximo 6). | Subestima las Skills profundas: `tensorflow` con Effort 5 en vez de 8 (Data Scientist sin Skills: 5 frente a 8; con `python` avanzado: 5 frente a 7). El ajuste topológico debe corregir mucho más: en Data Scientist sin Skills mueve 47 de 64 Skills, frente a 37 con la fórmula actual (en Data Scientist con `python` avanzado, 45 frente a 34). |
| **Elegida:** aditivo, faltantes transitivos | El Effort refleja la cadena completa. Mueve menos Skills al ajustar (el orden por prioridad ya respeta más los Prerequisites). Effort máximo 8. | Suma lineal: cada faltante pesa lo mismo sin importar su Difficulty. |
| (b) Multiplicativo, faltantes directos y transitivos | Penaliza más lo que tiene muchas bases pendientes. Casi no necesita ajuste en Data Analyst y Data Scientist (7 a 13 Skills movidas). | Castiga en exceso: Effort hasta 20 (`tensorflow`, `deep learning` en Data Scientist sin Skills). `machine learning` (Frequency 42.99 en Data Scientist) baja del puesto 9 al 14 aunque es una de las Skills más pedidas. Un solo Prerequisite duplica o triplica el costo. |
| Nivel básico tratado como cubierto | Más simple de explicar para el Learner ("ya conozco algo"). | Las Skills dependientes suben sin repasar la base (`pandas` del puesto 27 al 21 con `python` básico en Data Scientist). |

La variante (b) con solo faltantes directos queda entre las dos primeras: Effort hasta 12 y `machine learning` en el puesto 14 en Data Scientist sin Skills.

Cifras (Data Scientist sin Skills, 64 Skills): `tensorflow` puesto 40 / 48 / 44 / 52 y Effort 5 / 8 / 8 / 20 para las variantes (a) / elegida / (b) solo directos / (b) completa.

## Limitaciones

- **Difficulty y Prerequisites son juicio experto** (ADR 0001), redactados por un agente y aprobados por una persona. No son dato observado en las Offers. Cambiar un valor cambia el orden.
- **Frequency mide cuánto aparece una Skill en las Offers**, no su relevancia para una persona concreta. Una Skill muy frecuente puede no interesar a este Learner.
- **Todavía no hay similitud** entre el Learner y los perfiles de las Offers. El ticket 05 ajustará la prioridad con ella.
- **Effort aditivo**: cada Prerequisite pendiente suma 1, sin importar su Difficulty (un faltante de Difficulty 1 pesa igual que uno de Difficulty 5). Es una aproximación.
- **Recorrido detenido en Skills dominadas** asume que dominar una Skill implica sus bases; puede ser optimista.
- **Los niveles son tres y burdos**: "intermedio" cuenta igual que "avanzado" para decidir qué está dominado.
- La Frequency de un Role refleja los datos de LinkedIn disponibles (ver `catalog/README.md`).

## Firma

Compuerta humana del ticket 04: quien revisa este documento lo firma aquí.

- **Nombre:** Oscar
- **Fecha:** 2026-10-20
- **Comentarios:** Aprobada tal cual, sin cambios. Las limitaciones listadas arriba quedan abiertas para que Gabriel las revise si quiere.

---

## Extensión con similitud (ticket 05)

> **Esta sección es POSTERIOR a la firma de arriba y fue aprobada por Oscar el 2026-10-20 (ver el último punto de esta sección).** Lo firmado (fórmula, Effort, desempate y ajuste topológico) no se modificó; esta sección solo agrega un factor. La viñeta de Limitaciones "Todavía no hay similitud..." queda **superada** por esta extensión; se dejó intacta por estar en el texto firmado. El criterio de similitud se explica en `docs/similarity.md`.

Con la similitud `sim(s) ∈ [0, 1]` entre la Skill candidata y lo que el Learner ya sabe o le interesa:

```
Prioridad(s) = Frequency(s, r) × (1 + sim(s)) / Effort(s)
```

- Sin Skills conocidas ni intereses reconocidos, `sim = 0` para todas y la fórmula es exactamente la firmada (`Frequency / Effort`); el orden no cambia.
- La similitud puede aumentar la prioridad hasta el doble (`sim = 1`). Es una extensión mínima: la Frequency y el Effort siguen mandando y la similitud desempata a favor de lo cercano.
- Desempate (prioridad, Frequency, nombre) y ajuste topológico por Prerequisites: sin cambios.

Ejemplo real (Data Scientist con `python` avanzado; Frequency en %):

| Skill | Frequency | Effort | sim | Prioridad firmada (`F/E`) | Prioridad con similitud |
|---|---|---|---|---|---|
| sql | 55.07 | 2 | 0.69 | 27.54 | 46.53 |
| r | 29.59 | 3 | 0.66 | 9.86 | 16.37 |
| agile | 10.61 | 1 | 0.39 | 10.61 | 14.75 |
| aws | 22.14 | 3 | 0.24 | 7.38 | 9.18 |

`r` pasa del puesto 4 al 3 y `agile` del 3 al 4: `r` está más cerca de `python` que `agile`, y como `r` tiene mucha más Frequency la diferencia de similitud (0.66 frente a 0.39) basta para invertir el orden.

**Alternativas no elegidas:** `Frequency / Effort + λ·sim` (mezcla unidades distintas y exige elegir λ según el Role) y `Frequency × sim / Effort` (por construcción llevaría a 0 la prioridad de toda Skill sin relación, aunque sea muy frecuente; no se midió, es razonamiento). No se encontró evidencia con ejemplos reales de que otra forma fuera claramente mejor.

- **Aprobación humana de la extensión:** Oscar, 2026-10-20 (reconocida tal cual, sin cambios).

---

## Fuente de la Frequency para Learners de nivel inicial (ticket 07)

> **Sección POSTERIOR a la firma y a la extensión con similitud. Pendiente de acuse humano.** Lo firmado no se modificó.

La fórmula **no cambia**: `Prioridad(s) = Frequency(s, r) × (1 + sim(s)) / Effort(s)`. Solo cambia de dónde sale la Frequency cuando el Learner profile declara nivel de experiencia inicial: en lugar de la Frequency base (asaniczka), se usa una mezcla con la Frequency de Offers de nivel inicial de arshkon. El valor por defecto (con experiencia) conserva exactamente el comportamiento anterior. Detalle, pesos y limitaciones en `docs/entry-level-complement.md`.

- **Acuse humano:** pendiente.
