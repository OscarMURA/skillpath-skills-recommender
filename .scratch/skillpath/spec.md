Status: ready-for-agent

# SkillPath: recomendador de rutas de aprendizaje de Skills

## Problem Statement

Un Learner del sector tecnológico (estudiante, recién graduado o profesional) quiere acceder a mejores oportunidades como Data Analyst, Software Engineer o Data Scientist, pero no sabe qué Skills aprender ni en qué orden. Las Offers piden cientos de tecnologías distintas y cada persona parte de conocimientos diferentes. Hoy decide por intuición o por lo más popular, que no siempre es lo más alcanzable para su punto de partida. Además, el taller del curso exige una propuesta (Parte 1), un recomendador basado en contenido con prototipo ejecutable (Parte 2) y un análisis de sesgos (Parte 3), evaluados por coherencia entre sí.

## Solution

El Learner elige un Role objetivo y marca las Skills que ya conoce con su Mastery level. SkillPath compara su Learner profile con el Catalog y devuelve un Learning path: una lista corta y ordenada de Skills que combina alta Frequency en las Offers del Role con bajo Effort, respetando los Prerequisites y excluyendo lo que ya domina. Cada recomendación se explica en lenguaje simple. El Learner usa una app web sencilla; el equipo entrega además un notebook y documentos que cubren las tres partes del taller.

## User Stories

1. Como Learner, quiero elegir mi Role objetivo entre Data Analyst, Software Engineer y Data Scientist, para que la ruta sea relevante a ese perfil.
2. Como Learner, quiero marcar las Skills que ya conozco, para no recibir recomendaciones de lo que domino.
3. Como Learner, quiero indicar mi Mastery level en cada Skill conocida (básico, intermedio, avanzado), para que el sistema distinga entre lo que domino y lo que debo profundizar.
4. Como Learner, quiero indicar áreas de interés, para que la ruta priorice Skills afines a lo que me motiva.
5. Como Learner, quiero ver un Learning path ordenado, para saber por dónde empezar.
6. Como Learner, quiero que una Skill con Prerequisites que no tengo aparezca después de ellos, para no intentar aprenderla sin base.
7. Como Learner, quiero que una Skill muy demandada pero muy costosa para mí baje de prioridad frente a otra igualmente demandada que puedo alcanzar rápido, para avanzar con eficiencia.
8. Como Learner, quiero ver por qué se me recomienda cada Skill (Frequency en mi Role, Skills relacionadas que ya sé, Prerequisites cubiertos), para confiar en la recomendación.
9. Como Learner, quiero ver el Effort estimado de cada Skill, para planificar mi tiempo.
10. Como Learner, quiero ver qué Skills todavía me faltan de mi Skill gap más allá del top, para tener una visión completa.
11. Como Learner nuevo sin datos, quiero llenar un formulario inicial corto, para recibir recomendaciones desde la primera sesión.
12. Como Learner que no llena nada, quiero ver igualmente las Skills más demandadas de mi Role, para no encontrarme con una pantalla vacía.
13. Como Learner de nivel inicial (junior), quiero que la demanda considere Offers de nivel Entry, para que la ruta refleje lo que piden a quien empieza.
14. Como Learner, quiero cambiar mi Role o mis Skills y ver la ruta actualizada al instante, para explorar escenarios.
15. Como Learner, quiero que el resultado sea el mismo si repito los mismos datos, para poder confiar y comparar.
16. Como Learner, quiero ver Skills relacionadas a las que ya domino, para aprovechar mi base.
17. Como Learner, quiero que la ruta incluya alguna Skill complementaria distinta a lo más obvio, para no quedarme solo en lo que ya conozco.
18. Como Learner, quiero que el sistema no me muestre habilidades blandas ni términos genéricos, para recibir recomendaciones técnicas concretas.
19. Como integrante del equipo, quiero un Catalog curado de unas 60 Skills con categoría, descripción, Difficulty y Prerequisites, para razonar sobre el esfuerzo.
20. Como integrante del equipo, quiero revisar y corregir a mano los Prerequisites y la Difficulty antes de usarlos, para controlar la calidad del Catalog.
21. Como integrante del equipo, quiero calcular la Frequency por Role a partir de las Offers de los tres datasets de asaniczka, para tener una base consistente.
22. Como integrante del equipo, quiero una tabla de alias que unifique variantes de una misma Skill, para no contarla varias veces.
23. Como integrante del equipo, quiero complementar la Frequency con Offers de nivel Entry de arshkon detectando Skills del Catalog en el texto, para cubrir el nivel junior.
24. Como integrante del equipo, quiero un único punto de entrada que reciba un Learner profile y devuelva un Learning path, para probar el sistema completo con personas de prueba.
25. Como integrante del equipo, quiero evaluar el sistema ocultando una Skill de las Offers y midiendo si aparece en las recomendaciones, para tener una métrica objetiva.
26. Como integrante del equipo, quiero métricas de sesgo (concentración de exposición, cobertura del Catalog, diferencia entre rutas junior y senior), para sustentar la Parte 3.
27. Como integrante del equipo, quiero un notebook que cuente el proceso paso a paso con código comentado y la fuente de los datasets, para cumplir la Parte 2.
28. Como integrante del equipo, quiero un diagrama que muestre fuente de datos, procesamiento, motor, formulario de arranque en frío y presentación, para cumplir el punto 2.2.
29. Como integrante del equipo, quiero un documento final con las Partes 1, 2 y 3 coherentes entre sí, para obtener la máxima calificación según la rúbrica.
30. Como Gabriel retomando el trabajo de Oscar, quiero que cada ticket deje su estado y notas de traspaso, para continuar sin perder contexto.
31. Como agente líder, quiero tickets con criterios de aceptación y bloqueos explícitos, para delegar y verificar cada pieza.

