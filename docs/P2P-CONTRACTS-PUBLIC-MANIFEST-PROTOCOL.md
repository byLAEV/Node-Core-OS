# Node Core OS P2P Contracts — protocolo público de manifiestos enlazados (borrador v0.1)

## 1. Alcance

Este documento especifica el primer flujo público de P2P Contracts. No implementa ni habilita funciones privadas, OpenPGP, importación de claves privadas ni cifrado privado. La modalidad privada queda aplazada hasta que la modalidad pública esté implementada y probada y el usuario autorice esa fase.

El objetivo es que un nodo pueda comprobar criptográficamente que una nueva versión del estado de P2P Contracts deriva de una versión anterior conocida y que la nueva solicitud fue añadida sin alterar las solicitudes históricas. También define cómo dos nodos independientes pueden validar y atestiguar el mismo candidato antes de que se propague a un tercer nodo.

## 2. Separar identidad, solicitud, manifiesto de estado y atestaciones

No se recomienda editar en el sitio un único archivo mutable que contenga todas las solicitudes. En su lugar se publican documentos inmutables enlazados:

1. **Solicitud**: documento independiente con el contenido de una solicitud pública y los atributos de identidad que el usuario autorizó expresamente a publicar.
2. **Manifiesto candidato**: nuevo estado que referencia el manifiesto anterior y añade exactamente una solicitud nueva.
3. **Atestación de validación**: documento firmado por un nodo validador que confirma que verificó el candidato y que el nuevo estado es una extensión válida del padre.
4. **Manifiesto aceptado**: el candidato con las atestaciones necesarias, publicado como versión aceptada del estado actual.

Los documentos anteriores nunca se sobrescriben. Una nueva versión crea un documento nuevo y conserva la referencia a su padre. Esta estructura es una cadena de manifiestos enlazados por hashes/CID; por sí sola no es una blockchain con consenso distribuido completo.

## 3. Consentimiento de identidad al abrir la aplicación

Al iniciar P2P Contracts, la aplicación debe mostrar qué campos de la identidad local de Node Core OS se proponen incluir en solicitudes públicas. El usuario debe aceptar expresamente ese uso antes de entrar en las funciones de creación de solicitudes.

- No asumir que aceptar usar la aplicación equivale a consentir publicar todos los datos personales sin mostrarlos.
- Mostrar los campos exactos que se publicarán y permitir confirmar la publicación.
- No incluir contraseñas, secretos, material de autenticación ni datos internos que no sean atributos públicos de identidad.
- Registrar en el documento de solicitud la versión del esquema de identidad y la lista de campos autorizados.
- Si el usuario no acepta, no crear ni publicar solicitudes con esos datos.

Este requisito no añade funciones privadas; es un control de publicación para la modalidad pública transparente.

## 4. Forma lógica de una solicitud pública

Cada solicitud es un documento separado e inmutable. Campos mínimos recomendados:

- `schema`: identificador y versión del esquema.
- `request_id`: identificador único.
- `created_at`: fecha informativa UTC; no se utiliza por sí sola para ordenar consenso.
- `author_node_id`: identificador del nodo que propone la solicitud.
- `identity_disclosure`: campos de identidad expresamente autorizados.
- `request_type`: tipo de necesidad o intercambio.
- `request_body`: contenido legible públicamente.
- `previous_request_ref`: opcional; solo para relacionar solicitudes del mismo autor si el protocolo lo necesita.

La solicitud se serializa de forma canónica antes de calcular su SHA-256 y CID. El hash identifica los bytes canónicos exactos; el CID permite recuperar el objeto cuando está disponible. No se debe confiar en una representación JSON con orden de claves o espacios arbitrarios. La implementación elegirá una regla de canonicalización documentada y probada antes de firmar o calcular hashes.

## 5. Manifiesto de estado candidato

Cada versión del manifiesto contiene al menos:

- `schema`: esquema y versión del protocolo.
- `application`: `Node Core OS P2P Contracts`.
- `sequence`: entero que aumenta exactamente en uno desde el padre.
- `previous_manifest_cid`: CID del manifiesto padre; vacío solo para el manifiesto génesis.
- `previous_manifest_hash`: hash del contenido canónico del padre.
- `new_request_cid`: referencia a la única solicitud añadida en esta versión.
- `request_count`: cantidad total de solicitudes referenciadas.
- `requests_root`: raíz/hash calculado sobre la lista ordenada de referencias de solicitudes.
- `author_node_id`: nodo que propone el candidato.
- `created_at`: dato informativo, no una prueba de orden.
- `protocol_version`: versión de reglas de validación.

