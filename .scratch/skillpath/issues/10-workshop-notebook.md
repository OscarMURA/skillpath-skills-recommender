# 10: Notebook del taller

**What to build:** Un notebook que cuenta el proceso de punta a punta con código comentado: datos, Catalog, similitud, reglas, ranking, una recomendación para al menos un perfil y la fuente de los datasets. Cubre la Parte 2.3 de la rúbrica.

**Blocked by:** 08

**Status:** done

- [x] Se ejecuta de principio a fin sin errores
- [x] Muestra recomendaciones para al menos un perfil de Learner
- [x] Explica con claridad el criterio de similitud
- [x] Documenta la fuente de cada dataset usado
- [x] Reutiliza el paquete del motor, sin duplicar su lógica

## Handoff

**Fecha:** 2026-10-21. **Líder:** Opus (planificó, delegó y verificó). **Trabajador:** Sonnet (notebook, prueba, extra y README; una segunda tanda corrigió el título).

### Qué se hizo
- `notebooks/skillpath.ipynb` (60 celdas, ~604 KB, 6 gráficas PNG), en español y guardado con salidas. Secciones: 0 objetivo y problema; 1 datos y fuentes (tabla con los 3 datasets de asaniczka como base, arshkon como complemento de nivel inicial y rajatraj0502 descargado pero no usado, según el ADR 0002; enlaces de Kaggle y advertencia de términos); 2 alias y exclusiones; 3 Frequency por Role (gráfica); 4 Catalog, Difficulty y grafo de Prerequisites; 5 criterio de similitud (documento de cada Skill, TF-IDF y coseno con un ejemplo de juguete comprobado contra `TfidfVectorizer`, vecinos reales de `python` y `sql`, ancla del Learner con Mastery level e intereses, y comprobación contra `compute_similarity` y `recommend`); 6 reglas de conocimiento y prioridad resuelta paso a paso; 7 tres Learner profiles (Data Analyst en arranque en frío, Data Scientist con experiencia, Software Engineer de nivel inicial con w = 0.68 y n = 216); 8 evaluación y sesgos leídos de `reports/`; 9 limitaciones, app Streamlit y qué sigue.
- `skillpath/similarity.py`: atributo de solo lectura `SimilarityModel.documents` (Skill → texto del documento). No cambia resultados; lo cubre una prueba en `tests/test_similarity.py`.
- `tests/test_notebook.py`: ejecuta el notebook en memoria, con `datos/` y con `SKILLPATH_DATOS_DIR` apuntando a una carpeta vacía. Se omite si falta el extra `notebook`.
- `pyproject.toml`: extra `notebook` (jupyter, nbclient, nbformat, nbconvert, ipykernel, matplotlib). `README.md`: sección «Cuaderno del taller».

### Cómo ejecutarlo
`pip install -e ".[dev,notebook]"`; abrir con `jupyter lab notebooks/skillpath.ipynb`; regenerar con `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.record_timing=False notebooks/skillpath.ipynb` (unos 3 a 5 s). `pytest` corre 335 pruebas (las 331 previas y 4 nuevas). La prueba del notebook tarda unos 6 s, así que no lleva marcador `slow`.

### Decisiones
- Sin `datos/` solo se omite la vista previa de los datasets crudos, con un aviso «OMITIDO». arshkon se lee con pocas filas, nunca completo.
- Las cifras del notebook salen de `recommend` y de las funciones del paquete. Las cuentas didácticas (ejemplo de juguete, cadena de Effort de `tensorflow`) se comprueban con `assert` contra el motor.
- La sección 5.5 lee los atributos privados `_by_normalized` y `_by_category` del modelo, solo para etiquetar cómo se resuelve cada interés.
- Nota menor: `docs/similarity.md` dice «153 palabras» para todos los Roles, pero Software Engineer tiene 152. El notebook dice «unas 150».

### Qué sigue
Ticket 11 (documentos del taller) y ticket 12 (revisión final contra la rúbrica).
