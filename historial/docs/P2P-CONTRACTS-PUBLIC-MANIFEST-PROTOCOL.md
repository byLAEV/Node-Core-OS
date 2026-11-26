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

## 13. Ventana pública de propagación y receptor temporal (diseño actualizado)

Esta sección concreta el flujo previsto para la primera versión pública. Donde las secciones anteriores describan una única solicitud nueva por manifiesto, se entiende que el **manifiesto de lote puede agrupar varias solicitudes recibidas durante una misma ventana**. La secuencia identifica la etapa o lote de propagación, no una solicitud individual.

### 13.1 Principio de funcionamiento

Un nodo anuncia que necesita publicar una solicitud propia y, por ese motivo, se ofrece a recibir durante un intervalo las solicitudes de otros nodos. No es un coordinador permanente ni recibe autoridad general sobre la aplicación: su función corresponde únicamente a la ventana identificada por el preestado vigente.

El mensaje pequeño de propagación informa como mínimo:

- versión del protocolo;
- hash/CID del estado aceptado anterior;
- hash del preestado de la ventana;
- identificador técnico del nodo receptor propuesto;
- referencia a la identidad de Node Core OS asociada, sin afirmar que un perfil declarado sea una identidad criptográficamente verificada;
- inicio de la ventana y momento mínimo en que se habilita el envío de la solicitud propia;
- duración de ventana según las reglas del protocolo;
- identificador único del anuncio y estado de su aceptación.

El anuncio se propaga a los nodos activos. Los nodos comparan el anuncio con su manifiesto sincronizado y consultan a otros pares conocidos para confirmar que el mismo preestado y receptor están reconocidos. La aplicación solo muestra la ventana como aceptada cuando dispone de la evidencia de aceptación definida por el protocolo; conectarse a un nodo o recibir su anuncio no basta por sí solo.

### 13.2 Tiempo mínimo de propagación

Para el prototipo se propone una ventana mínima inicial de **600 segundos (10 minutos)**, configurable por versión del protocolo y usada como valor de prueba, no como constante criptográfica ni garantía de sincronización global.

Cuando el nodo receptor acepta el preestado, registra el inicio de la ventana y calcula `send_enabled_at = window_started_at + minimum_propagation_seconds`. Antes de ese momento, la interfaz mantiene deshabilitado el botón para enviar la solicitud propia. El temporizador no impide que el nodo reciba solicitudes de otros participantes durante la ventana.

La interfaz debe mostrar el tiempo restante y explicar por qué el botón está deshabilitado. Al alcanzar el momento mínimo, habilita el envío de la solicitud propia y permite cerrar la ventana conforme a la transición de estado del protocolo.

El timestamp sirve para controlar la experiencia y la regla temporal del protocolo, pero no prueba por sí solo el orden real de llegada ni que todos los nodos hayan recibido el anuncio. Las reglas deben definir la fuente del tiempo, la tolerancia de reloj y qué ocurre si el nodo se reinicia o queda desconectado. El cierre debe conservar la hora declarada y el estado previo para poder verificarlos.

### 13.3 Envío de solicitudes durante la ventana

Mientras la ventana está abierta, un nodo que desea enviar una solicitud:

1. lee el manifiesto local sincronizado;
2. comprueba que el preestado y el receptor anunciados siguen siendo los reconocidos;
3. consulta a otros nodos activos si dispone de fuentes adicionales;
4. crea su solicitud usando el formulario público preestablecido;
5. envía la solicitud al receptor de la ventana vigente;
6. guarda el recibo de recepción y la referencia de la solicitud.

El contenido del mensaje de propagación debe ser pequeño. Las solicitudes se transmiten por separado y se agrupan por referencia en el lote; no se requiere retransmitir el historial completo en cada mensaje. La solicitud incluye su propio identificador, el preestado al que pertenece y los campos públicos que el usuario autorizó.

### 13.4 Lote y cierre

El receptor conserva las solicitudes recibidas durante la ventana y sus recibos. Al habilitarse y enviar su propia solicitud, esta también se incorpora al lote. El receptor crea un manifiesto inmutable de lote con:

- hash/CID del estado padre y del preestado;
- identificador del receptor de la ventana;
- inicio y cierre declarados de la ventana;
- referencias ordenadas a las solicitudes recibidas y a la solicitud propia;
- cantidad de solicitudes;
- referencias a los recibos disponibles;
- versión del protocolo y hash del contenido canónico.

El manifiesto se calcula sobre una serialización canónica y se publica mediante la capa de contenido existente. Los nodos que lo verifican comprueban las referencias y recalculan el hash. La lista ordenada del lote no debe sobrescribir manifiestos anteriores.

Para mantener el primer prototipo simple, la ventana se cierra cuando vence el mínimo temporal y el nodo envía su propia solicitud; después publica el manifiesto candidato del lote. El siguiente preestado no se considera vigente hasta que el manifiesto de transición que cierra el lote ha sido aceptado conforme a la regla pública definida. Las solicitudes tardías se asignan a la ventana siguiente, no se añaden retroactivamente al lote cerrado.

### 13.5 Siguiente receptor

Tras cerrar y aceptar el lote, otro nodo que también necesite enviar una solicitud puede anunciar el siguiente preestado desde el nuevo estado aceptado. La red repite el mismo procedimiento con un receptor temporal distinto. El nodo anterior no conserva el rol para ventanas futuras salvo que vuelva a participar y su propuesta sea aceptada de nuevo.

Los nodos generales conservan los manifiestos de propagación y de lote necesarios para descubrir el receptor vigente y las solicitudes públicas. Pueden recuperar los documentos completos bajo demanda según la política de almacenamiento, sin tener que descargar todos los expedientes operativos de P2P Contracts.

### 13.6 Pruebas específicas

Antes de integrar la ventana en la red, probar localmente:

- el botón de envío propio permanece deshabilitado antes de los 600 segundos;
- las solicitudes entrantes se reciben mientras el botón propio está deshabilitado;
- al vencer el intervalo, el botón se habilita y la solicitud del receptor entra en el mismo lote;
- el manifiesto del lote contiene las referencias esperadas, en orden determinista;
- un nodo remitente recibe un recibo con identificador de solicitud y preestado;
- una solicitud enviada después del cierre se asigna a la siguiente ventana;
- reiniciar la aplicación conserva o reconstruye el estado del temporizador de forma explícita y comprobable;
- los nodos verifican el manifiesto del lote sin confiar únicamente en la palabra del receptor;
- la transición al siguiente preestado solo ocurre después de aceptar el cierre del lote;
- el flujo utiliza identidades de prueba y no modifica HashPaper ni habilita funciones privadas.

Esta sección describe el comportamiento previsto; todavía no es una implementación funcional. Antes de codificar, deben confirmarse las interfaces reales de red, almacenamiento y contenido de Node Core OS, y concretarse una regla mínima de aceptación compatible con las capacidades criptográficas que realmente existen.
