# 04: Prerequisites, Effort y Mastery level

**What to build:** El Learner indica su Mastery level en cada Skill conocida y el Learning path se vuelve personal: excluye lo que domina (desde intermedio), mantiene lo de nivel básico como candidato para profundizar, pone cada Skill después de sus Prerequisites y prioriza alta Frequency con bajo Effort.

**Blocked by:** 03

**Status:** done

- [x] Quien domina una Skill (intermedio o avanzado) no la recibe; con nivel básico sí puede recibirla
- [x] Una Skill nunca aparece antes de sus Prerequisites faltantes
- [x] Una Skill muy frecuente pero muy costosa baja frente a otra igual de frecuente y más alcanzable (caso de prueba)
- [x] La misma entrada produce siempre el mismo resultado
- [x] La fórmula de prioridad queda documentada y **firmada por un humano** (compuerta)

## Handoff

**Fecha:** 2026-10-20. **Líder:** Opus. **Trabajadores:** Sonnet (el primero se cortó por un error de red; un segundo revisó y completó).

### Qué se hizo

- `skillpath/recommender.py`: `recommend(LearnerProfile) -> LearningPath` (mismo seam, mismos modelos) ahora calcula Effort y prioridad. Lee el Catalog vía `catalog.CATALOG` y `catalog.FREQUENCY`, así las pruebas los sustituyen por fixtures con monkeypatch.
- `tests/test_priority.py`: 34 casos nuevos (Mastery level, orden con cadenas profundas, Effort transitivo, frecuente-pero-costosa, determinismo y desempates).
- `docs/priority-formula.md`: fórmula, decisiones, 3 ejemplos reales, alternativas descartadas, limitaciones y sección Firma.
- `app/streamlit_app.py` no cambió: ya mostraba Effort y explicación.

### Fórmula final

`Effort(s) = Difficulty(s) + |Faltantes*(s)|`, `Prioridad(s) = Frequency(s, Role) / Effort(s)`. Faltantes* = Prerequisites directos y transitivos (sin duplicados) que el Learner no domina.

Orden: prioridad descendente; desempate por mayor Frequency y luego nombre ascendente; después ajuste topológico estable (se toma la Skill mejor ordenada cuyos Prerequisites directos pendientes ya estén colocados), con salvaguarda contra ciclos.

### Alternativas comparadas (números en el documento)

- Difficulty + faltantes directos (antigua): `tensorflow` con Effort 5 frente a 8; el ajuste topológico mueve 47 de 64 Skills en Data Scientist sin Skills, frente a 37 con la fórmula elegida.
- Difficulty × (1 + faltantes): castiga en exceso (Effort hasta 20); `machine learning` (Frequency 42.99) baja del puesto 9 al 14 en Data Scientist sin Skills.
- Básico como cubierto: `pandas` sube del puesto 27 al 21 con `python` básico en Data Scientist, sin repasar la base.

### Decisiones

- Faltantes transitivos, no solo directos.
- Nivel básico = no dominado: cuenta como faltante y la Skill sigue siendo candidata. Intermedio y avanzado = dominada.
- Desempate explícito (Frequency y luego alfabético) para que el resultado no dependa del orden de inserción.
- Recorrido detenido en Skills dominadas. Consecuencia: si el Learner domina `deep learning` pero no `machine learning`, `tensorflow` no exige `machine learning` antes (Effort 4, sin faltantes).

### Adaptaciones de pruebas

Ninguna prueba previa necesitó cambios: las 53 anteriores pasan sin modificar. Las aserciones de texto de `tests/test_recommend.py` siguen válidas porque la explicación conserva la frase "Aparece en el X% de las ofertas de {role}; esfuerzo estimado N.".

### Resultado de pytest

`.venv/bin/pytest -q`: 87 passed.

### Cómo firmar

1. Revisar `docs/priority-formula.md`.
2. Anotar nombre y fecha en su sección Firma.
3. Marcar el criterio "firmada por un humano" de este ticket.
4. Pasar el Status a `done`.

Nada está en commit: revisar y hacer commit a mano.

## Firma (compuerta humana)

Oscar firmó la fórmula de prioridad tal cual el 2026-10-20 en `docs/priority-formula.md`, sin cambios. Status: `done`. Siguiente: ticket 05 (similitud con co-ocurrencia y explicaciones), que ajusta la prioridad con la similitud.
