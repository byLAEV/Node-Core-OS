# LAEV HUC Standalone Protocol 0.7

## 1. Objetivo

Definir un paquete de certificado autónomo que combine X.509, una atestación complementaria HUC-CC y una prueba de estado UTXO firmada por el emisor. No se necesita blockchain, red de validadores o nodo de consenso.

## 2. Objetos

### X.509

Certificado estándar, firmado por la CA emisora, con sujeto, clave pública, serial, vigencia y restricciones X.509.

### HUC-CC

Objeto JSON versionado y firmado con Ed25519 por el emisor. Contiene:

- hash SHA-256 del DER X.509;
- serial del certificado;
- outpoint lógico inicial;
- secuencia de emisión;
- ID del emisor y hash de política;
- modo `ISSUER_SIGNED_POLICY`;
- vigencia consistente con X.509.

No reemplaza X.509 y se distribuye como documento complementario separado.

### UTXO lógico

Cada certificado posee una salida lógica no transferible. ISSUE crea una salida; RENEW consume la salida anterior y crea una nueva; REVOKE consume la salida vigente sin sucesor. El registro de eventos local del emisor es append-only y cada evento está firmado.

### State Attestation

Objeto firmado Ed25519 por el emisor. Acredita el estado actual del certificado, el outpoint si está activo, secuencia, cabeza del registro, hora de emisión y vencimiento de la evidencia. El paquete público lleva esta atestación, no las claves privadas ni el registro completo de otros certificados.

## 3. Paquete de verificación

El paquete ZIP contiene:

- certificado CA público;
- clave pública del emisor;
- política HUC;
- ancla de confianza;
- X.509;
- HUC-CC;
- state attestation;
- manifiesto con hashes.

El verificador recibe por otro canal la huella SHA-256 del ancla. Comprueba CA autofirmada, ancla, firma X.509, vínculo HUC-CC, firma HUC-CC, firma de estado y frescura.

## 4. Estados

| Estado | Significado | Veredicto |
|---|---|---|
| ACTIVE | UTXO vigente no consumido | VALID si evidencia fresca |
| SUPERSEDED | UTXO consumido por renovación | INVALID |
| REVOKED | UTXO consumido por revocación | INVALID |
| Evidencia antigua | No se puede confirmar vigencia actual | INDETERMINATE |

No se reactiva un certificado revocado ni sustituido. Se emite uno nuevo.

## 5. HUC Direct Exchange

El verificador crea un `challenge` con:

- hash DER del certificado esperado;
- audiencia de la aplicación;
- nonce aleatorio de 256 bits;
- creación y expiración.

El titular devuelve:

- el challenge exacto;
- el paquete HUC;
- firma RSA-PKCS1v1.5/SHA-256 sobre un mensaje con separación de dominio.

El verificador valida challenge, audiencia, ventana temporal, paquete, estado del emisor, prueba de posesión y nonce no utilizado. El nonce queda en un replay store local.

El protocolo de mensajes es independiente del transporte. Puede llevarse sobre QR, NFC, Bluetooth, Nearby Share, HTTPS directo o intercambio de archivos. No exige un servicio HUC en línea ni una red P2P de nodos.

## 6. Confianza y frescura

La atestación de estado se emite con un TTL fijado en la política. El verificador también aplica un máximo de antigüedad local. El pin del ancla debe obtenerse fuera de banda.

Un paquete ACTIVE desconectado no conoce revocaciones posteriores. Tras renovar o revocar, el emisor genera una atestación nueva y el titular/verificador debe recibir el paquete actualizado. La opción INDETERMINATE evita tratar evidencia expirada como válida.

## 7. Alcance

Esta versión no implementa nodos, blockchain, pagos, consenso distribuido, relay, sockets, descubrimiento P2P, OCSP/CRL ni sellado de tiempo de terceros. HUC-CC es una atestación protocolaria de emisor individual, no un quórum multiinstitucional. Se puede añadir firma múltiple offline en una evolución futura sin adoptar nodos.