## Implementation Decisions

- **Arquitectura:** un paquete de Python con el motor de recomendación, que consumen tanto el notebook como la app web. La lógica no se duplica en ninguna de las dos.
- **Modelo de datos:** el Catalog es un conjunto de datos versionado (nombre, categoría, descripción, Difficulty de 1 a 5, Prerequisites, alias), junto con una lista de exclusión de habilidades blandas y genéricas.
- **Fuente base:** el campo de habilidades de los tres datasets de asaniczka (misma estructura de columnas). El Role de cada Offer es el dataset de origen; se documenta como limitación.
- **Frequency:** porcentaje de las Offers del Role que mencionan la Skill.
- **Complemento junior:** Offers de nivel Entry/Associate de arshkon; se detectan Skills del Catalog por búsqueda de términos en la descripción. Los datasets rajatraj0502 y el resto de arshkon no se usan. Ver ADR 0002.
- **Similitud:** TF-IDF y similitud del coseno sobre la descripción de cada Skill, su categoría y las Skills con que co-ocurre en las Offers. Mide cercanía entre las Skills conocidas o de interés del Learner y las candidatas.
- **Effort:** crece con la Difficulty y con el número de Prerequisites que aún faltan.
- **Prioridad inicial:** frecuencia del Role, ajustada por similitud, dividida por Effort. El orden final respeta los Prerequisites. La fórmula exacta es una propuesta sujeta a revisión humana.
- **Reglas de conocimiento:** excluir Skills dominadas (Mastery level intermedio o avanzado); las de nivel básico siguen siendo candidatas.
- **Arranque en frío:** formulario inicial; si está vacío, el resultado cae a las Skills de mayor Frequency del Role. Una Skill nueva en el Catalog no sufre arranque en frío porque trae sus atributos.
- **Sin LLM en ejecución:** el recomendador es determinista. Ver ADR 0003.
- **Interfaz:** app web en Streamlit, en español, con formulario de Learner profile, Learning path con explicación y vista del Skill gap.
- **Orquestación:** un agente líder (Opus) reparte tickets a agentes trabajadores (Sonnet). Cada ticket tiene estado, bloqueos, criterios de aceptación y notas de traspaso. Ver ADR 0004.
- **Compuertas humanas:** revisión del Catalog, firma de la fórmula de prioridad y revisión final contra la rúbrica.

## Testing Decisions

- Una buena prueba verifica solo comportamiento externo, no detalles internos.
- **Seam único:** el punto de entrada que recibe un Learner profile y devuelve un Learning path. Las pruebas lo llaman con personas de prueba.
- Personas de prueba (al menos cinco) con rutas esperadas revisadas a mano: por ejemplo, alguien que ya domina Python y SQL no recibe esas Skills; una Skill con Prerequisites faltantes aparece después de ellos; la misma entrada da siempre el mismo resultado; un perfil vacío devuelve las Skills más frecuentes del Role.
- El Catalog se valida aparte como datos: toda Skill tiene Difficulty en rango, Prerequisites existentes en el propio Catalog y sin ciclos.
- Evaluación offline: ocultar una Skill de cada Offer y medir si se recupera en las primeras K recomendaciones; métricas de sesgo para la Parte 3.
- No hay pruebas previas en el repositorio: se establecen como referencia.

## Out of Scope

- Filtrado colaborativo y cualquier uso de interacciones reales de usuarios.
- Recomendar cursos, certificaciones u ofertas de empleo concretas.
- Extracción de Skills desde texto libre más allá de la búsqueda por diccionario del complemento junior.
- Cuentas de usuario, persistencia de perfiles y despliegue en producción.
- Roles distintos de Data Analyst, Software Engineer y Data Scientist.
- Reclasificar Offers por título (el Role es el dataset de origen).

## Further Notes

- Fecha límite y formato exacto de entrega pendientes de confirmar con el curso; se asume notebook más documento PDF/Word.
- El repositorio de GitHub aún no existe porque la red del equipo bloquea la conexión; hasta entonces el tracker es local en `.scratch/`.
- Sesgos a documentar en la Parte 3: Offers en inglés y de EE. UU., Roles no puros, ausencia de niveles junior en asaniczka (parcialmente cubierta por arshkon) y juicio experto en Prerequisites y Difficulty.
