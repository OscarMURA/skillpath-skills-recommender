# 09: App Streamlit completa

**What to build:** La interfaz en español para el Learner: formulario de Learner profile (Role, Skills con niveles, intereses, experiencia), Learning path con explicaciones y una vista del Skill gap completo.

**Blocked by:** 05, 06

**Status:** done

- [x] El Learner completa su perfil y ve su Learning path con explicación por Skill
- [x] Hay una vista del Skill gap más allá del top
- [x] Cambiar el Role o las Skills actualiza el resultado
- [x] Revisada en el navegador con una persona de prueba por Role
- [x] Todo el texto visible está en español y usa el vocabulario del glosario

## Handoff

**Fecha:** 2026-10-21. **Líder:** Opus (planificó, revisó en el navegador y verificó). **Trabajador:** Sonnet (código y pruebas, en tres tandas).

### Qué se hizo

- `app/streamlit_app.py` reescrito; el motor no cambió de lógica.
  - **Barra lateral «Tu Learner profile»:** Role objetivo, experiencia, «Empezar sin datos», sugerencias del Role, Skills conocidas con Mastery level por Skill e intereses.
  - **Leyenda** «¿Qué significa cada término?» con las 11 definiciones.
  - **Avisos honestos:** muestra pequeña de nivel inicial, arranque en frío e interés no reconocido.
  - **Pestaña «Learning path»:** métricas, las primeras N Skills (10 por defecto, ajustable) en tarjetas con la explicación completa, y las 10 más frecuentes.
  - **Pestaña «Skill gap completo»:** todas las Skills con Frequency > 0 que el Learner no domina, con posición, categoría, Frequency, Effort, Difficulty y Prerequisites pendientes. Tiene filtro por categoría, orden por posición, Frequency o Effort, y ayuda en cada columna.
  - **Pestaña «Cómo funciona y límites»:** explicación simple y las limitaciones de `docs/evaluation.md`.
  - `recommend` va envuelto en `st.cache_data`.
  - Todos los widgets tienen key; las Skills declaradas, sus niveles y la pestaña activa se conservan al cambiar de Role.
  - Las sugerencias ocultan las Skills ya declaradas en el multiselect.
  - Semilla opcional del Learner profile por query params, solo en la primera carga. Ejemplo: `?role=Data+Scientist&exp=entry&known=python:intermediate,sql:basic&interests=deep+learning`. Los valores que no están en el Catalog se ignoran.
- `skillpath/recommender.py`: **solo el texto** de las explicaciones (`_explain*`), sin cambiar números, orden ni lógica.
  - «ofertas» pasa a «Offers»; «esfuerzo estimado N» pasa a «Effort N»; «prerrequisitos» pasa a «Prerequisites».
  - «al final de la ruta» pasa a «al final del Learning path».
  - «Sin habilidades… frecuencia y esfuerzo» pasa a «Sin Skills… Frequency y Effort».
- Pruebas adaptadas **solo en la cadena esperada**, por el cambio de texto: `tests/test_cold_start.py`, `test_entry_level.py`, `test_priority.py`, `test_recommend.py`, `test_similarity.py` y `test_app_entry_level.py`. En esta última también se cambió `at.table` por `at.dataframe`.
- `tests/test_app.py` reescrito.
  - Pasa de índices a keys.
  - El Learning path ya no es una tabla de 64 filas; esa comprobación pasa a la del Skill gap contra `recommend`.
  - La columna «Similitud» sale de la UI; la sustituye la comprobación de «Se relaciona con» en la explicación.
  - Pruebas nuevas, parametrizadas por los tres Roles cuando aplica:
    - perfil vacío, Skills e intereses;
    - el Skill gap completo es exactamente el del motor;
    - con Mastery level básico la Skill se queda en el Skill gap y con intermedio sale;
    - Prerequisites pendientes;
    - filtro y orden;
    - estado al cambiar de Role;
    - avisos;
    - sugerencias;
    - query params;
    - vocabulario sobre el texto visible, sobre las cadenas del archivo y sobre las explicaciones del motor.
- `.venv/bin/pytest -q`: **331 passed** (antes 298).
- Capturas en `docs/img/`, a 1440×1000:
  - `app-data-analyst.png`: P2, Learning path.
  - `app-software-engineer.png`: P4, pestaña Skill gap completo.
  - `app-data-scientist.png`: P5, Learning path.
- README sin cambios: el comando de ejecución es el mismo.

### Revisión en el navegador

Se hizo con el panel de navegador integrado y con Playwright (Chromium), con `streamlit run app/streamlit_app.py --server.headless true --server.port 8599`.

Personas revisadas, una por Role:

| Persona | Role y experiencia | Qué se vio |
|---|---|---|
| P1 | Data Analyst, inicial, vacío | Avisos de arranque en frío y de muestra de 80 Offers. |
| P2 | Data Analyst, con experiencia | Learning path y explicaciones. |
| P4 | Software Engineer, con experiencia | Skill gap de 60 Skills. Al cambiar a Data Scientist se conservan las Skills y la pestaña. |
| P5 | Data Scientist, interés deep learning | Learning path. |
| P6 | Data Scientist, inicial, interés «zzz qqq» | Avisos de muestra de 47 Offers y de interés no reconocido. |

Las explicaciones de la UI coinciden con `recommend`. No hubo excepciones en pantalla. En la consola solo aparecieron los errores de reconexión al reiniciar el servidor a propósito. El servidor quedó detenido.

Hallazgos corregidos:
- Placeholders en inglés («Choose options»).
- Etiquetas de sugerencias cortadas.
- Pestaña activa que se perdía al cambiar de Role.
- Formato de la Frequency poco homogéneo.
- Definición confusa de Effort.
- Sugerencias sin marcar para Skills ya declaradas.

Hallazgos que quedan, propios de Streamlit:
- Algunos textos internos siguen en inglés: «Select all», «Select N matches» y el menú de la barra superior.
- En el multiselect, Enter puede añadir la siguiente coincidencia si queda texto escrito.

### Decisiones de vocabulario (revisar)

- Los términos canónicos se usan en inglés dentro de frases en español («las Offers de Data Analyst», «Mastery level intermedio»), como en los docs. Cada uno se explica en la leyenda y en los `help`, sin sinónimos españoles.
- La prueba de vocabulario es más estricta que el glosario. Prohíbe además «habilidad(es)», «frecuencia», «oferta(s)», «rol», «perfil», «catálogo», «prerrequisito(s)» y «demanda».
- «Categoría», «Posición», «Experiencia» y «nivel inicial» quedan en español porque no son términos del glosario.
- Definiciones propias que conviene revisar:
  - Effort: «estimación de cuánto te tomará aprender la Skill: su Difficulty más los Prerequisites que aún no dominas». Se evita «costo» y «esfuerzo».
  - Role: «uno de los tres objetivos profesionales». Se evita «perfil».

### Qué sigue

- 10 (notebook) y 11 (documentos) pueden usar las capturas de `docs/img/` y la sección «Cómo funciona y límites» como texto base para la presentación al Learner.
- Observación para el 11: en P5 el interés «deep learning» no aparece en las explicaciones del top 10, coherente con el hallazgo del 08 (un interés pesa poco frente a la Frequency).

Nada está en commit: revisar y hacer commit a mano.
