# Redes distribuidas, validación y consenso

- **ID de categoría:** `CAT-NETWORK-CONSENSUS`
- **Estado:** `proposed`
- **Política económica:** `pending-consensus`

## Servicios potenciales

- Verificación de bloques o estados protocolarios.
- Comprobación de firmas y transiciones de estado.
- Corroboración de evidencias de nodos conforme a una regla publicada.
- Pruebas de recuperación ante particiones y fallos de comunicación.
- Relay y sincronización cuando un protocolo implementado lo permita.

## Requisitos de participación

El nodo debe ejecutar una versión compatible del protocolo, validar entradas, registrar el resultado, proteger credenciales y exponer métricas necesarias sin revelar secretos. La política debe distinguir identidades criptográficas diferentes de operadores realmente independientes cuando esa independencia sea relevante.

## Evidencias y aceptación

Usar identificadores de tarea y bloque, versión de protocolo, hashes de entradas y salidas, resultado determinista o regla de validación, marca temporal y firma cuando corresponda. Rechazar evidencias duplicadas, incompatibles o fuera de la política de aceptación.

## Límites

Más firmas o nodos no prueban por sí mismos independencia, veracidad ni consenso correcto. No se fija una recompensa por bloque o voto en esta ficha; la economía queda pendiente de consenso.
