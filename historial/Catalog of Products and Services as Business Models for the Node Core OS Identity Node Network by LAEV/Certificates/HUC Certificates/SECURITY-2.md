# Seguridad — LAEV HUC Standalone 0.7

## Controles incluidos

- CA X.509 RSA-3072 de laboratorio.
- CSR firmado por titular; la clave privada del titular no se entrega al emisor.
- HUC-CC complementario firmado Ed25519.
- Registro lógico UTXO local de solo adición, con hash encadenado y firmas del emisor.
- State Attestation firmada con estado, secuencia, cabeza de ledger, TTL y outpoint.
- Trust anchor externo para fijar CA, clave pública de emisor y política.
- Paquetes ZIP públicos sin claves privadas.
- Verificación offline de X.509, HUC-CC y estado.
- HUC Direct challenge-response con nonce de 256 bits, audiencia, expiración, prueba de posesión y replay store.
- Renovación consume la salida anterior; revocación consume la salida activa.

## Riesgos y límites

1. **Autoridad del emisor:** el emisor controla las claves que certifican identidad, HUC-CC y estado. No hay consenso de varias organizaciones en esta versión.
2. **Evidencia obsoleta:** un paquete puede contener estado ACTIVE de antes de una revocación reciente. TTL, expiración y resultado INDETERMINATE reducen este riesgo, pero no eliminan la ventana de propagación.
3. **Prueba de posesión:** el challenge demuestra control de la clave privada correspondiente al certificado, no identidad civil ni que el titular esté autorizado para una operación específica.
4. **Transporte:** QR, NFC y Bluetooth son medios; no proporcionan cifrado/autenticación automáticamente. La aplicación debe proteger el canal y los datos.
5. **Replay store:** debe ser persistente, protegido y compartido por instancias de verificación que deban reconocer los mismos nonces usados.
6. **Claves demo:** claves privadas PEM sin cifrar para pruebas. No producción; utilizar HSM/KMS o almacén protegido.
7. **Identidad:** el CSR prueba posesión de clave, no identidad legal. Hace falta RA/KYC según el caso de uso.
8. **Sin revocación X.509 clásica:** no hay OCSP/CRL; validadores PKI tradicionales no consultan automáticamente HUC.
9. **Sin timestamp externo:** las fechas dependen del reloj local; no existe sello de tiempo independiente.
10. **JSON restringido:** la canonicalización propia debe sustituirse por RFC 8785/JCS completo antes de interoperar entre implementaciones de producción.

## No usar en producción todavía

No utilizar como CA pública, certificado TLS público, documento legal, licencia profesional ni mecanismo de acceso crítico. Requiere revisión criptográfica, custodia de claves, gestión de identidades, procedimiento legal, pruebas de interoperabilidad y auditoría externa.
