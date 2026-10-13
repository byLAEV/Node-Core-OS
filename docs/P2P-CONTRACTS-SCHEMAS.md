# Node Core OS P2P Contracts — esquema documental v0.1

- **Estado:** propuesta técnica para revisión; todavía no es código ejecutable.
- **Versión del protocolo:** `0.1.0`.
- **Modo inicial:** transparente y público para datos de prueba.
- **Alcance:** solicitudes, respuestas, propuestas, aceptaciones, evidencias y manifiesto de estado.
- **Compatibilidad:** no modifica ni reutiliza los formatos de HashPaper.

## 1. Reglas comunes

### 1.1 Codificación y representación

- Los documentos se representan como objetos JSON codificados en UTF-8.
- Los nombres de campos son sensibles a mayúsculas y minúsculas.
- Los campos obligatorios deben estar presentes.
- Los campos desconocidos se rechazarán en la primera versión, salvo que un esquema permita explícitamente extensiones.
- No se usarán números de punto flotante para cantidades de activos; se representarán como cadenas decimales validadas por el tipo de activo.
- Las fechas serán UTC en formato RFC 3339, por ejemplo `2026-10-12T12:00:00Z`.
- Cada documento incluye un campo `schema` con el identificador de tipo y versión.
- Un documento publicado será inmutable. Una corrección genera un nuevo documento que referencia el anterior.
- El CID identifica el contenido publicado; el ID lógico identifica el documento dentro del protocolo. No son equivalentes.

La implementación deberá serializar de manera determinista antes de publicar: UTF-8, claves de objeto ordenadas, separadores JSON compactos y sin valores no estándar como NaN o Infinity. Se deben añadir pruebas de bytes exactos antes de firmar documentos. La firma OpenPGP queda fuera de esta especificación documental inicial y se especificará en una fase posterior.

### 1.2 Identificadores y referencias

Los IDs serán cadenas con prefijo de tipo y sufijo único generado por la implementación, por ejemplo `request-<uuid>`, `response-<uuid>`, `proposal-<uuid>`, `acceptance-<uuid>` y `evidence-<uuid>`.

Las referencias a contenido publicado utilizarán CIDs reales devueltos por Node Core OS. Los ejemplos de esta especificación son ilustrativos y no deben usarse como CIDs.

### 1.3 Identidad de participante

`participant_id` identifica al participante según la política de identidad de P2P Contracts. En la primera fase de pruebas puede usar identificadores sintéticos como `node-demo-a`. Cuando se integren perfiles y firmas, se documentará por separado la relación entre participante, Peer ID y clave pública. Un perfil declarado no se etiquetará como identidad civil verificada.

## 2. Solicitud

Esquema: `node-core-p2p-contracts/request/1`.

Campos obligatorios:

| Campo | Tipo | Regla |
|---|---|---|
| `schema` | string | Exactamente `node-core-p2p-contracts/request/1`. |
| `request_id` | string | Único; prefijo `request-`. |
| `requester_id` | string | Identificador del participante que publica. |
| `created_at` | string | Fecha UTC RFC 3339. |
| `request_type` | string | Tipo de solicitud definido por el protocolo. |
| `title` | string | No vacío, longitud máxima definida por el validador. |
| `description` | string | Descripción pública no vacía. |
| `terms` | object | Condiciones explícitas, validadas según `request_type`. |
| `visibility` | string | En v0.1 solo se admite `public`. |
| `status` | string | Al crearla, `open`. |
| `previous_document_cid` | string o null | CID del documento previo si es una revisión; null para la primera versión. |

El estado actual de una solicitud se derivará de eventos/documentos publicados; no se debe reescribir el documento original para cambiar su estado. La primera versión puede cerrar o cancelar una solicitud mediante un documento de evento definido en la implementación; hasta que ese tipo de documento esté especificado, no se debe inventar una transición de cierre.

Ejemplo ilustrativo:

```json
{
  "schema": "node-core-p2p-contracts/request/1",
  "request_id": "request-00000000-0000-4000-8000-000000000001",
  "requester_id": "node-demo-a",
  "created_at": "2026-10-12T12:00:00Z",
  "request_type": "exchange",
  "title": "Solicitud ficticia de intercambio",
  "description": "Ejemplo para probar la publicación y trazabilidad.",
  "terms": {
    "asset": "BTC",
    "amount": "0.001",
    "network": "test-only"
  },
  "visibility": "public",
  "status": "open",
  "previous_document_cid": null
}
```

