# 11: Documentos del taller

**What to build:** Los documentos de las Partes 1, 2 y 3, coherentes entre sí: la Parte 1 actualizada (incluye arshkon), el análisis de arranque en frío (2.1), el diagrama de arquitectura (2.2) y el análisis y mitigación de sesgos (3.1 y 3.2).

**Blocked by:** 08, 09

**Status:** done

- [x] El diagrama muestra fuente de datos, procesamiento, motor (contenido y conocimiento), Frequency, formulario de arranque en frío y presentación
- [x] Los sesgos están clasificados y explicados con su impacto en el problema
- [x] Cada sesgo tiene su propia estrategia de mitigación con explicación de cómo reduce su impacto
- [x] Las Partes usan el mismo objetivo del sistema y las mismas estrategias que la Parte 1
- [x] Los números citados provienen de los resultados del ticket 08

## Handoff

**Fecha:** 2026-10-21. **Líder:** Opus (planificó y verificó). **Trabajador:** Sonnet.

### Qué se hizo

- Archivos creados:
  - `docs/taller/documento_final.md` (fuente del documento).
  - `docs/taller/documento_final.docx`, generado con `.venv/bin/python docs/taller/build_docx.py` (pandoc vía `pypandoc_binary` y post-proceso con `python-docx`). Las dependencias se instalaron solo en `.venv`, no en `pyproject`.
  - `docs/taller/img/architecture.png` y `architecture.py` (matplotlib; `.venv/bin/python docs/taller/img/architecture.py`).
  - Copias de las capturas en `docs/taller/img/` (`app-software-engineer.png` se copió pero no se usa).
- Correcciones a `docs/`:
  - `docs/similarity.md`: «153 palabras» pasa a «152 a 153 según el Role» (DA 153, DS 153, SE 152; verificado ejecutando el código).
  - `docs/evaluation.md`: «todas las Offers son de EE. UU.» pasa a 79,8 % EE. UU. y el resto Reino Unido, Canadá y Australia (columna `search_country`, 21 252 de 26 616; verificado por el líder).
- El ejemplo de recomendación (Tabla 8) se obtuvo con `recommend(LearnerProfile("Data Scientist", {"python": "advanced"}))`. El líder lo re-ejecutó y comprobó; se corrigió la similitud de azure a 0,20.
- 335 pruebas en verde.

### Verificación del .docx

- Con `python-docx`: 5 Heading 1, 8 Heading 2 (1.1 a 3.2), 36 Heading 3, 13 tablas, 3 imágenes y 16 pies de Tabla/Figura. Sin restos de Markdown. Tiene portada, índice (campo con `updateFields`) y números de página en el pie.
- **No se pudo** convertir a PDF, inspeccionar visualmente ni contar páginas: la automatización de Microsoft Word por AppleScript/`docx2pdf` agotó el tiempo (error -1712, probablemente un permiso de automatización pendiente en macOS).
- El diagrama sí se revisó visualmente (PNG). Mide 11,5 × 18,7 cm en el Word para caber con su pie.
- **Pendiente humano:** abrir en Word, aceptar la actualización de campos (índice), revisar la paginación (meta 12 a 18 páginas; el texto tiene unas 7 900 palabras con tablas, así que puede quedar algo por encima) y exportar a PDF.

### Cambios al texto de la Parte 1 de los integrantes (para aprobación)

Comparación de `docs/parte1_propuesta.md` con las secciones 1.1 a 1.3 de `docs/taller/documento_final.md`:

1. **Tiempo verbal, futuro a presente o pasado,** en todo el texto. Ejemplos: «Se enfocará en tres perfiles» pasa a «Se enfoca…»; «utilizará información» a «utiliza»; «serán estudiantes…» a «son»; «seleccionará» a «selecciona»; «se construirá un perfil» a «se construye»; «El catálogo se construirá» a «se construyó»; «se calculará» a «se calculó»; «se definirán» a «se definieron»; «presentará una ruta» a «presenta». En 1.3 igual: «Será una de las estrategias principales» a «Es una de…», «comparará» a «compara», «Se propone utilizar TF-IDF» a «Se utiliza TF-IDF», «prioriza/utiliza/aplican» en presente.
2. **1.1, párrafo nuevo «Dominio y problema».** Añade el dominio (educación y desarrollo profesional en TI), «46.543 valores distintos en el campo de habilidades (ADR 0001)», la crítica a «una lista fija de las más pedidas» y por qué un recomendador es adecuado.
3. **1.2, Usuarios.** Se agrega al final del primer párrafo la frase «Necesitan una lista corta, ordenada y explicada.»
4. **1.2, Tabla 1 (nueva)** con los campos del perfil (perfil objetivo, nivel de experiencia, habilidades conocidas, nivel de dominio con pesos 0,5; 0,75; 1,0, áreas de interés). Se añade «La Tabla 1 describe los campos del perfil; el nivel de dominio es una autodeclaración, no una prueba.» al párrafo que sigue a «Con esta información se construye un perfil inicial…».
5. **1.2, subtítulos nuevos** «Usuarios» y «Elementos a recomendar».
6. **Complemento de nivel inicial.** Original: «se complementarán con las ofertas de nivel Entry». Nuevo: «se complementan con las ofertas de nivel Entry level e Internship», más «Tras eliminar ofertas repetidas quedan 80, 216 y 47 ofertas de nivel inicial para Data Analyst, Software Engineer y Data Scientist (`catalog/frequency_entry_by_role.csv`)».
7. **Catálogo.** Nuevo párrafo: «El catálogo final es una lista curada de 64 habilidades técnicas, de las 425 distintas que quedan tras normalizar y excluir habilidades blandas». El original decía «se construirá a partir de tres datasets».
8. **Tabla 2 de atributos** sustituye la lista de viñetas (Nombre, Categoría, Descripción, Perfiles relacionados, Frecuencia, Conocimientos previos, Dificultad) por una tabla con ejemplo real por atributo. Fusiona «Perfiles relacionados» y «Frecuencia» en una fila, y **añade dos atributos:** «Habilidades que co-ocurren» (cercanía 0,738 de python y sql en Data Scientist) y «Esfuerzo (por usuario)».
9. **Dificultad** pasa de «complejidad… considerando sus características» a una escala «de 1 (introductoria) a 5 (especializada)».
10. **Párrafo posterior a la tabla.** Se reescribe en pasado y se quita la frase de que prerrequisitos y dificultad «se definirán»; ahora «se definieron durante la preparación del catálogo».
11. **1.3, párrafo introductorio nuevo** ligado al objetivo: «El objetivo pide tres cosas a la vez: una ruta relevante…, que prefiera lo de mayor valor… y que sea alcanzable… Cada estrategia cubre una de ellas.»
12. **Contenido:** se añade «(detalle en 2.3)» tras TF-IDF y coseno.
13. **Conocimiento:** se añade «(esfuerzo = dificultad + prerrequisitos pendientes)»; se funden dos párrafos de modo que «También se aplican reglas…» sigue en el mismo párrafo que el ejemplo de prioridad.
14. **Colaborativo:** original «inicialmente no se contará con suficientes usuarios»; nuevo «el sistema no cuenta con suficientes usuarios… es un sistema nuevo, sin cuentas ni historial». Se fusionan en un solo párrafo.
15. **Subsección nueva «Recomendación basada en contexto»:** «No se utiliza… El único dato contextual que entra es el nivel de experiencia». El original no la tenía.
16. **Subsección nueva «Por qué estas estrategias y no otras»** con la Tabla 3 (estrategias frente al objetivo y a los criterios de datos, perfil, ítems, escalabilidad y privacidad; incluye la fórmula `frecuencia × (1 + similitud) / esfuerzo`).
17. **Cuadro «Objetivo del sistema»** al inicio del documento (antes de la Parte 1); el original no lo tenía. El resto del texto se conserva casi literal (popularidad, híbrido), salvo el tiempo verbal.

