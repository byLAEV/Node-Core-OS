# Certificado de identidad artística musical y distribución streaming — Trilema Records

**ID del servicio:** `trilema-music-streaming`  
**Estado:** propuesta documental / no emitido  
**Interfaz local prevista:** `http://127.0.0.1:8765`  
**Ámbito:** identidad artística, catálogo musical, derechos declarados, publicación y distribución de audio y video en streaming.

## Propósito

Definir un servicio de Node Core OS para que Trilema Records pueda administrar una identidad artística musical verificable y operar un catálogo de obras y grabaciones con distribución de audio y video. La interfaz web se ejecutará localmente en `127.0.0.1:8765`; el servicio deberá poder trabajar con almacenamiento local y, cuando esté configurado, almacenamiento distribuido mediante Kubo IPFS.

Este documento registra una especificación de producto. **No afirma que la interfaz, el servidor de streaming, la emisión de certificados, la distribución comercial ni las integraciones con plataformas estén implementadas o disponibles.**

## Componentes funcionales propuestos

1. **Identidad artística:** nombre artístico, identificador persistente, perfiles públicos, integrantes y vínculos autorizados con personas u organizaciones.
2. **Credencial firmada:** declaración verificable del vínculo entre la identidad artística y la entidad emisora/administradora, con emisor, clave, fechas, versión, estado y revocación.
3. **Catálogo:** obras, grabaciones máster, versiones, portadas, videos, metadatos, créditos, colaboradores, ISRC/ISWC cuando existan y territorios.
4. **Declaración de derechos:** titularidad o licencia declarada, cadena de autorizaciones, porcentajes si están documentados, territorios, ventanas y restricciones. La credencial no sustituye contratos ni determina por sí sola la titularidad legal.
5. **Distribución:** preparación de paquetes y metadatos, destinos, estado de entrega, acuses, historial de cambios y retiros.
6. **Streaming local:** catálogo reproducible desde el servicio local, con control de acceso y URLs temporales cuando corresponda. No debe exponerse el servidor de desarrollo a Internet por defecto.
7. **Integridad y almacenamiento:** hash de cada archivo, manifiesto de contenido, almacenamiento local y opción de fijación/recuperación en Kubo IPFS.
8. **Auditoría:** registro de acciones, versiones, consentimientos, publicaciones, retiros y verificaciones.
9. **Privacidad:** separación entre metadatos públicos, información contractual privada y secretos; nunca almacenar claves privadas en el catálogo ni publicarlas en IPFS.

## Interfaz local

- Dirección prevista: `http://127.0.0.1:8765`.
- El enlace solo funcionará cuando el servicio esté instalado y ejecutándose en el mismo equipo.
- En la primera etapa, enlazar únicamente a loopback; no usar `0.0.0.0` ni publicar el puerto en una red externa sin autenticación, autorización, TLS y revisión de seguridad.
- La interfaz deberá mostrar estado del servicio, almacenamiento local, estado de Kubo, catálogo, credenciales, publicaciones y registros de auditoría.
- La API deberá versionarse y validar cada entrada; las acciones de publicación y retiro requieren confirmación y registro.

## Límites de confianza

- Una firma demuestra que una clave firmó una declaración y que el contenido no cambió; no demuestra automáticamente que la persona sea quien dice ser ni que posea los derechos de una obra.
- La identidad civil, la representación de Trilema Records y los derechos musicales deben verificarse mediante documentación y procesos separados.
- Los hashes e identificadores IPFS acreditan integridad/referenciabilidad del contenido, no licencias ni autorización para distribuirlo.
- La distribución a DSPs (servicios de música digital) depende de acuerdos, requisitos técnicos y cuentas habilitadas; este proyecto no debe prometer disponibilidad automática.
- El streaming de obras requiere autorización de los titulares pertinentes, incluyendo derechos de composición, grabación, interpretación y audiovisuales según el caso.

## Etapas de implementación

1. Modelo de datos y esquema de credencial; validación de metadatos y estados.
2. Servicio HTTP local en loopback, API versionada y autenticación local.
3. Catálogo local con hashes y manifiestos reproducibles.
4. Integración opcional con Kubo: add/pin/cat, verificación de CID y manejo de fallos.
5. Reproductor de audio/video local con rangos HTTP, límites de tamaño y formatos permitidos.
6. Flujo de revisión de derechos, aprobación, publicación y retiro.
7. Adaptadores de distribución externos solo tras verificar documentación y credenciales de cada destino.
8. Pruebas automatizadas, revisión de seguridad, respaldo/recuperación y documentación de instalación.

## Criterios mínimos de aceptación

- La aplicación escucha exclusivamente en `127.0.0.1:8765` por defecto.
- Una credencial inválida, expirada o revocada no se presenta como válida.
- Un archivo modificado no coincide con el hash registrado.
- El sistema distingue metadatos públicos, privados y secretos.
- El sistema impide publicar contenido sin una declaración de derechos revisada y aprobación explícita.
- Las operaciones de carga, publicación, retiro y cambio de derechos quedan auditadas.
- La indisponibilidad de Kubo no corrompe el catálogo local ni se reporta como publicación exitosa.
- Las pruebas distinguen funcionalidades implementadas de integraciones simuladas.

## Archivos de esta carpeta

- [Especificación del servicio](./SERVICE-SPECIFICATION.md)
- [Modelo inicial de credencial](./music-identity-credential.schema.json)

## Estado de certificación

Esta carpeta es una definición inicial del producto dentro del catálogo. No es un certificado ya emitido, una acreditación de derechos de autor, una licencia de distribución ni evidencia de que el streaming esté funcionando. La emisión de una credencial requerirá un emisor configurado, una política de confianza, evidencia revisada, firma, verificación y mecanismo de revocación.