El ejemplo no ordena realizar una transacción real. `test-only` es una etiqueta descriptiva, no un mecanismo de seguridad por sí mismo.

## 3. Respuesta

Esquema: `node-core-p2p-contracts/response/1`.

Campos obligatorios:

- `schema`
- `response_id`
- `request_id`: debe apuntar a una solicitud existente y validada.
- `responder_id`
- `created_at`
- `response_type`: valor definido por el protocolo, inicialmente `message`, `offer` o `decline`.
- `message`: texto no vacío.
- `previous_document_cid`: CID anterior si se trata de una revisión; null en la primera respuesta.

Una respuesta no altera el documento de solicitud. Si propone condiciones concretas, debe enlazarse a una propuesta separada.

## 4. Propuesta

Esquema: `node-core-p2p-contracts/proposal/1`.

Campos obligatorios:

- `schema`
- `proposal_id`
- `request_id`
- `response_id` o null cuando la propuesta no nace de una respuesta
- `proposer_id`
- `created_at`
- `terms`: objeto con condiciones completas, no una descripción ambigua.
- `previous_proposal_cid`: null para la primera propuesta; CID de la versión anterior para una revisión.

Una revisión nueva no reemplaza la anterior. La aceptación debe señalar el CID exacto de la propuesta aceptada, no solo su ID lógico.

## 5. Aceptación

Esquema: `node-core-p2p-contracts/acceptance/1`.

Campos obligatorios:

- `schema`
- `acceptance_id`
- `proposal_id`
- `proposal_cid`: contenido exacto aceptado.
- `accepting_participant_id`
- `decision`: `accept` o `reject`.
- `created_at`
- `statement`: declaración explícita del participante.
- `signature_ref`: null en la fase documental sin firmas; deberá apuntar a una firma verificable cuando OpenPGP se integre.

Cada parte registra su propia decisión. Una aceptación de una parte no significa que todas las partes hayan aceptado, ni prueba ejecución o liquidación del acuerdo.

## 6. Evidencia de ejecución

Esquema: `node-core-p2p-contracts/evidence/1`.

Campos obligatorios:

- `schema`
- `evidence_id`
- `proposal_id`
- `proposal_cid`
- `created_at`
- `submitted_by`
- `evidence_type`: tipo explícito, por ejemplo `participant_statement`, `test_result` o `external_reference`.
- `verification_status`: inicialmente `unverified`; solo se usará `verified` cuando exista un procedimiento reproducible y su resultado se conserve.
- `description`
- `references`: lista de referencias CID o identificadores externos con tipo y contexto.

La aplicación no inferirá que una operación está confirmada a partir de una afirmación textual. La verificación de transacciones de redes externas queda fuera del primer alcance.

## 7. Manifiesto general de estado

Esquema: `node-core-p2p-contracts/manifest/1`.

Campos obligatorios:

- `schema`
- `application_id`: `node-core-os-p2p-contracts`.
- `application_version`
- `protocol_version`: `0.1.0`.
- `sequence`: entero positivo, comenzando en 1.
- `previous_manifest_cid`: null en el primer manifiesto.
- `update_manifest_cid`: CID del manifiesto de actualización de la aplicación si existe; null mientras no exista.
- `public_requests`: lista de objetos con `request_id` y `cid`.
- `published_evidence`: lista de objetos con `evidence_id` y `cid`.
- `publisher_id`
- `created_at`
- `signature_ref`: null antes de integrar firmas; la versión firmada deberá definir exactamente qué bytes se firman.

El manifiesto es un anuncio verificable del estado publicado y de necesidades públicas seleccionadas. No es votación, certificación de la veracidad de cada afirmación ni aprobación colectiva de contratos. Solo incluirá documentos que se hayan publicado correctamente y que los participantes estén autorizados a hacer públicos.

Los nodos generales de Node Core OS deben poder recuperar y conservar el manifiesto sin descargar todos los documentos operativos. Los nodos participantes pueden sincronizar los documentos adicionales que les correspondan.

## 8. Reglas de secuencia y conflictos