### Decisiones para revisión humana

- **Vocabulario:** el documento usa español natural (habilidad, oferta, perfil, ruta de aprendizaje, brecha). Los términos canónicos del GLOSSARY aparecen solo en el Anexo A y entre paréntesis. El diagrama sí usa términos del repositorio (Role, Frequency, Effort…) con remisión al Anexo A.
- **Objetivo del sistema elegido:** «Recomendar a cada usuario una ruta de aprendizaje ordenada de las habilidades que le faltan para su perfil profesional objetivo, priorizando las de mayor valor en el mercado laboral que pueda adquirir con menor esfuerzo dados sus conocimientos actuales.»
- **10 sesgos (S1 a S10) y sus mitigaciones (M1 a M10):** son propuestas, no están implementadas.
- **Evaluación interpretada con honestidad:** el sistema rinde unas 5,8 veces el azar en hit@5, pero no supera claramente a la baseline de solo frecuencia (MRR 0,362 frente a 0,374).
- **Incoherencias encontradas y sin corregir:**
  - Docstring de `skillpath/similarity.py`: dice nombre ×2 y tf sublineal; el código usa ×3 y `sublinear_tf=False`.
  - La spec y el ADR 0002 hablan de «Entry/Associate»; la implementación usa Entry level e Internship.
  - `docs/similarity.md` y `docs/entry-level-complement.md` dicen «EE. UU.» sin matizar el 79,8 %.
  - La sección de nivel inicial de `docs/priority-formula.md` sigue pendiente de acuse humano.
  - Las rutas esperadas de los perfiles de prueba siguen pendientes de revisión.

### Cruce rúbrica y sección

| Criterio | Sección del documento | Valoración | Nota |
|---|---|---|---|
| 1.1 Contexto de aplicación | §1.1 | Muy bien | Dominio, problema y por qué un sistema recomendador. |
| 1.2 Usuarios y elementos | §1.2, Tablas 1 y 2 | Muy bien | Perfil del usuario y atributos de los ítems con ejemplos reales. |
| 1.3 Estrategias | §1.3, Tabla 3 | Muy bien | Estrategias ligadas al objetivo y a los 5 criterios; explica por qué no colaborativo ni contexto. |
| 2.1 Arranque en frío | §2.1, Tabla 4 | Muy bien | Usuarios sí; ítems casi no (prueba con sqlmesh); contribución de cada estrategia. Riesgo menor: no se midió el efecto del formulario. |
| 2.2 Diagrama de arquitectura | §2.2, Figura 1 y Tabla 5 | Muy bien | Diagrama alineado con las estrategias de 1.3. Riesgo: usa términos en inglés del repositorio. |
| 2.3 Prototipo funcional | §2.3 | Muy bien (probable) | Criterio de similitud con ejemplo numérico, datos con enlaces, ejemplo real y evaluación honesta. Riesgo: el sistema no supera a la popularidad pura (explicado en el texto). |
| 3.1 Sesgos | §3.1, Tabla 11 | Muy bien | 10 sesgos clasificados con evidencia. |
| 3.2 Mitigación | §3.2, Tabla 12 | Muy bien | Una mitigación por sesgo, con cómo reduce el impacto y la métrica. |
| Formato del .docx | `docs/taller/documento_final.docx` | Sin verificar visualmente | Estructura comprobada con `python-docx`; no se pudo abrir en Word ni exportar a PDF. |

### Qué sigue

Ticket 12 (revisión final contra la rúbrica, humana): aprobar los cambios a la Parte 1, abrir el .docx en Word, actualizar el índice, revisar la paginación y exportar a PDF.
