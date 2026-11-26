# Seguridad HUC 0.6

## Estado

Prototipo de investigación. No es una blockchain, ni una implementación completa BFT, ni un producto listo para producción.

## Activos

- Claves privadas Ed25519 de los validadores RSP.
- Claves privadas de autoridades HUC-CC.
- Clave privada de la CA X.509.
- Manifiesto de red y su pin externo.
- Ledger replicado y bloqueos persistentes de voto.
- Claves privadas de titulares.

## Controles presentes

- Identidad Ed25519 independiente por nodo.
- Manifiesto estático con claves públicas únicas y hash de red.
- Perfil `n=3f+1`, quórum `2f+1`.
- Firmas de voto con separación de dominio y vinculación a red, epoch, secuencia, estado padre y propuesta.
- Bloqueo persistente de un voto por nodo y slot.
- Verificación de firmas de quórum antes de aplicar.
- Reproducción determinista del ledger desde génesis.
- Rechazo de rollback y forks en sincronización.
- Paquetes públicos de sincronización sin claves privadas.
- En modo PKI, todos los validadores verifican el X.509, la CA y las firmas HUC-CC antes de votar.
- Escrituras atómicas y bloqueo local entre operaciones concurrentes del mismo nodo.

## Supuestos de seguridad del perfil 4/3

- Como máximo un validador es bizantino (`f=1`).
- Los tres validadores restantes siguen las reglas y no firman dos propuestas para el mismo slot.
- Los bloqueos de voto se conservan de forma durable y no se borran/restauran desde una copia antigua.
- Cada institución protege su clave privada y fija el manifiesto de red por canal independiente.
- Las firmas válidas y el hash de estado padre se verifican antes de aplicar.

No se afirma seguridad ante dos o más validadores bizantinos, robo de varias claves, rollback del almacenamiento de un nodo honesto o cambios de membresía no autorizados.

## Liveness y bloqueos

Si las cuatro instituciones reciben y validan la misma propuesta, tres pueden confirmar aunque una esté desconectada. Si los votos se dividen 2/2 entre dos propuestas para el mismo slot, no existe commit. Los nodos mantienen su primer voto y la secuencia se detiene. No hay view-change ni liberación automática de locks en 0.6.

Un protocolo de recuperación inseguro podría permitir doble commit; por ello no se libera un bloqueo mediante expiración simple. La recuperación debe requerir un protocolo de cambio de vista/epoch diseñado, probado y auditado (objetivo 0.7).

## Limitaciones restantes

- El transporte de mensajes es manual mediante archivos/ZIP; no hay P2P, relay ni TLS API.
- Membresía estática, sin reconfiguración del comité.
- No se implementa view-change ni BFT completo.
- El coordinador no es autoridad, pero una propuesta aún puede necesitar un proponente y cualquier nodo puede agregar firmas. Esto no es un ordenamiento central.
- Las claves privadas del prototipo se guardan sin cifrar; requiere HSM/KMS o almacén seguro.
- No hay timestamp de tercero confiable.
- El modo de red sin `pki` valida hashes y transiciones, pero no X.509 ni HUC-CC; solo sirve para pruebas genéricas.
- La identidad civil y autorización legal del sujeto deben verificarse por política de emisión externa.
- Un verificador offline no puede saber de una revocación posterior al último estado sincronizado.
- El perfil JSON canónico es restringido y todavía requiere RFC 8785/JCS completo para interoperabilidad multi-lenguaje de producción.

## Requisitos antes de producción

1. Especificar y auditar formalmente el protocolo de quórum, anti-equivocación, view-change y recuperación.
2. Pruebas adversariales de red, particiones, reordenamiento, repetición, replay, rollback y persistencia.
3. HSM/KMS o custodia de claves cifrada, backup, rotación y revocación.
4. Transporte autenticado, cifrado, protección contra DoS y observabilidad.
5. Procedimiento de admisión/retiro de validadores y rotación de políticas.
6. Timestamp confiable, política de privacidad/retención y validación de identidad.
7. Integración CRL/OCSP si consumidores X.509 tradicionales deben reconocer las revocaciones HUC.
8. Auditoría criptográfica, legal y de cumplimiento independiente.
