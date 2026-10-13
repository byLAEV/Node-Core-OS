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

## 11. Alcance de la versión inicial y política OpenPGP futura

### 11.1 Versión inicial: solo modo público

**La primera versión funcional de P2P Contracts implementará únicamente la modalidad pública y transparente.** Primero debe funcionar y superar pruebas la creación de solicitudes, respuestas, propuestas, aceptaciones, evidencias, publicación mediante las interfaces existentes de Node Core OS y trazabilidad entre nodos.

- No habrá selector funcional de modo privado en esta primera versión.
- No se integrará OpenPGP como función de comunicación en la primera versión.
- No se solicitará ni se importará una clave privada para utilizar las funciones públicas.
- No se generarán claves OpenPGP nuevas.
- La opción privada solo se diseñará e implementará en una fase posterior, después de validar la modalidad pública y con autorización explícita para comenzar esa fase.

La modalidad pública debe mostrar claramente que los documentos y datos incluidos se publicarán abiertamente. Usar datos ficticios de prueba y no publicar secretos, credenciales ni datos personales reales.

### 11.2 Requisito para una futura modalidad privada

Cuando el usuario autorice desarrollar la modalidad privada, P2P Contracts **no generará claves privadas OpenPGP**, ni durante la instalación ni durante el uso. El usuario aportará las claves que ya posee.

La opción preferida para la primera iteración privada será pedir al usuario que introduzca o cargue su clave privada existente cada vez que una operación requiera usarla, sin conservarla de forma persistente. El material secreto deberá mantenerse en memoria solo durante el tiempo estrictamente necesario y liberarse al terminar la operación, en la medida que lo permita el runtime. No debe copiarse a logs, archivos temporales, manifiestos, contactos ni almacenamiento distribuido.

Antes de adoptar ese método, se verificará si la biblioteca OpenPGP elegida puede procesar una clave importada de forma temporal, cómo gestiona las copias en memoria y cómo solicita la contraseña de una clave privada protegida. No se prometerá borrado perfecto de memoria que el lenguaje o la biblioteca no puedan garantizar.

Si una clave privada está protegida por contraseña, la contraseña también se solicitará de forma segura y no se almacenará en logs ni en configuración. Si la clave no se puede importar o desbloquear, la operación se detiene.

Un fingerprint o hash de una clave privada **no sustituye la clave privada** y no permite firmar ni descifrar. El fingerprint sirve para identificar o comparar una clave; almacenar únicamente ese valor no habilita ninguna operación criptográfica.

No se implementará almacenamiento persistente de claves privadas en la primera versión privada sin una decisión de diseño posterior y explícita. La aplicación tampoco impondrá un mecanismo de permisos de exportación como garantía absoluta: en un dispositivo controlado por el usuario no se puede asegurar que una clave que se ha introducido sea técnicamente imposible de copiar. El objetivo inicial es no almacenarla y reducir su exposición.

### 11.3 Contactos OpenPGP en la futura modalidad privada

Cuando se autorice esa fase, el usuario podrá importar las claves públicas OpenPGP existentes de sus contactos. Cada contacto conservará localmente, por defecto, la clave pública, el fingerprint calculado por la biblioteca, una etiqueta local y la fecha de incorporación.

- Validar el formato de la clave pública y mostrar su fingerprint.
- Permitir al usuario compararlo por un canal independiente antes de confiar en el contacto.
- No publicar automáticamente claves públicas de contactos en manifiestos o en IPFS.
- No confiar únicamente en el nombre, correo electrónico o etiqueta declarados en la clave.
- No sustituir silenciosamente una clave ya registrada.

La etiqueta del contacto no es una identidad civil verificada.

### 11.4 Reglas de la futura modalidad privada

Cuando esa fase sea autorizada, seleccionar **Privado** deberá significar cifrado OpenPGP obligatorio de extremo a extremo, sin fallback a texto claro:

1. Seleccionar destinatarios con claves públicas importadas y validadas.
2. Construir el documento privado.
3. Cifrarlo para las claves públicas de los destinatarios antes de transmitirlo o añadirlo a IPFS.
4. Si se exige acreditar la autoría, firmar usando la clave privada existente que el remitente aporte para esa operación.
5. Enviar únicamente el paquete cifrado. Si falta una clave, la clave no puede usarse o el cifrado falla, detener el envío.
6. El destinatario descifra localmente con su propia clave privada existente.

El cifrado para el destinatario usa su clave pública. La firma del remitente usa la clave privada del remitente. Son operaciones distintas; una no reemplaza a la otra.

El texto en claro no debe aparecer en manifiestos generales, índices públicos, logs, archivos temporales sin protección ni contenido publicado en IPFS. Los metadatos y los CIDs cifrados también pueden revelar correlaciones y deberán minimizarse.

### 11.5 Pruebas obligatorias antes de habilitar la modalidad privada

La futura implementación privada no se aceptará si:

1. Genera claves privadas automáticamente.
2. Persiste la clave privada del usuario cuando se haya elegido el diseño de uso temporal.
3. Usa un fingerprint/hash como si fuera una clave privada operativa.
4. Envía contenido en claro cuando el usuario ha seleccionado privado.
5. Publica el documento original en IPFS antes de cifrarlo.
6. Continúa enviando si falla la importación, el desbloqueo, la firma requerida o el cifrado.
7. Guarda claves o contenido privado en logs, manifiestos o índices públicos.
8. Sustituye silenciosamente una clave pública de contacto.
9. Confunde cifrado, firma e identidad verificada.

Las pruebas usarán claves de prueba creadas fuera de Node Core OS y solo en fixtures no productivos. La aplicación de producción no generará claves. Se verificará que el envío fallido no transmite nada y que el contenido en claro no aparece en los archivos de salida.

## 12. Decisiones que siguen pendientes

Antes de codificar los validadores se deben acordar:
- Los límites máximos de longitud y tamaño de cada documento.
- El catálogo inicial de `request_type`, `response_type` y `evidence_type`.
- La política de autorización de publicadores del manifiesto.
- El formato exacto de la firma y su canonicalización.
- La forma en que la aplicación recibe las instancias compartidas de almacenamiento y contenido del runtime.

La primera implementación debe mantener la biblioteca estándar de Python, si es suficiente para los esquemas y el almacenamiento local. OpenPGP se evaluará por separado y no se añadirá una dependencia criptográfica sin comprobar su compatibilidad y mantenimiento.
