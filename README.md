# SkillPath

Sistema recomendador de rutas de aprendizaje de habilidades profesionales (Data Analyst, Software Engineer, Data Scientist) basado en ofertas laborales y conocimientos previos.

Proyecto del curso de Sistemas Recomendadores (2026-1) — Grupo 7: Gabriel Escobar y Oscar Ramirez.

## Contenido

- [`docs/parte1_propuesta.md`](docs/parte1_propuesta.md) — Parte 1: contexto, usuarios/ítems y estrategias.
- [`datos/`](datos/README.md) — instrucciones para descargar los datasets (no se versionan).

## Estrategia

Híbrido: filtrado basado en contenido (TF-IDF + similitud del coseno) + recomendación basada en conocimiento (prerrequisitos y dificultad), ponderado por la frecuencia de cada habilidad en las ofertas.

## Cómo ejecutar

Requiere Python 3.12 o superior.

```bash
# Crear el entorno virtual e instalar el paquete con dependencias de desarrollo
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ejecutar la app
streamlit run app/streamlit_app.py

# Ejecutar las pruebas
pytest

# Ejecutar la evaluación (leave-one-skill-out y métricas de sesgo; escribe en reports/, ~18 s)
python -m skillpath.evaluate
```
