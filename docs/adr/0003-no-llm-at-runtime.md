# El recomendador no usa LLM en tiempo de ejecución

SkillPath se construye con un equipo de agentes de desarrollo, pero el recomendador en sí es clásico: TF-IDF, similitud del coseno, reglas de Prerequisites y fórmula de prioridad. Así cada recomendación es reproducible y explicable, y el criterio de similitud se puede detallar con claridad como pide la rúbrica del taller (2.3).

Alternativa descartada: un agente LLM que arme la ruta al vuelo. Sería más flexible, pero no determinista ni evaluable con las métricas offline previstas.
