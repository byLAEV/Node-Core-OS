# Paquete interno `p2p_contracts`

## Propósito

Este paquete contendrá la lógica de dominio de Node Core OS P2P Contracts. Debe permanecer separado de la interfaz de terminal, del punto de entrada y de los detalles concretos de transporte, almacenamiento o contenido.

**Estado actual:** documentación de diseño. Los módulos descritos aquí aún no están implementados.

## Módulos previstos y responsabilidades

- `cli.py`: presenta el menú, formularios, estados y cuenta regresiva al usuario.
- `config.py`: concentra la configuración versionada, incluido el tiempo mínimo de propagación.
- `schemas.py`: valida anuncios de ventana, solicitudes, recibos, lotes y manifiestos.
- `canonical_json.py`: genera una representación determinista para el contenido que se va a hashear.
- `hashing.py`: calcula y verifica SHA-256 sobre los bytes canónicos.
- `request_service.py`: crea y valida solicitudes locales.
- `propagation_service.py`: crea anuncios de receptor y coordina las comprobaciones del preestado conocido.
- `window_service.py`: implementa la máquina de estados de la ventana y calcula cuándo se habilita el envío propio.
- `batch_service.py`: agrupa referencias de solicitudes y define el orden determinista del lote.
- `manifest_service.py`: construye y verifica manifiestos inmutables enlazados al estado padre.
- `receipt_service.py`: crea y valida recibos asociados a una solicitud y preestado.
- `identity_consent.py`: presenta los campos de identidad que se publicarían y exige consentimiento expreso.
- `storage_adapter.py`: integra las operaciones con el almacenamiento real de Node Core OS.
- `content_adapter.py`: integra la publicación, recuperación y política de conservación de contenido.
- `network_adapter.py`: encapsula el transporte de mensajes de aplicación una vez que su interfaz real esté auditada.
- `errors.py`: define errores explícitos para que los fallos no se oculten ni se reporten como éxito.

Los nombres son la estructura prevista, no módulos disponibles actualmente. Se pueden ajustar después de la auditoría del runtime siempre que se mantengan las responsabilidades y los criterios de prueba.

## Contratos de diseño

1. Validar datos externos antes de utilizarlos.
2. Rechazar campos requeridos ausentes, tipos incorrectos y versiones no soportadas.
3. Calcular hashes solo después de producir los bytes canónicos definitivos.
4. Distinguir entre solicitud válida, recibida, incluida en un lote y lote aceptado.
5. No cambiar el estado aceptado ni cerrar un lote si falla una verificación obligatoria.
6. Mantener la lógica de tiempo separada de la interfaz para poder probarla con un reloj simulado.
7. Mantener el transporte separado de la lógica de negocio para permitir pruebas deterministas sin red.
8. No asumir que un identificador de par de Kubo equivale a una firma de contenido o a una identidad personal verificada.
9. No generar claves privadas ni añadir funciones privadas/OpenPGP.
10. No introducir dependencias externas hasta justificar su necesidad y documentar su compatibilidad.

## Orden recomendado de implementación

1. Esquemas y errores.
2. Serialización canónica y hashes con vectores de prueba.
3. Servicios locales de solicitudes y recibos.
4. Máquina de estados de la ventana con reloj simulado.
5. Servicio de lotes y manifiestos.
6. Adaptadores de almacenamiento y contenido.
7. Adaptador de transporte verificado.
8. Integración con CLI y runtime.

## Criterios de aceptación del paquete

- Las mismas entradas canónicas producen exactamente los mismos bytes y hashes.
- Los datos inválidos se rechazan con errores claros.
- Cada transición de estado tiene condiciones explícitas.
- La lógica local puede probarse sin Kubo ni conectividad de red.
- Los adaptadores pueden probarse con dobles de prueba y luego con los servicios reales.
- No se declara ninguna operación exitosa sin comprobar el resultado.