El manifiesto debe permitir reconstruir la lista completa y ordenada de solicitudes, o referenciar un índice inmutable verificable. Para la primera implementación conviene preferir una lista ordenada de CIDs simple y comprobable antes que introducir un árbol de Merkle complejo. Si se utiliza `requests_root`, su algoritmo exacto y el orden de entrada deben definirse y probarse.

## 6. Reglas que debe comprobar un validador

Un nodo validador no debe aceptar el candidato por el mero hecho de recibirlo. Debe recuperar y comprobar:

1. El manifiesto padre existe y su contenido coincide con `previous_manifest_cid` y `previous_manifest_hash`.
2. La secuencia candidata es exactamente `parent.sequence + 1`.
3. La lista de solicitudes del candidato contiene todas las referencias del padre en el mismo orden, sin cambios ni eliminaciones.
4. Se añadió exactamente una referencia nueva, `new_request_cid`, al final de la lista.
5. `request_count` es exactamente el contador del padre más uno y coincide con la longitud real de la lista.
6. El contenido de la nueva solicitud se recupera y su hash/CID coincide con la referencia.
7. El esquema, los campos obligatorios y los tipos de datos son válidos.
8. La identidad de autoría y la firma del candidato se validan con el mecanismo de identidad criptográfica que esté efectivamente implementado y aprobado. No se deben inventar firmas ni tratar un nombre o Peer ID como firma.
9. No se ha observado ya una versión distinta para el mismo padre y la misma secuencia. Si existen candidatos en conflicto, marcarlos como bifurcación; no elegir uno solo por timestamp.
10. La política de consentimiento para los atributos publicados se cumplió.

Si una sola comprobación falla, el validador rechaza el candidato y no lo propaga como estado aceptado.

## 7. Dos nodos validan; un tercero verifica

Flujo propuesto:

1. Nodo A crea la solicitud pública y el manifiesto candidato con referencia al padre.
2. Nodo A distribuye el candidato a Nodo B para validación.
3. Nodo B recupera el padre y la solicitud, ejecuta todas las comprobaciones de la sección 6 y compara el historial anterior con el candidato.
4. Si el candidato es una extensión válida, Nodo B crea una atestación que incluye el hash exacto del candidato, el CID del padre, la secuencia, el resultado de validación y el identificador del validador. La atestación debe estar firmada por un mecanismo criptográfico realmente implementado.
5. Nodo A publica el candidato junto con la atestación de B y cualquier prueba de autoría requerida por el protocolo.
6. Nodo C recupera el candidato, el padre, la solicitud y la atestación; vuelve a ejecutar las comprobaciones y valida que la atestación de B corresponde exactamente al hash candidato que recibió.
7. Nodo C solo marca el candidato como validado según esta política si las pruebas son correctas. Si el hash cambia un solo byte, el hash del documento cambia y la atestación deja de coincidir.

**Importante:** que A y B coincidan no constituye por sí solo consenso global de toda la red ni impide que A y B coludan. Es una política mínima de dos participantes para detectar alteraciones accidentales y hacer que un tercero verifique una validación independiente. Para resistencia Sybil o consenso fuerte se necesita una política adicional de membresía, quórum y resolución de bifurcaciones, no incluida en v0.1. No se debe afirmar “consenso de toda la red” solo por dos firmas.

## 8. Cómo se demuestra que el historial no fue alterado

La cadena se valida desde una raíz conocida:

- Cada manifiesto referencia el CID/hash de su padre.
- El validador recupera el padre y recalcula su hash desde los bytes canónicos.
- Compara todas las solicitudes del padre con el prefijo de la lista candidata.
- Solo permite una nueva solicitud al final.
- Recalcula el hash del candidato y verifica que la atestación firmada se refiere a ese hash exacto.
- El tercer nodo repite las comprobaciones de forma independiente.

Un hash por sí solo no demuestra quién creó un documento ni que su contenido sea verdadero. La firma identifica el control de una clave criptográfica, y el validador verifica las reglas del protocolo. La identidad civil requiere un mecanismo aparte.

