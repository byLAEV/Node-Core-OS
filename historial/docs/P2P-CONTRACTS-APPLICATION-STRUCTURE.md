# Node Core OS P2P Contracts — estructura de aplicación propuesta

Estado: diseño para revisión; todavía no es código ejecutable.

## 1. Objetivo de la primera versión

Construir una aplicación terminal integrada con Node Core OS que permita crear solicitudes públicas mediante un formulario, anunciar una ventana temporal de recepción, recibir varias solicitudes pequeñas de otros nodos y publicar un manifiesto inmutable del lote. La aplicación usa el almacenamiento local y las interfaces de contenido/Kubo que ya existen en Node Core OS.

La primera versión es pública y transparente. No incorpora modo privado, OpenPGP ni generación de claves. HashPaper permanece sin cambios y fuera del alcance de esta aplicación.

## 2. Reglas de funcionamiento

1. El nodo que anuncia una ventana lo hace porque también necesita enviar una solicitud propia.
2. El anuncio identifica el estado padre, el preestado, el nodo receptor, la duración de la ventana y la hora a partir de la cual se habilita el envío de la solicitud propia.
3. La propuesta de receptor se publica como un mensaje pequeño, separado del contenido de las solicitudes.
4. Los nodos consultan el manifiesto sincronizado y pueden contrastar el anuncio con otros nodos conocidos.
5. Mientras el temporizador está activo, el receptor puede recibir solicitudes de otros nodos, pero su botón para enviar la solicitud propia permanece deshabilitado.
6. Valor inicial de prueba: 600 segundos. Debe estar configurado como parámetro versionado, no repetido como número mágico por el código.
7. Las solicitudes recibidas se validan con un esquema común y se guardan localmente. El remitente recibe un recibo con el ID de solicitud y el preestado.
8. Al cerrar la ventana, la solicitud propia del receptor se agrega al mismo lote y se genera un manifiesto inmutable con referencias ordenadas.
9. El siguiente preestado solo entra en vigor cuando el manifiesto de cierre pasa las comprobaciones de aceptación definidas para el prototipo.
10. Las solicitudes que llegan después del cierre se asignan a la ventana siguiente; nunca se modifica retroactivamente un lote cerrado.

## 3. Estructura de módulos propuesta

La estructura final debe seguir el patrón real de las aplicaciones existentes en el repositorio. Esta es la separación lógica prevista, no una afirmación de que estos archivos ya existan:

```text
applications/
└── p2p_contracts/
    ├── README.md
    ├── VERSION
    ├── main.py
    ├── p2p_contracts/
    │   ├── __init__.py
    │   ├── cli.py
    │   ├── config.py
    │   ├── schemas.py
    │   ├── canonical_json.py
    │   ├── hashing.py
    │   ├── request_service.py
    │   ├── propagation_service.py
    │   ├── window_service.py
    │   ├── batch_service.py
    │   ├── manifest_service.py
    │   ├── receipt_service.py
    │   ├── identity_consent.py
    │   ├── storage_adapter.py
    │   ├── content_adapter.py
    │   ├── network_adapter.py
    │   └── errors.py
    └── tests/
        ├── test_schemas.py
        ├── test_canonical_json.py
        ├── test_hashing.py
        ├── test_window_service.py
        ├── test_request_service.py
        ├── test_batch_service.py
        ├── test_manifest_service.py
        ├── test_storage_adapter.py
        ├── test_content_adapter.py
        └── test_three_node_flow.py
```

### Responsabilidad de cada módulo

- `main.py`: punto de entrada de la aplicación, siguiendo el patrón real de las aplicaciones integradas.
- `cli.py`: menú de terminal, formulario y estado visible del temporizador.
- `config.py`: parámetros versionados, incluido el mínimo de propagación; sin constantes duplicadas.
- `schemas.py`: validación estricta de mensajes de propagación, solicitudes, recibos, lotes y manifiestos.
- `canonical_json.py`: representación determinista del contenido antes de calcular el hash.
- `hashing.py`: cálculo y comprobación de SHA-256 sobre bytes canónicos.
- `request_service.py`: creación y validación local de solicitudes públicas.
- `propagation_service.py`: anuncio de receptor y consulta del estado conocido.
- `window_service.py`: estados de ventana y cálculo de `send_enabled_at`.
- `batch_service.py`: recopilación de referencias, orden determinista y cierre del lote.
- `manifest_service.py`: creación y verificación de manifiestos inmutables enlazados al padre.
- `receipt_service.py`: recibos de recepción para que cada remitente pueda comprobar qué solicitud envió.
- `identity_consent.py`: muestra los campos de identidad que se publicarían y registra el consentimiento expreso; no convierte un perfil declarado en identidad criptográficamente verificada.
- `storage_adapter.py`: adapta las operaciones al `StorageManager` existente; no inventa otra raíz de almacenamiento.
- `content_adapter.py`: adapta publicación, recuperación y pinning al `ContentManager` existente y comprueba sus resultados.
- `network_adapter.py`: encapsula el transporte de mensajes entre nodos. No debe asumir que la conectividad básica de Kubo es mensajería de aplicación.
- `errors.py`: errores explícitos y estados de operación; evita reportar éxito si una etapa falló.

## 4. Estados del protocolo

### Ventana de recepción

