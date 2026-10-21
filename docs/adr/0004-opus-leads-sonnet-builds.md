# Opus lidera y Sonnet programa

El desarrollo se organiza con un agente líder que reparte tickets a agentes trabajadores. Decidimos que el líder use un modelo Opus (planificar, ordenar dependencias, verificar criterios de aceptación y actualizar el estado) y que los trabajadores usen Sonnet (escribir código, tests y documentos), para dejar el razonamiento más caro donde más pesa y el volumen de implementación en el modelo más económico.

Consecuencia: cada delegación debe indicar el modelo explícitamente, porque por defecto un subagente hereda el del líder.