La inmutabilidad también depende de conservar una referencia de confianza al manifiesto génesis o a una cabeza de cadena aceptada previamente. Un nodo recién instalado que solo recibe una cadena de un único par no puede detectar siempre que ese par le ocultó una bifurcación alternativa. Se debe comparar la cabeza conocida con referencias obtenidas de más de un nodo independiente cuando estén disponibles.

## 9. Bifurcaciones y solicitudes simultáneas

Si dos nodos crean candidatos diferentes que comparten el mismo padre y secuencia, se produce una bifurcación. No se deben fusionar ni sobrescribir silenciosamente los candidatos.

Para v0.1:

- conservar ambos candidatos y sus atestaciones como evidencia;
- marcar la cabeza de estado como `CONFLICT` o `FORK_DETECTED`;
- no declarar una sincronización completa mientras la política de resolución no determine una cabeza;
- usar una regla de resolución explícita en una fase posterior (por ejemplo, quórum de validadores identificados y una elección determinista);
- no usar solo el timestamp, el orden de llegada o el CID lexicográficamente menor para afirmar que existe consenso.

Para la primera prueba de funcionamiento puede serializarse la creación de solicitudes: solo un candidato por cabeza de manifiesto puede avanzar a la vez. La concurrencia se implementará después de probar la cadena básica.

## 10. Manifiestos sincronizados en los nodos generales

Cada nodo general de Node Core OS conservará localmente los manifiestos de estado de P2P Contracts que reciba y pueda validar, dentro de la carpeta de manifiestos sincronizados que determine la arquitectura existente de Node Core OS.

El nodo general debe distinguir:
- `RECEIVED`: bytes recibidos, aún no validados;
- `VALID`: contenido y cadena verificados;
- `ATTESTED`: tiene la atestación requerida por la política;
- `CURRENT`: es la cabeza aceptada conocida;
- `CONFLICT`: hay más de un candidato incompatible;
- `PARTIAL`: faltan el padre, la solicitud o una atestación necesaria.

No se debe inventar una ruta local hasta inspeccionar el código actual de Node Core OS y reutilizar su gestor de almacenamiento. Guardar un CID no equivale a recuperar el objeto ni a fijarlo en Kubo. Las operaciones de pinning y sincronización deben integrarse con las interfaces existentes, no duplicarlas.

Los nodos generales pueden conservar el manifiesto de estado y los objetos públicos que el protocolo requiera para verificarlo. La decisión de descargar o fijar cada solicitud completa se debe definir explícitamente; no debe suponerse que el manifiesto por sí solo contiene todos los datos referenciados.

## 11. Pruebas mínimas antes de la propagación

- Un candidato válido con exactamente una solicitud añadida se acepta.
- Si se altera una solicitud histórica, la validación falla.
- Si se elimina, reordena o reemplaza una referencia anterior, falla.
- Si se cambia un byte del padre o del candidato, el CID/hash o la atestación ya no coincide.
- Si la secuencia no es padre + 1, falla.
- Si falta el padre o la solicitud, el estado es `PARTIAL`, no `CURRENT`.
- Si falta la atestación requerida o su firma no es válida, no se acepta según la política.
- Si dos candidatos comparten padre y secuencia, se detecta y conserva el conflicto.
- Un tercer nodo que no participó en la creación vuelve a verificar el historial y las atestaciones.
- El rechazo no propaga el candidato como aceptado.
- El flujo público funciona sin OpenPGP privado ni claves privadas nuevas.
- HashPaper no se modifica.

## 12. Límites y siguiente paso

Este documento es una especificación de diseño, no código ejecutable ni una afirmación de que el consenso ya existe. Antes de programar se debe auditar cómo se identifican y autentican actualmente los nodos, cómo se guardan los manifiestos sincronizados y qué interfaz de Node Core OS se utiliza para recuperar y fijar contenido IPFS.

Orden de implementación recomendado:

1. Probar canonicalización, hashes y validación de esquemas localmente.
2. Implementar documentos de solicitud y manifiesto inmutable.
3. Implementar la comprobación de extensión append-only.
4. Definir y probar la atestación criptográfica con las capacidades de identidad existentes; no crear claves nuevas sin decisión explícita.
5. Simular tres nodos y un nodo malicioso que altera el historial.
6. Integrar almacenamiento local y Kubo/IPFS.
7. Probar sincronización, conflictos y recuperación.
8. Mantener OpenPGP privado aplazado.

