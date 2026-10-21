# SkillPath

Sistema que recomienda a un estudiante o profesional de TI una ruta ordenada de habilidades técnicas por aprender, a partir de la demanda en ofertas laborales y de lo que ya sabe.

## Language

**Skill**:
Capacidad técnica concreta (lenguaje, herramienta, framework o concepto) que aparece en las ofertas y que una persona puede aprender.
_Avoid_: competencia, tecnología, habilidad blanda

**Role**:
Uno de los tres perfiles profesionales objetivo: Data Analyst, Software Engineer o Data Scientist.
_Avoid_: perfil, cargo, job title

**Offer**:
Publicación laboral usada como evidencia de qué Skills demanda un Role.
_Avoid_: vacante, posting, anuncio

**Catalog**:
Conjunto curado de unas 60 Skills técnicas que el sistema puede recomendar, cada una con categoría, descripción, Difficulty y Prerequisites.
_Avoid_: lista de habilidades, base de habilidades

**Frequency**:
Porcentaje de las Offers de un Role que mencionan una Skill.
_Avoid_: popularidad, conteo, demanda

**Prerequisite**:
Skill que conviene o es necesario conocer antes de aprender otra.
_Avoid_: dependencia, requisito previo

**Difficulty**:
Complejidad intrínseca de adquirir una Skill, en una escala de 1 a 5 definida al armar el Catalog.
_Avoid_: dificultad estimada, nivel

**Effort**:
Costo estimado para un Learner concreto de adquirir una Skill, según su Difficulty y los Prerequisites que aún le faltan.
_Avoid_: esfuerzo de aprendizaje, costo

## Learner

**Learner**:
Persona que recibe la recomendación: estudiante, recién graduado o profesional de TI.
_Avoid_: usuario, estudiante, cliente

**Mastery level**:
Grado en que un Learner domina una Skill: básico, intermedio o avanzado. Desde intermedio se considera dominada.
_Avoid_: nivel de dominio, nivel

**Learner profile**:
Role objetivo del Learner, sus Skills conocidas con su Mastery level y sus áreas de interés.
_Avoid_: perfil de usuario

**Skill gap**:
Skills que el Role objetivo demanda y que el Learner aún no domina.
_Avoid_: brecha, faltantes

**Learning path**:
Lista ordenada de Skills que se recomienda aprender, que respeta los Prerequisites y prioriza alto Frequency con bajo Effort.
_Avoid_: ruta, plan de estudio, recomendación
