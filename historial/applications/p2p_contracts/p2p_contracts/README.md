# Paquete interno P2P Contracts

## Implementación inicial

- service.py: validación de cantidades, serialización JSON canónica, hash SHA-256, persistencia de solicitudes BTC, manifiestos encadenados, evidencias y búsqueda por ID.
- cli.py: formularios de terminal para crear una solicitud, registrar un resultado, consultar un ID y mostrar el manifiesto local.
- __init__.py: identificadores de aplicación y versión de desarrollo.

La interfaz utiliza StorageManager, IdentityProfileStore y NodeNetwork existentes. La conectividad de Kubo no se debe interpretar como transporte de mensajes entre aplicaciones.

## Reglas de integridad

- Las cantidades financieras se validan como cadenas decimales, sin números de punto flotante.
- Los documentos originales no se sobrescriben al registrar evidencias; cada cambio genera un manifiesto nuevo.
- Cada manifiesto referencia el hash del manifiesto anterior y mantiene las referencias de solicitudes y evidencias.
- La consulta recalcula los hashes de la solicitud y las evidencias antes de mostrarlos.
- Los resultados se etiquetan como declaraciones no verificadas.
- Los campos de identidad se precargan localmente y requieren consentimiento expreso para incluirse.
- La aplicación no firma, ejecuta ni liquida transacciones financieras.

## Límites

El prototipo es local. No publica todavía documentos en IPFS ni los propaga por la red. No incluye modo privado, OpenPGP ni generación de claves. HashPaper permanece fuera del alcance.
