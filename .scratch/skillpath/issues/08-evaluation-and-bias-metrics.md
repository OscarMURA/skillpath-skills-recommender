# 08: Evaluación y métricas de sesgo

**What to build:** Evidencia objetiva de que el sistema funciona y de dónde están sus sesgos: una evaluación leave-one-skill-out sobre las Offers, al menos cinco personas de prueba con rutas revisadas a mano y métricas de sesgo (concentración de exposición, cobertura del Catalog y diferencia entre rutas junior y senior).

**Blocked by:** 05, 07

**Status:** done

- [x] La evaluación oculta una Skill por Offer y reporta si se recupera en las primeras K recomendaciones
- [x] Hay al menos cinco personas de prueba con rutas esperadas documentadas
- [x] Se reportan concentración de exposición, cobertura del Catalog y diferencia junior vs senior
- [x] Los resultados están en un formato que se puede citar en la Parte 3

## Handoff

**Fecha:** 2026-10-21. **Líder:** Opus. **Trabajadores:** Sonnet (A: `evaluate.py`, pruebas y `reports/`; B: personas de prueba; C: documento).

### Qué se hizo

- `skillpath/evaluate.py`: comando `.venv/bin/python -m skillpath.evaluate` (opciones `--datos`, `--out`, `--sample-per-role`, `--seed`, `--test-fraction`). Tarda unos 18 s y es determinista: dos ejecuciones dieron CSV idénticos byte a byte. No modifica `catalog/frequency_by_role.csv` ni `catalog/cooccurrence.csv` (compara su hash antes y después).
- Evaluación leave-one-skill-out: partición 80/20 por sha1 del conjunto de Skills normalizadas de la Offer (`job_link` si está vacío), Frequency y co-ocurrencia recalculadas solo con entrenamiento e inyectadas sin tocar los archivos versionados, 500 casos por Role. Cuatro métodos: línea base de Frequency pura, fórmula sin similitud, sistema completo y aleatorio.
- Métricas de sesgo sobre los artefactos de producción (516 Learner profiles por Role: 500 de Offers de prueba y 16 sintéticos): concentración, cobertura, exposición por categoría y por Difficulty, correlación exposición-Frequency y comparación nivel inicial frente a con experiencia.
- `tests/test_evaluate.py` (12 pruebas) y `tests/test_personas.py` (40 pruebas, 6 Learner profiles de prueba).
- 11 CSV en `reports/` (listados en `docs/evaluation.md`).
- `docs/evaluation.md`: metodología, resultados, personas, sesgos, limitaciones y evidencia para la Parte 3. `pyproject.toml` añade `scipy` (la importa `evaluate.py`) y `README.md` el comando de evaluación.
- `.venv/bin/pytest -q`: 298 passed.

### Hallazgos principales

- **El sistema completo es muy superior al azar:** hit@10 global 0,670 frente a 0,173; MRR 0,362 frente a 0,080 (1.500 casos).
- **No supera claramente a la línea base de Frequency pura:** hit@5 empata (0,496), hit@10 0,670 frente a 0,660 y MRR 0,362 frente a 0,374.
- **La similitud aporta poco:** frente a la fórmula sin similitud, +1,4 puntos en hit@5, +2,0 en hit@10 y +0,024 en MRR.
- **Sesgo de accesibilidad:** el Effort hunde las Skills de Difficulty 4-5 (hit@10 0,223 y 0,000 frente a 0,451 y 0,222 de la línea base) y favorece las de Difficulty 1-2. La Difficulty 4-5 (25 % del Catalog) recibe 1,5-5,2 % de la exposición.
- **Cobertura baja:** 34-44 % del Catalog por Role con K = 10; 16 Skills no aparecen en ningún Role (`deep learning`, `scikit-learn`, `pytorch`, `tensorflow`, `airflow`...). La categoría machine learning recibe 4,7 % de la exposición en Data Scientist (9,4 % del Catalog).
- **Sesgo hacia lo frecuente:** Spearman exposición-Frequency de 0,76 a 0,85; las 10 Skills más expuestas ocupan 72-76 % de los puestos con K = 10.
- **El complemento de nivel inicial cambia poco:** Jaccard@10 de 0,75 a 0,82. Subida dudosa de `sas` en Data Scientist inicial (0,1 % a 8,0 % de exposición; 13 de 47 Offers de arshkon, detección por texto).
- **Fuga evitada:** con la clave por conjunto de Skills la fuga de Offers idénticas es 0; con hash de `job_link` habría sido 18, 41 y 7.

### Decisiones (revisar)

- **Clave de partición = conjunto de Skills**, no `job_link`, para que las plantillas idénticas no crucen la partición.
- **Learner simulado:** demás Skills del Catalog de la Offer en Mastery level intermedio, sin intereses, con experiencia; mínimo 2 Skills del Catalog; muestra de hasta 500 por Role con semilla 42.
- **Sesgo medido sobre los artefactos de producción** (Frequency y co-ocurrencia de todas las Offers), con grupo `all` y K = 10 como referencia.
- **La línea base de Frequency pura** (`popularity`) se incluye para dejar claro cuándo el sistema aporta sobre simplemente ordenar por Frequency; el resultado es honesto: aporta poco en aciertos y se justifica por accesibilidad.
- **Tres expectativas de las personas resultaron erróneas** y se documentan en `docs/evaluation.md`: en P4 solo `react` y `typescript` entran al top 10 del bloque web/DevOps esperado; `deep learning` queda en el puesto 34 (no en el top 15) con interés declarado, y `pandas` en el puesto 28 (no en el top 10) para P6. Observación para el diseño: un interés explícito pesa poco frente a la Frequency.

### Pendiente de revisión humana

Los Learning paths esperados de las 6 personas de prueba los escribió un agente (no un humano) a partir de razonamiento de dominio. Están marcados así en `docs/evaluation.md`.

### Qué sigue

- El 09 (app completa) puede usar `docs/evaluation.md` y `reports/`.
- El 10 (notebook) puede leer los CSV de `reports/`.
- El 11 (documentos) cita `docs/evaluation.md` en las Partes 2 (2.3) y 3 (3.1 y 3.2).

Nada está en commit: revisar y hacer commit a mano.
