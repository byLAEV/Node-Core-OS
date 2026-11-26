# Simulación de respuesta a incidentes multiempresa

## Objetivo

Validar el siguiente paso de Node Core OS byLAEV mediante datos sintéticos: dos pools empresariales independientes registran activos propios, reciben reportes autenticados y solicitan apoyo de nodos de identidad ante un incidente.

## Escenario automatizado

1. Se crean dos pools empresariales con claves de prueba independientes.
2. Cada pool emite un certificado firmado para un activo distinto: un dominio Web2 ficticio y un dispositivo ficticio.
3. Cada activo firma un reporte de instalación.
4. La pool verifica firma, emisor, vigencia y relación entre certificado y activo.
5. Se vuelve a entregar un mismo evento para comprobar que el registro idempotente no lo duplica.
6. Un activo genera un reporte sintético de incidente firmado y vinculado a su certificado.
7. Los nodos de identidad confiables emiten recomendaciones firmadas sobre el mismo resumen criptográfico del incidente.
8. La prueba verifica que solo dos o más nodos distintos y confiables pueden formar el quórum de recomendación.
9. Se altera un reporte para comprobar que la autenticación rechaza el contenido manipulado.

## Ejecución local

Requiere Python 3.10+ y `cryptography`.

```bash
python -m pip install cryptography
python scripts/multi_enterprise_incident_response_simulation.py
python -m unittest discover -s tests -p 'test_multi_enterprise_incident_response_simulation.py' -v
```

GitHub Actions ejecuta el escenario y las pruebas de regresión en cambios relevantes, pull requests y ejecución manual.

## Criterios de aceptación

- Dos pools empresariales se mantienen separadas.
- Un certificado de una pool no se puede instalar como certificado de propiedad de otra pool.
- Un reporte dirigido a la pool equivocada se rechaza.
- Certificados vencidos, firmas inválidas y reportes manipulados se rechazan.
- Reenviar el mismo ID de evento no crea un segundo registro dentro de la ejecución.
- Repetir el voto de un mismo nodo no alcanza el quórum.
- Votos alterados o de nodos fuera de la lista confiable no cuentan.
- La respuesta de la simulación no modifica activos reales.

## Límites y advertencias

La simulación es local y en memoria. No contacta dominios reales, no escanea hosts, no genera tráfico de ataque, no despliega certificados X.509, no cambia firewalls y no ejecuta mitigación real. Una recomendación de quórum no demuestra que un ataque haya sido detenido.

La lista de nodos confiables se suministra explícitamente a la prueba. La existencia de claves distintas no demuestra independencia organizacional ni resistencia completa a Sybil. La idempotencia solo se prueba en la memoria del proceso; la producción requiere almacenamiento durable, control de concurrencia y protección anti-replay que sobreviva a reinicios.

Todavía quedan fuera de alcance: transporte autenticado entre nodos, consenso distribuido desplegado, rotación y revocación compartida, persistencia, autorización granular por pool, análisis de evidencias operativas, pruebas de partición de red y adaptadores de contención.

## Siguientes pasos tras un CI exitoso

1. Revisar los resultados de GitHub Actions y los logs de cada caso.
2. Integrar estos contratos con los módulos de identidad ya existentes, evitando duplicar sistemas.
3. Añadir persistencia e idempotencia transaccional.
4. Probar particiones, repetición de incidentes, nodos comprometidos, certificados revocados y reportes contradictorios.
5. Medir detección, falsos positivos, tiempo de respuesta y recuperación en un entorno aislado.
6. Evaluar mecanismos de contención reales solo con autorización explícita y pruebas seguras.
