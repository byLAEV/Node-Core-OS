# Disponibilidad de nodos y cómputo distribuido

- **ID de categoría:** `CAT-AVAILABILITY-COMPUTE`
- **Estado:** `proposed`
- **Política económica:** `pending-consensus`

## Servicios potenciales

- Monitorización de disponibilidad bajo una definición acordada.
- Prestación de capacidad computacional para tareas autorizadas.
- Ejecución de trabajos distribuidos y entrega de resultados.
- Medición de recursos consumidos conforme a límites publicados.
- Pruebas de recuperación y continuidad de servicio.

## Requisitos de participación

Especificar versión de entorno, capacidad declarada, cuotas, aislamiento, límites de CPU/memoria/almacenamiento, permisos de entrada y salida, tratamiento de fallos y reglas de medición. Las tareas deben ser explícitas y autorizadas.

## Evidencias y aceptación

Registrar identificador de tarea, versión de runtime, entradas autorizadas, resultado, métricas firmadas o verificables y condición de aceptación. Para disponibilidad, definir intervalo, método de sondeo, tolerancia y tratamiento de mantenimiento y fallos de red.

## Límites

Un heartbeat aislado no prueba que un servicio esté disponible o sea útil durante todo un periodo. El esfuerzo computacional no demuestra automáticamente que el resultado sea correcto. La remuneración queda pendiente de consenso.
