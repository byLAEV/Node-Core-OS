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

## 11. Decisiones que siguen pendientes

Antes de codificar los validadores se deben acordar:
- Los límites máximos de longitud y tamaño de cada documento.
- El catálogo inicial de `request_type`, `response_type` y `evidence_type`.
- La política de autorización de publicadores del manifiesto.
- El formato exacto de la firma y su canonicalización.
- La forma en que la aplicación recibe las instancias compartidas de almacenamiento y contenido del runtime.

La primera implementación debe mantener la biblioteca estándar de Python, si es suficiente para los esquemas y el almacenamiento local. OpenPGP se evaluará por separado y no se añadirá una dependencia criptográfica sin comprobar su compatibilidad y mantenimiento.
