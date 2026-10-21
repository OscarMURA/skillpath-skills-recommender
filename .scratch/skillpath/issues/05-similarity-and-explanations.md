# 05: Similitud con co-ocurrencia y explicaciones

**What to build:** El sistema usa TF-IDF y similitud del coseno sobre la descripción de cada Skill, su categoría y las Skills con que co-ocurre en las Offers, para favorecer Skills cercanas a las que el Learner ya sabe o le interesan. Cada recomendación incluye una explicación simple de por qué se sugiere.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] La similitud ajusta la prioridad y su criterio está descrito con claridad en un documento corto
- [ ] Una prueba muestra que un Learner con una Skill dada recibe Skills relacionadas por delante de otras no relacionadas
- [ ] Cada elemento del Learning path trae una explicación (Frequency en el Role, Skills relacionadas que ya domina, Prerequisites cubiertos)
- [ ] Los intereses indicados por el Learner influyen en el resultado

## Handoff

_(el agente completa)_
