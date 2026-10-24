# Mensajería P2P cifrada RSA/AES

## Alcance

La mensajería segura se incorpora como una capa adicional al protocolo P2P existente. No cambia el identificador de nodo ni reemplaza la identidad Ed25519: el ID continúa siendo `sha256:` más el hash de la clave pública Ed25519. La nueva pareja RSA se guarda por separado y se vincula en sus metadatos al ID Ed25519 existente.

## Criptografía

- RSA-3072 con OAEP y SHA-256: encapsula la clave AES aleatoria.
- AES-256-GCM: cifra el texto y autentica el contenido mediante un nonce aleatorio de 12 bytes y AAD ligada al ID del mensaje y a los IDs del emisor y receptor.
- RSA-PSS con SHA-256: firma el sobre cifrado completo y la confirmación de recepción.
- El texto admite hasta 16 KiB UTF-8. El transporte existente mantiene el límite de tamaño del marco.

RSA no cifra directamente el texto: se usa cifrado híbrido. La clave AES de cada mensaje es nueva y se cifra para la clave pública del destinatario.

## Archivos y configuración

La identidad RSA se crea bajo demanda mediante `NodeRSAIdentityStore(NodeIdentityStore(data_dir)).initialize()`:

- `identity/private/message-rsa.key`: clave privada RSA, modo POSIX 0600.
- `identity/message-rsa.json`: algoritmo, ID Ed25519 asociado y clave pública PEM.

No se reemplaza ni modifica `identity/node.json` ni `identity/private/node.key`. Si falta uno de los archivos RSA, o si la clave privada y la pública no coinciden, la implementación falla de forma cerrada en vez de rotar la clave automáticamente.

Para recibir mensajes, configure `NodePeerService` con `rsa_identity_store` y `trusted_rsa_public_keys`. Este último es un mapa de IDs Ed25519 de nodos ya confiables a claves públicas RSA PEM verificadas por un canal independiente. El servicio rechaza claves RSA anunciadas por el propio sobre si no coinciden con la clave fijada para ese ID. No se habilita confianza automática ni descubrimiento global.

Para enviar, use `send_secure_message(host, port, expected_peer_node_id, recipient_rsa_public_key_pem, text)`. El método exige la autenticación P2P existente sobre TLS, envía el sobre y devuelve solo cuando verifica la firma RSA-PSS de una confirmación que corresponde al ID de mensaje y a ambos IDs de nodo esperados.

## Confirmación y recepción

La recepción valida la identidad de emisor autenticada, la clave RSA fijada, la firma del sobre y el tag AES-GCM antes de entregar texto a `on_message(peer, message_id, text)`. Solo si la función de recepción retorna sin error, el mensaje se agrega a `received_messages` y se envía un `MESSAGE_ACK` firmado. El emisor verifica la firma y los IDs antes de reportar la confirmación.

`received_messages` es una bandeja en memoria para la integración inicial, no un almacenamiento durable. El acuse confirma aceptación por el proceso receptor, no lectura humana ni persistencia en disco. La deduplicación durable y la integración con una bandeja local persistente quedan fuera de esta primera capa.

## Pruebas

- `python -m unittest tests.test_p2p_secure_messaging tests.test_p2p_secure_message_delivery -v`
- `python -m unittest discover -s tests -v`

Las pruebas cubren cifrado/descifrado, rechazo de manipulación, fijación de clave del emisor, vínculo con la identidad Ed25519, permisos de clave privada, firma del acuse y entrega real entre dos servicios P2P sobre TLS local. La aprobación definitiva depende de los resultados observados de CI en el commit de la rama; crear estos archivos no implica que las pruebas ya hayan pasado.
