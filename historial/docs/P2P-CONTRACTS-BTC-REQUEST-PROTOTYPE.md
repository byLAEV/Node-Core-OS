# P2P Contracts: primera prueba de solicitud BTC

## Estado

Prototipo local de desarrollo. El código inicial incluye un formulario de intercambio BTC por otro activo, un manifiesto local encadenado por hashes, registros de evidencia y búsqueda por ID. No se declara implementada la propagación entre nodos ni la publicación en IPFS.

## Solicitud de intercambio

El formulario solicita:
- Cantidad de BTC que ofrece el usuario.
- Código del activo que desea recibir.
- Cantidad del activo solicitado.
- Red del activo, cuando corresponda.
- Descripción pública de condiciones.
- Uno o más métodos de contacto: correo, teléfono, clave pública PGP, oficina, protocolo externo u otro.
- Identificador técnico y direcciones del nodo obtenidos de Kubo.
- Campos del perfil de identidad local, mostrados antes de pedir consentimiento para incluirlos.

Las cantidades se guardan como cadenas decimales y se validan sin usar coma flotante. BTC debe ser positivo, no puede tener más de ocho decimales y el activo solicitado debe ser distinto de BTC.

Una entrada de contacto de tipo PGP solo admite una clave pública armada y rechaza explícitamente un bloque de clave privada.

## Consentimiento e identidad

El perfil local es una declaración y no equivale a identidad civil verificada. Los campos personales se precargan, se muestran al usuario y solo se incorporan si el usuario acepta y selecciona los campos. El identificador de perfil no se publica si no se autorizan datos de identidad.

El nodo técnico se incluye en la solicitud local. El usuario debe revisar los identificadores y direcciones antes de confirmar la creación. No se incluyen contraseñas ni claves privadas.

## Documentos e integridad

La solicitud tiene su propio ID y hash SHA-256 calculado sobre JSON canónico UTF-8 con claves ordenadas y separadores compactos. El manifiesto mantiene una secuencia, el hash del manifiesto anterior y referencias a las solicitudes y evidencias conocidas. Cada modificación crea un manifiesto nuevo; no se sobrescribe el manifiesto anterior.

La cabecera local apunta al manifiesto actual y permite comprobar su hash. Esta comprobación detecta alteraciones accidentales o incoherencias locales, pero no demuestra por sí sola consenso de red ni una firma de identidad.

## Evidencia y búsqueda

La aplicación puede crear evidencia de tipo respuesta, resultado de intercambio o seguimiento. Cada evidencia referencia el ID de la solicitud, contiene una declaración del informante y se marca inicialmente como self_reported_unverified.

La búsqueda por ID consulta el manifiesto local y carga las evidencias asociadas. Si no hay un resultado final registrado, la solicitud se muestra como abierta. Los resultados finales previstos son:
- exchange_completed
- not_completed
- cancelled
- disputed

Los eventos response_received, offer_received y no_response pueden registrarse sin cerrar automáticamente la solicitud. Un resultado final es un estado declarado, no una verificación independiente de una transacción.

## Persistencia y límite de red

Los documentos se guardan bajo la raíz local de almacenamiento de Node Core OS, dentro de p2p_contracts. El prototipo no publica documentos en IPFS ni los propaga a otros nodos. La etiqueta LOCAL_ONLY debe mostrarse hasta que se implemente y pruebe el transporte y la publicación de manifiestos.

## Pruebas

La suite inicial verifica cantidades, activo solicitado, creación de solicitud, consentimiento de identidad, incorporación de evidencia, consulta por ID y detección de alteración del manifiesto. Debe ejecutarse desde la raíz del repositorio con:

    python -m unittest applications.p2p_contracts.tests.test_service

No declarar las pruebas como aprobadas hasta ejecutarlas en un entorno real.