1. El primer manifiesto usa `sequence: 1` y `previous_manifest_cid: null`.
2. Cada nueva versión incrementa la secuencia en uno y apunta al CID exacto del manifiesto anterior.
3. La secuencia por sí sola no demuestra legitimidad; se valida la procedencia del publicador según la política que se implemente.
4. Dos manifiestos distintos con la misma secuencia y el mismo antecedente se reportan como conflicto.
5. No se elige silenciosamente una rama usando solo el timestamp.
6. Si no se puede consultar suficiente información para verificar el estado más reciente, la sincronización se marca parcial o pendiente.
7. Un manifiesto inválido no debe reemplazar el último manifiesto verificado localmente.

La política de autorización para publicar nuevas versiones debe definirse antes de implementar escritura concurrente. No se introduce un voto global de todos los nodos.

## 9. Estados de sincronización

La interfaz debe utilizar estados explícitos:

- `synced_verified`: las referencias requeridas se recuperaron y verificaron.
- `partial`: se recuperó solo una parte del contenido necesario.
- `pending_offline`: no hay conexión suficiente para comprobar el estado actual.
- `conflict`: se detectaron manifiestos incompatibles.
- `verification_error`: falla la integridad, la firma o la validación del esquema.

No declarar sincronización completa si el nodo no pudo verificar el estado más reciente según las fuentes que el protocolo haya definido.

## 10. Casos de prueba derivados

La implementación debe probar al menos:

1. Rechazar un documento con campo obligatorio ausente.
2. Rechazar un valor de `visibility` distinto de `public` en v0.1.
3. Rechazar una respuesta cuyo `request_id` no exista.
4. Rechazar una aceptación cuyo `proposal_cid` no coincida con el documento de propuesta recuperado.
5. Rechazar una revisión que no enlace con el antecedente declarado.
6. Rechazar un manifiesto que apunte a un CID ausente o cuyo documento no valide.
7. Detectar dos manifiestos diferentes con la misma secuencia y el mismo antecedente.
8. No marcar como verificada una evidencia declarativa.
9. Mantener el último manifiesto verificado cuando una actualización nueva sea inválida.
10. Probar la serialización determinista con un conjunto fijo de documentos y bytes esperados.
11. Comprobar que el contenido publicado no contiene claves privadas ni credenciales.
12. Verificar que las operaciones fallidas de Kubo no se presentan como publicación exitosa.

## 11. Política OpenPGP: importar claves existentes; no generar claves

**Requisito obligatorio de diseño:** la primera versión de P2P Contracts no generará claves privadas OpenPGP nuevas, ni Node Core OS ni la aplicación las crearán automáticamente.

### 11.1 Clave privada del usuario

- El usuario podrá importar una clave privada OpenPGP que ya posea.
- La importación debe ser una acción explícita del usuario, nunca automática.
- La clave privada y cualquier material secreto asociado se conservarán únicamente en el almacenamiento privado local con permisos restrictivos.
- La clave privada no se publicará en IPFS, manifiestos, solicitudes, registros, exportaciones de contactos ni mensajes.
- No se escribirá la clave privada en logs, mensajes de error ni archivos temporales sin protección.
- La aplicación no debe exigir que la clave privada se cargue o se guarde en texto claro persistente. Se debe evaluar el formato de importación, el descifrado de claves protegidas por contraseña y el almacenamiento seguro antes de implementar.
- Si el usuario no ha importado una clave privada, la aplicación no debe generar una en su lugar. Las funciones privadas que necesiten esa clave deben permanecer deshabilitadas y explicar cómo importar una clave existente.
- La exportación de una clave privada, si se ofrece en el futuro, requerirá una acción explícita y no forma parte de v0.1.

### 11.2 Contactos OpenPGP

El usuario podrá añadir contactos importando o pegando su **clave pública OpenPGP** existente. Cada contacto debe conservar como mínimo la clave pública original, su fingerprint calculado por la biblioteca OpenPGP seleccionada, una etiqueta local elegida por el usuario y la fecha de incorporación.

- La etiqueta del contacto es solo una etiqueta local, no una identidad civil verificada.
- La aplicación debe calcular y mostrar el fingerprint, y permitir que el usuario lo compare con el contacto por un canal independiente antes de confiar en él.
- Validar el formato de la clave y rechazar entradas inválidas. No confiar únicamente en el nombre, correo electrónico o etiqueta declarados dentro de la clave.
- El almacén de contactos es local por defecto. No publicar automáticamente claves públicas de contactos en manifiestos o en IPFS.
- El usuario podrá eliminar o marcar como no confiable un contacto. Las claves públicas conocidas no deben sustituirse silenciosamente.

