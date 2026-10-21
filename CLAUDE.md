# SkillPath

Taller de Sistemas Recomendadores (Grupo 7). Recomendador de rutas de aprendizaje de habilidades técnicas. Ver `README.md`, `GLOSSARY.md` y `docs/adr/`.

## Convenciones

- UI y documentos en español; código, archivos y nombres de repo en inglés.
- Usa el vocabulario de `GLOSSARY.md` (Skill, Role, Offer, Catalog, Frequency, Learner...). No uses los sinónimos que el glosario marca con _Avoid_.
- `datos/` y los PDFs del curso no se versionan.

## Modelos de los agentes

- **Agente líder: Opus.** Lee la spec y los tickets, decide el orden, delega y verifica criterios de aceptación.
- **Agentes trabajadores: Sonnet.** Escriben el código, los tests y los documentos de cada ticket. Al delegar con la herramienta Agent, pasar `model: "sonnet"`.
- Ver `docs/adr/0004-opus-leads-sonnet-builds.md`.

## Agent skills

### Issue tracker

Tickets y specs como Markdown local en `.scratch/<feature>/`. Ver `docs/agents/issue-tracker.md`.

### Domain docs

Contexto único: `GLOSSARY.md` y `docs/adr/` en la raíz. Ver `docs/agents/domain.md`.
