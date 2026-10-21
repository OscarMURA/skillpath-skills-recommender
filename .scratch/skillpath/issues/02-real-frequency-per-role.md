# 02: Frequency real por Role

**What to build:** El Learning path deja de usar datos de ejemplo y pasa a basarse en la demanda real de las Offers. Se cargan los tres datasets de asaniczka (un Role por dataset), se unifican variantes de una misma Skill con una tabla de alias, se excluyen habilidades blandas y genéricas, y se calcula la Frequency de cada Skill por Role.

**Blocked by:** 01

**Status:** done

- [x] La Frequency por Role se calcula como porcentaje de las Offers del Role que mencionan la Skill
- [x] Existen la tabla de alias y la lista de exclusión, ambas versionadas y documentadas
- [x] Una prueba verifica casos conocidos (por ejemplo, variantes de Python cuentan como una sola Skill; communication queda excluida)
- [x] El Learning path del punto de entrada ya usa la Frequency real
- [x] Los archivos de `datos/` no se versionan

## Handoff

**Qué se hizo (2026-10-20, líder Opus, trabajador Sonnet):**

- `skillpath/frequency.py`: carga los tres datasets de asaniczka (un dataset = un Role), normaliza `job_skills` (minúsculas, espacios, puntuación de borde sobrante; conserva `.net`, `c++`, `c#`, `node.js`, `ci/cd`), aplica alias, descarta exclusiones y calcula la Frequency por Role. También `load_frequency_table` para leer el CSV pequeño.
- `skillpath/build_frequency.py`: comando reproducible `.venv/bin/python -m skillpath.build_frequency` (opciones `--datos`, `--out`, `--min-frequency 1.0`, `--top N`, `--raw`). Escribe `catalog/frequency_by_role.csv` (617 filas, ~26 KB). En ejecución el recomendador solo lee ese CSV.
- `catalog/aliases.csv` (80 alias), `catalog/exclusions.txt` (46 exclusiones) y `catalog/README.md` (criterios, comando, limitaciones y casos dudosos).
- `skillpath/catalog.py`: sin Frequency inventada; carga la real del CSV. Docstring corregido: el 02 reemplazó la Frequency y el 03 reemplaza el Catalog de 5 Skills (sigue placeholder). `ROLES` = Data Analyst, Software Engineer, Data Scientist.
- `skillpath/recommender.py`: `recommend` (misma firma) usa la Frequency real buscando el nombre normalizado de la Skill del Catalog. Skill sin dato en el Role: Frequency 0.0, sigue como candidata y la explicación dice "No aparece en las ofertas de {role} analizadas."
- Pruebas: `tests/test_frequency.py` (fixtures pequeñas en memoria: variantes de Python cuentan una vez, communication excluida, Offer repetida cuenta una vez, vacíos fuera del denominador, rango y valor exacto, normalización de `.net`/`c++`/`c#`, archivos versionados) y 3 pruebas nuevas en `tests/test_recommend.py` (tres Roles, Frequency real, Skill sin dato). Resultado verificado por el líder: `32 passed`. App verificada con `AppTest` en los tres Roles sin excepciones; `app/streamlit_app.py` no necesitó cambios.

**Decisiones:**

- Denominador = Offers del Role con `job_skills` no vacío (DA 12.705, SE 9.367, DS 4.336). Cada Offer cuenta una vez por Skill.
- El CSV guarda Skills con Frequency >= 1,0 %, más las Skills del Catalog aunque estén bajo el umbral (Pandas en DA y SE; Excel y Tableau en SE).
- Referencia: Software Engineer python 37,79 % / sql 23,96 % sin alias; 37,90 % / 23,96 % con alias.
- Pendiente de revisión humana: alias y exclusiones discutibles listados en `catalog/README.md` (p. ej. variantes de `agile` unificadas inflan `agile` a 33,9 % en SE; se excluyeron `research`, `training`, `customer service`; se conservaron `data analysis`, `machine learning`, `agile`, áreas como `finance`).

**Qué sigue:** ticket 03 (Catalog curado de ~60 Skills). El Catalog debe usar nombres que, normalizados con `aliases.csv`, coincidan con las Skills de `frequency_by_role.csv`; si alguna del Catalog queda bajo el umbral, el build ya la incluye si está en el Catalog.

Nada está en commit: revisar y hacer commit a mano.
