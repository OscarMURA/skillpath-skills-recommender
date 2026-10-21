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

## Cuaderno del taller

[`notebooks/skillpath.ipynb`](notebooks/skillpath.ipynb) cuenta el proceso de punta a punta (datos y fuentes, Catalog, criterio de similitud, reglas de conocimiento, Learning paths de ejemplo, resumen de la evaluación). Se versiona con las salidas ya ejecutadas, así que se puede leer sin ejecutarlo. Reutiliza el paquete `skillpath` y no necesita `datos/`: lo esencial sale de `catalog/` y `reports/` (solo se omite la vista previa de los datasets crudos).

```bash
# Instalar el extra opcional del cuaderno (Jupyter, nbclient, matplotlib...)
pip install -e ".[dev,notebook]"

# Abrirlo
jupyter lab notebooks/skillpath.ipynb

# Ejecutarlo de principio a fin y guardarlo con salidas (unos 5 s)
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.record_timing=False notebooks/skillpath.ipynb
```

Opcional: `SKILLPATH_DATOS_DIR=/ruta` apunta el cuaderno a otra carpeta de datasets (o a una vacía para comprobar que funciona sin ellos). La prueba `tests/test_notebook.py` lo ejecuta en una copia temporal, con y sin `datos/` (tarda unos 6 s y se omite si no está instalado el extra `notebook`).
