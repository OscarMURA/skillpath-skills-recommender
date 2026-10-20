# SkillPath

Sistema recomendador de rutas de aprendizaje de habilidades profesionales (Data Analyst, Software Engineer, Data Scientist) basado en ofertas laborales y conocimientos previos.

Proyecto del curso de Sistemas Recomendadores (2026-1) — Grupo 7: Gabriel Escobar y Oscar Ramirez.

## Contenido

- [`docs/parte1_propuesta.md`](docs/parte1_propuesta.md) — Parte 1: contexto, usuarios/ítems y estrategias.
- [`datos/`](datos/README.md) — instrucciones para descargar los datasets (no se versionan).

## Estrategia

Híbrido: filtrado basado en contenido (TF-IDF + similitud del coseno) + recomendación basada en conocimiento (prerrequisitos y dificultad), ponderado por la frecuencia de cada habilidad en las ofertas.