- `PROPOSED`: anuncio creado, todavía no reconocido.
- `PROPAGATING`: anuncio distribuido y consultado.
- `ACCEPTED`: se cumple la regla de aceptación del prototipo.
- `RECEIVING`: se reciben solicitudes durante la ventana.
- `WAITING_FOR_SEND_TIME`: el receptor todavía no puede enviar su propia solicitud.
- `READY_TO_SEND`: venció el mínimo temporal.
- `CLOSING`: se prepara el lote.
- `FINALIZED`: manifiesto de lote aceptado.
- `INCOMPLETE`: faltan datos o no se pudo confirmar la publicación.

### Solicitud

- `DRAFT`
- `VALIDATED`
- `SENT`
- `RECEIPTED`
- `INCLUDED_IN_BATCH`
- `REJECTED`

Los estados deben validarse mediante transiciones explícitas; no aceptar cualquier cambio de texto.

## 5. Formatos mínimos

### Anuncio de ventana

Debe incluir esquema/versión, ID único del anuncio, hash/CID del estado padre, hash del preestado, ID técnico del nodo receptor, referencia de identidad, inicio declarado, duración, `send_enabled_at` y versión de reglas. El mensaje no contiene el expediente de una solicitud.

### Solicitud

Debe incluir esquema, ID único, referencia al preestado, ID técnico del remitente, campos de identidad que el usuario autorizó, tipo de solicitud, contenido del formulario y hora informativa. El formulario se valida antes de transmitirlo.

### Recibo

Debe referenciar el ID y hash de la solicitud, el preestado, el receptor y la hora de recepción declarada. Un recibo prueba que un receptor emitió esa confirmación; no prueba por sí solo que el manifiesto final la incluya.

### Manifiesto del lote

Debe incluir esquema, estado padre, preestado, receptor, inicio/cierre declarados, referencias ordenadas a todas las solicitudes recibidas que se van a incluir, solicitud propia del receptor, cantidad, referencias a recibos disponibles, versión de reglas y hash del contenido canónico.

La lista y el orden se deben fijar antes de calcular el hash. No incluir un campo que cambie después del hash.

## 6. Temporizador y cierre

- Configurar `minimum_propagation_seconds = 600` para el primer prototipo.
- Guardar de manera persistente el estado de la ventana y el instante de inicio declarado, usando el almacenamiento real de Node Core OS.
- Al reiniciar, recalcular el tiempo restante desde el estado persistido y validar que el anuncio sigue correspondiendo al manifiesto vigente.
- No confiar en el reloj del cliente remitente para decidir si su solicitud pertenece a una ventana.
- Antes del cierre, la recepción de solicitudes sigue habilitada.
- El envío de la solicitud propia solo se habilita cuando vence el mínimo.
- Después de cerrar el lote, cualquier solicitud tardía se enruta a la ventana siguiente.
- La aplicación debe explicar al usuario por qué el botón está bloqueado y mostrar la cuenta regresiva.

## 7. Integración con Node Core OS

Interfaces confirmadas en el repositorio:
- `StorageManager` en `node_core/storage.py`: almacenamiento local con comprobación de rutas dentro de la raíz.
- `ContentManager` en `node_core/content.py`: añadir contenido, recuperar por CID, pinning y registro de contenido.
- `NodeNetwork` en `node_core/network.py`: identidad Peer ID de Kubo, pares conectados, conexión y ping.

Límite confirmado: `NodeNetwork` documenta conectividad básica, no mensajería autenticada de aplicación ni consenso. Por tanto, el adaptador de red debe basarse en una interfaz de transporte explícita que se audite y pruebe antes de conectar la aplicación. No se debe fingir que enviar un ping transmite una solicitud.

El adaptador de contenido debe comprobar que la publicación devuelve un CID y que el contenido recuperado coincide con los bytes canónicos esperados. Guardar un CID no equivale a que el objeto esté disponible en todos los nodos.

## 8. Datos y privacidad de la modalidad pública

- Mostrar exactamente los campos de identidad que se incluirán en cada solicitud.
- Exigir consentimiento expreso antes de publicar esos campos.
- Usar identidades de prueba en pruebas automáticas y de tres nodos.
- Advertir que los documentos publicados en IPFS pueden copiarse y permanecer accesibles aunque se retire una referencia local.
- No publicar contraseñas, secretos ni material de autenticación.
- No implementar ni exponer un selector de modo privado en esta fase.

## 9. Qué no debe añadirse todavía

- OpenPGP o modo privado.
- Generación de claves nuevas.
- Un sistema de reputación.
- Árboles de Merkle antes de tener una lista de lote determinista y probada.
- Una base de datos nueva si el almacenamiento existente puede resolver el primer prototipo.
- Un protocolo de consenso general complejo.
- Reescrituras de HashPaper o cambios en su instalador.
- Un soporte oficial para Termux que no haya sido validado de manera separada.

## 10. Criterio de estructura terminada

La estructura se considera lista para empezar la implementación cuando cada módulo tenga contrato de entrada/salida, errores definidos y pruebas planeadas; los adaptadores apunten a interfaces existentes; el flujo de ventana y lote esté representado por estados claros; y los formatos tengan ejemplos válidos e inválidos. Esta definición no declara implementada la aplicación.
