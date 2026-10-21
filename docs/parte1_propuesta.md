# SkillPath — Parte 1. Propuesta del sistema recomendador

**Grupo 7:** Gabriel Escobar, Oscar Ramirez

**Nombre del proyecto:** SkillPath — Sistema recomendador de rutas de aprendizaje de habilidades profesionales basado en ofertas laborales y conocimientos previos.

## 1.1. Contexto de aplicación

Los estudiantes y profesionales del sector tecnológico necesitan desarrollar competencias que les permitan acceder a mejores oportunidades laborales. Sin embargo, identificar qué habilidades deberían aprender y en qué orden puede resultar complicado debido a la variedad de tecnologías solicitadas por las empresas y las diferencias entre los conocimientos previos de cada persona.

El proyecto propone un sistema que recomiende rutas de aprendizaje personalizadas, priorizando las habilidades que aporten mayor valor profesional y que el usuario pueda adquirir con menor esfuerzo, aprovechando sus conocimientos actuales. Se enfocará en tres perfiles: Data Analyst, Software Engineer y Data Scientist.

El sistema utilizará información de ofertas laborales para identificar las competencias más solicitadas en cada perfil y las relacionará con los conocimientos del usuario. Su propósito es ayudar a priorizar el aprendizaje de habilidades que permitan fortalecer su perfil profesional de manera eficiente, mejorando su preparación para las oportunidades laborales.

## 1.2. Usuarios y elementos a recomendar

Los usuarios principales serán estudiantes universitarios, recién graduados y profesionales del sector tecnológico interesados en desarrollar competencias para desempeñarse como Data Analyst, Software Engineer o Data Scientist. Sus conocimientos previos podrán variar, por lo que las recomendaciones deberán adaptarse a su punto de partida.

El usuario seleccionará su perfil profesional objetivo e indicará las habilidades que ya posee, su nivel de dominio y sus áreas de interés. Con esta información se construirá un perfil inicial que permitirá identificar las competencias que le faltan y estimar cuáles podría aprender con mayor facilidad aprovechando sus conocimientos actuales.

Los elementos recomendados serán habilidades técnicas profesionales, como lenguajes de programación, herramientas, frameworks y conocimientos especializados. El catálogo se construirá a partir de tres datasets de Kaggle:

- [Data Analyst Job Postings](https://www.kaggle.com/datasets/asaniczka/data-analyst-job-postings)
- [Software Engineer Job Postings](https://www.kaggle.com/datasets/asaniczka/software-engineer-job-postings-linkedin)
- [Data Scientist Job Postings](https://www.kaggle.com/datasets/asaniczka/data-scientist-linkedin-job-postings)

Estos tres datasets solo contienen ofertas de nivel Associate y Mid senior. Para cubrir también el nivel inicial, se complementarán con las ofertas de nivel Entry del dataset [LinkedIn Job Postings (2023–2024)](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings), detectando las habilidades del catálogo en el texto de sus descripciones.

Se tendrán en cuenta los siguientes atributos, obtenidos del procesamiento de los datasets o complementados durante la construcción del catálogo:

- **Nombre:** identifica la habilidad técnica, como Python, SQL o Docker.
- **Categoría:** clasifica la habilidad en áreas como programación, bases de datos o análisis de datos.
- **Descripción:** explica en qué consiste la habilidad y sus principales aplicaciones.
- **Perfiles relacionados:** identifica los perfiles profesionales en cuyas ofertas aparece la habilidad.
- **Frecuencia de aparición:** indica qué tan recurrente es la habilidad en las ofertas laborales de cada perfil.
- **Conocimientos previos recomendados:** identifica las habilidades que facilitan o son necesarias para aprender una nueva competencia.
- **Dificultad estimada:** representa la complejidad de adquirir la habilidad, considerando sus características y conocimientos previos necesarios.

La frecuencia de aparición se calculará a partir de las ofertas laborales, mientras que los conocimientos previos recomendados y la dificultad se definirán durante la preparación del catálogo. Estos atributos permitirán evaluar tanto la relevancia profesional de una habilidad como el esfuerzo estimado que necesitaría cada usuario para aprenderla.

El sistema presentará una ruta priorizada de habilidades por aprender, comenzando por aquellas que ofrezcan una mejor relación entre su valor profesional y el esfuerzo de aprendizaje estimado.

## 1.3. Estrategias de recomendación

### Filtrado basado en contenido

Será una de las estrategias principales. El sistema comparará el perfil profesional objetivo, los intereses y los conocimientos actuales del usuario con las características de las habilidades identificadas en las ofertas laborales.

Este enfoque permitirá identificar competencias relacionadas con los objetivos profesionales del usuario y con las habilidades que ya domina. Se propone utilizar TF-IDF y similitud del coseno para calcular la relación entre las descripciones de las habilidades, los intereses y los conocimientos del usuario.

La similitud permitirá identificar habilidades relevantes y relacionadas, aunque no determinará por sí sola el esfuerzo necesario para aprenderlas.

### Recomendación basada en conocimiento

Complementará el filtrado basado en contenido para determinar qué habilidades conviene aprender primero. Se utilizarán relaciones de prerrequisitos y niveles de dificultad para estimar el esfuerzo de aprendizaje de cada habilidad según los conocimientos actuales del usuario.

El sistema priorizará aquellas competencias que combinen una alta relevancia en las ofertas laborales con un menor esfuerzo estimado de aprendizaje. Así, una habilidad muy solicitada, pero que requiera numerosos conocimientos adicionales, podría tener menor prioridad que otra igualmente relevante que el usuario pueda adquirir más rápidamente.

También se aplicarán reglas para excluir habilidades que el usuario ya domina y respetar los conocimientos previos necesarios para avanzar hacia competencias más complejas.

### Filtrado colaborativo

Utiliza las preferencias e interacciones de usuarios similares para generar recomendaciones. No será la estrategia principal porque inicialmente no se contará con suficientes usuarios ni registros de aprendizaje.

Podría incorporarse cuando el sistema disponga de información sobre las habilidades aprendidas por otros usuarios y sus experiencias de aprendizaje.

### Recomendación basada en popularidad

Prioriza las habilidades que aparecen con mayor frecuencia en las ofertas laborales. Esta información será útil para estimar su relevancia profesional dentro de cada perfil.

Sin embargo, no se utilizará como único criterio, ya que las habilidades más solicitadas no necesariamente son las que un usuario puede adquirir con mayor facilidad. Su frecuencia se utilizará como un factor de priorización junto con los conocimientos previos y el esfuerzo estimado de aprendizaje.

### Enfoque híbrido

El proyecto utilizará un enfoque combinado de filtrado basado en contenido y recomendación basada en conocimiento, complementado con la frecuencia de aparición de las habilidades en las ofertas laborales.

El filtrado basado en contenido permitirá identificar competencias relevantes para el perfil profesional y los intereses del usuario, mientras que las reglas basadas en conocimiento permitirán estimar su accesibilidad y establecer un orden de aprendizaje.

De esta manera, el sistema no se limitará a recomendar las habilidades más solicitadas, sino que buscará construir una ruta de aprendizaje personalizada que priorice las competencias con mayor valor profesional alcanzable en el menor esfuerzo estimado, considerando el punto de partida de cada usuario.
