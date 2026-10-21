# Catálogo curado de ~60 Skills en lugar de extracción libre

Los datasets traen decenas de miles de valores distintos de Skills (46.543 solo en Data Analyst), mezclan habilidades blandas y no incluyen descripción, Prerequisites ni Difficulty. Decidimos recomendar únicamente las ~60 Skills técnicas más frecuentes de los tres Roles, con atributos redactados por un agente y revisados por humanos, en vez de recomendar cualquier cadena que aparezca en las ofertas.

Alternativas descartadas: usar todo el campo `job_skills` (ruidoso y sin atributos para razonar sobre esfuerzo) y extraer Skills de las descripciones con NLP (más cobertura, pero requiere validación que el taller no necesita).

Consecuencia: los Prerequisites y la Difficulty son juicio experto, no dato observado; se documenta como limitación en la Parte 3.
