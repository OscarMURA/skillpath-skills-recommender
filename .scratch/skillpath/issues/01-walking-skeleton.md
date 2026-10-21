# 01: Esqueleto andante

**What to build:** Un Learner elige un Role y marca algunas Skills en una página web mínima, y recibe un Learning path de un mini-catálogo de 5 Skills escrito a mano. Atraviesa todas las capas (motor, interfaz y prueba) para que el equipo tenga una base ejecutable sobre la que crecer. Incluye dejar listos el paquete del motor, el entorno y la forma de correr pruebas.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Existe un único punto de entrada que recibe un Learner profile y devuelve un Learning path
- [x] La página web llama a ese punto de entrada y muestra el resultado
- [x] Al menos una prueba pasa llamando al punto de entrada con un perfil de ejemplo
- [x] El entorno se instala y la app y las pruebas se ejecutan con comandos documentados en el README
- [x] El código y los archivos están en inglés y usan el vocabulario de `GLOSSARY.md`

## Handoff

**Qué se hizo (2026-10-20, líder Opus, trabajador Sonnet):**

- `pyproject.toml`: paquete `skillpath` (setuptools), dependencias streamlit, pandas, scikit-learn; extra `dev` con pytest; `testpaths = ["tests"]`; `requires-python = ">=3.12"`.
- `skillpath/`: `models.py` (`Skill`, `LearnerProfile`, `LearningPath`, `LearningPathItem`), `catalog.py` (mini Catalog de 5 Skills para Data Analyst: SQL, Excel, Python, Pandas con Prerequisite Python, Tableau; y Frequency de ejemplo), `recommender.py` (`recommend`). Punto de entrada único: `from skillpath import recommend`.
- `app/streamlit_app.py`: página en español (Role, Skills conocidas con Mastery level, tabla del Learning path con Frequency, Effort y explicación).
- `tests/test_recommend.py`: 6 pruebas que solo llaman a `recommend` (Skills dominadas excluidas, nivel básico sigue candidato, Prerequisite antes, determinismo, perfil vacío, Role desconocido). Resultado: `6 passed`.
- README: sección "Cómo ejecutar". Entorno en `.venv/` con Python 3.12.14 (`python3.12`).
- Verificado por el líder: pytest pasa; Streamlit headless en el puerto 8599 respondió 200; la página corre sin excepciones con `streamlit.testing.v1.AppTest`.

**Decisiones (provisionales, sujetas a revisión humana):**

- `LearnerProfile.known_skills` es `dict[str, str]` con niveles internos `basic`/`intermediate`/`advanced`; la UI los muestra como básico/intermedio/avanzado.
- Effort provisional = Difficulty + número de Prerequisites faltantes; prioridad provisional = Frequency / Effort; empates por nombre; luego ajuste para que cada Skill quede después de sus Prerequisites faltantes (si hubiera ciclo, el resto se agrega por puntaje). Un Prerequisite conocido solo en nivel básico cuenta como faltante. La fórmula real se define en el ticket 04 y requiere firma humana.
- Role desconocido lanza `ValueError`. `interests` existe pero aún no se usa (ticket 05).
- Catalog y Frequency de `catalog.py` son datos inventados marcados PLACEHOLDER. Ojo: el comentario dice que el ticket 02 reemplaza ambos; en realidad el 02 reemplaza la Frequency y el 03 el Catalog.
- Se usó Python 3.12 en vez del 3.14 por defecto de Homebrew; no se probó si 3.14 funciona.

**Qué sigue:** ticket 02 (`02-real-frequency-per-role.md`): calcular la Frequency real por Role desde las Offers de asaniczka y reemplazar `FREQUENCY` en `skillpath/catalog.py`, manteniendo `recommend` como seam y las pruebas en verde.

Nada está en commit: revisar y hacer commit a mano.
