# Especificación del servicio — Trilema Records

## 1. Identificación

- Producto: certificado de identidad artística musical y distribución de streaming de audio y video.
- Organización/servicio objetivo: Trilema Records.
- Identificador: `trilema-music-streaming`.
- Endpoint local previsto: `http://127.0.0.1:8765`.
- Estado de implementación: propuesta; endpoint y funcionalidades no verificados.

## 2. Actores y permisos

| Actor | Permisos previstos |
|---|---|
| Administrador de sello | Configurar entidad, usuarios, políticas y destinos |
| Artista | Administrar perfil, créditos y entregas autorizadas |
| Gestor de catálogo | Cargar archivos y metadatos; preparar publicaciones |
| Revisor de derechos | Revisar evidencias y aprobar/rechazar publicación |
| Auditor | Consultar historial y evidencias según permisos |
| Oyente | Reproducir únicamente contenido publicado y autorizado |

Aplicar mínimo privilegio y separar carga, aprobación y publicación. No permitir que una misma cuenta eluda el flujo de aprobación.

## 3. Recursos de API propuestos

Prefijo: `/api/v1`.

- `GET /health` — estado del servicio y dependencias, sin revelar secretos.
- `GET/POST /artists` — perfiles artísticos.
- `GET/POST /releases` — lanzamientos y metadatos.
- `POST /assets` — carga controlada de audio/video.
- `GET /assets/{id}/integrity` — hash y estado de almacenamiento.
- `POST /rights/reviews` — enviar evidencia para revisión.
- `POST /releases/{id}/approve` — aprobación autorizada y auditada.
- `POST /releases/{id}/publish` — publicación local o envío a adaptador habilitado.
- `POST /releases/{id}/withdraw` — retiro auditado.
- `GET /playback/{asset_id}` — entrega de medios autorizados.

Estos son contratos propuestos, no endpoints existentes. Cada operación de escritura deberá autenticar, autorizar, validar esquema y registrar actor, fecha, objeto y resultado.

## 4. Modelo de almacenamiento

- Local: originales, derivados, metadatos, base de datos y logs con permisos restrictivos.
- Kubo IPFS opcional: contenido direccionado por CID y manifiestos. No fijar automáticamente datos personales, contratos privados ni material no autorizado.
- Base de datos: estados transaccionales de catálogo, derechos, publicaciones y revocaciones.
- Respaldo: copias cifradas y prueba periódica de restauración.

Mantener el CID separado de la autorización. Un CID no es un permiso de distribución.

## 5. Credencial y firma

La credencial debe declarar el sujeto artístico, entidad emisora, alcance, fecha de emisión, expiración, identificador de clave, evidencia referenciada y estado. Firmar una representación canónica con el mecanismo criptográfico soportado por Node Core OS. No crear un algoritmo criptográfico propio. Las claves privadas se mantienen fuera del catálogo, preferiblemente en un almacén protegido del sistema.

La credencial certifica únicamente las afirmaciones que el emisor haya verificado. No sustituye contratos, registros oficiales ni acuerdos de distribución.

## 6. Audio y video

Aceptar formatos mediante una lista explícita y validación por contenido, no solo por extensión. Limitar tamaño, duración, resolución y tasa de bits. Procesar medios en un entorno aislado; evitar ejecutar metadatos o archivos subidos. El reproductor debe soportar entrega progresiva/rangos HTTP y verificar integridad antes de publicar.

## 7. Distribución

Cada destino externo tendrá un adaptador independiente, credenciales almacenadas de forma segura, validación de metadatos, idempotencia, reintentos limitados, acuse de recibo y procedimiento de retiro. No asumir que Spotify, Apple Music u otro DSP ofrece una API abierta o que la cuenta de Trilema Records tiene acceso.

## 8. Seguridad y privacidad

- Loopback por defecto; no exposición pública automática.
- Autenticación local, control de sesión y protección CSRF cuando aplique.
- Validación de entradas, límites de carga y protección contra traversal.
- Separar secretos, documentos privados y metadatos públicos.
- Cifrar respaldos; definir retención y borrado.
- Auditoría append-only o con protección de integridad.
- Revisar licencias, consentimiento, derechos conexos y privacidad antes de publicación.

## 9. Pruebas requeridas

Pruebas unitarias de esquemas y firmas; integración con almacenamiento local; Kubo opcional con nodo de prueba; integridad tras alteración; permisos y roles; carga de archivos malformados; rangos HTTP; retiro y revocación; recuperación tras caída; y verificación de que el servidor no escucha fuera de loopback.

## 10. Condición de salida a producción

No declarar el servicio operativo hasta que exista implementación reproducible, pruebas CI aprobadas, documentación de instalación, revisión de seguridad, política de emisión/revocación, flujo de derechos probado y evidencia de distribución en cada destino anunciado.