### 11.3 Modo privado: cifrado OpenPGP obligatorio

Cuando el usuario elija **Privado**, el contenido de comunicación de P2P Contracts debe usar OpenPGP de extremo a extremo. No se permitirá un fallback silencioso a texto claro.

1. El usuario selecciona uno o más contactos destinatarios cuyas claves públicas ya se hayan importado y validado.
2. La aplicación construye el documento de comunicación privado.
3. El documento se cifra para la clave pública de cada destinatario previsto antes de cualquier publicación o transmisión.
4. Si se requiere acreditar la autoría, la aplicación firma el contenido con la clave privada previamente importada por el remitente. La firma se valida separadamente del cifrado.
5. Solo el paquete OpenPGP cifrado puede salir del almacenamiento privado hacia el transporte o el almacenamiento distribuido.
6. Si falta una clave pública de destinatario, el formato no es válido, el cifrado falla o la política de firma no se cumple, la operación se detiene y muestra un error. No enviar el contenido en claro.
7. Las respuestas privadas se cifran para las claves públicas de los destinatarios previstos. El remitente debe tener una clave privada importada si la política del mensaje requiere firma.
8. El destinatario debe descifrar localmente con una clave privada que ya controle. La aplicación no puede leer ni recuperar el contenido sin la clave correspondiente.

El cifrado a un destinatario utiliza su clave pública; la clave privada del remitente no sustituye la clave pública del destinatario. La firma de autoría, cuando se aplique, requiere la clave privada importada del remitente. Cifrado y firma son propiedades distintas y la interfaz debe indicarlas por separado.

### 11.4 Transporte y metadatos

- No guardar el texto en claro de mensajes privados en el manifiesto general, índices públicos, logs ni registros de depuración.
- No publicar el CID del texto en claro ni crear primero una copia pública del documento original.
- Cualquier documento enviado por IPFS debe cifrarse antes de añadirse a IPFS; el CID que se publique debe corresponder al paquete cifrado.
- Un manifiesto general puede anunciar solo la existencia de actividad privada mediante un identificador opaco y datos mínimos, si el usuario lo autoriza. No debe revelar el contenido, participantes, asunto ni referencias que permitan recuperar el texto en claro.
- Incluso el CID de un paquete cifrado y sus metadatos pueden filtrar correlaciones. Reducir esos datos y documentar la limitación.
- La opción pública sigue siendo deliberadamente transparente y no usa cifrado para ocultar su contenido. La selección de visibilidad debe mostrarse antes de publicar y confirmarse claramente.

### 11.5 Reglas de aceptación y pruebas

La implementación no se acepta si:

1. Genera una clave privada de forma automática o durante la instalación.
2. Envía en texto claro cualquier mensaje seleccionado como privado.
3. Sube contenido privado a IPFS antes de cifrarlo.
4. Guarda texto en claro privado en logs, manifiestos o índices públicos.
5. Envía un mensaje privado sin una clave pública válida para cada destinatario.
6. Sustituye silenciosamente una clave pública de contacto.
7. Presenta una etiqueta o un nombre de clave como identidad verificada.
8. Confunde cifrado con firma o con verificación de identidad.
9. Falla el cifrado y continúa el envío por una ruta pública.

Las pruebas deben usar claves de prueba creadas fuera de Node Core OS y almacenadas en fixtures de test no productivos. La aplicación de producción no generará claves nuevas. Las pruebas deben comprobar que solo se publica el paquete cifrado, que el texto original no aparece en archivos de salida ni logs y que una operación de cifrado fallida no transmite nada.

## 12. Decisiones que siguen pendientes

Antes de codificar los validadores se deben acordar:
- Los límites máximos de longitud y tamaño de cada documento.
- El catálogo inicial de `request_type`, `response_type` y `evidence_type`.
- La política de autorización de publicadores del manifiesto.
- El formato exacto de la firma y su canonicalización.
- La forma en que la aplicación recibe las instancias compartidas de almacenamiento y contenido del runtime.

La primera implementación debe mantener la biblioteca estándar de Python, si es suficiente para los esquemas y el almacenamiento local. OpenPGP se evaluará por separado y no se añadirá una dependencia criptográfica sin comprobar su compatibilidad y mantenimiento.
