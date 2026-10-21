# 02: Frequency real por Role

**What to build:** El Learning path deja de usar datos de ejemplo y pasa a basarse en la demanda real de las Offers. Se cargan los tres datasets de asaniczka (un Role por dataset), se unifican variantes de una misma Skill con una tabla de alias, se excluyen habilidades blandas y genéricas, y se calcula la Frequency de cada Skill por Role.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] La Frequency por Role se calcula como porcentaje de las Offers del Role que mencionan la Skill
- [ ] Existen la tabla de alias y la lista de exclusión, ambas versionadas y documentadas
- [ ] Una prueba verifica casos conocidos (por ejemplo, variantes de Python cuentan como una sola Skill; communication queda excluida)
- [ ] El Learning path del punto de entrada ya usa la Frequency real
- [ ] Los archivos de `datos/` no se versionan

## Handoff

_(el agente completa)_
