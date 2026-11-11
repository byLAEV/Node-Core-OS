# NODE-PKI-GUARD

## Propuesta técnica oficial v1.0

**Certificado complementario de autorización criptográfica basado en infraestructura UTXO**

- **Proyecto:** NODE Core OS byLAEV
- **Autor del diseño:** byLAEV
- **Identificador del sistema:** NODE-PKI-GUARD
- **Componente complementario:** NODE-PKI-BINDING
- **Unidad de autorización:** NODE-PKI-AUTH-UTXO
- **Versión del documento:** 1.0
- **Estado:** Propuesta técnica oficial para revisión, implementación y validación
- **Clasificación:** Especificación de diseño
- **Estado de implementación:** Documentación propuesta; no implica implementación funcional ni conformidad verificada.

---

## 1. Declaración de la propuesta

NODE-PKI-GUARD es un sistema de seguridad criptográfica diseñado para complementar los certificados digitales X.509 y las infraestructuras de clave pública (PKI) existentes.

Su objetivo es añadir una capa verificable de autorización, control de capacidades y prevención de reutilización de permisos mediante una infraestructura UTXO integrada con NODE Core OS.

El sistema no pretende sustituir a las autoridades certificadoras (CA), a OpenSSL, a X.509 ni a los protocolos de comunicación existentes. Su propuesta consiste en permitir que los certificados convencionales sigan realizando sus funciones originales y que NODE-PKI-GUARD añada controles adicionales cuando una operación requiera autorización protegida.

La combinación produce una credencial compuesta:

1. **Certificado X.509:** acredita la identidad y las capacidades criptográficas según la infraestructura PKI que lo emitió.
2. **NODE-PKI-BINDING:** relaciona el certificado X.509 con una identidad y una política verificable de NODE Core OS.
3. **NODE-PKI-AUTH-UTXO:** representa una autorización específica, limitada y consumible una sola vez.
4. **Recibo de ejecución:** permite comprobar el resultado de la operación autorizada.

La validez del componente UTXO nunca convierte en válido un certificado X.509 inválido.

## 2. Objetivo principal

Proporcionar una capa complementaria de seguridad que permita:

- Vincular certificados X.509 con identidades verificables dentro de NODE Core OS.
- Demostrar la posesión de las claves privadas asociadas.
- Establecer permisos específicos para operaciones sensibles.
- Autorizar una operación mediante un UTXO individual.
- Impedir que una autorización consumida vuelva a utilizarse.
- Controlar la vigencia, el contexto y el destinatario de cada autorización.
- Aplicar políticas de límites y cuotas verificadas por consenso.
- Registrar evidencia verificable de las operaciones.
- Integrarse con programas, servicios, redes, aplicaciones web y sistemas Web2 y Web3 que implementen el protocolo.

## 3. Principio de funcionamiento

NODE-PKI-GUARD utiliza un modelo híbrido de validación.

El certificado X.509 continúa proporcionando las funciones habituales de identidad, autenticación y confianza. NODE-PKI-GUARD interviene únicamente cuando la operación solicitada está clasificada como protegida.

El sistema contempla tres decisiones:

| Estado | Comportamiento |
|---|---|
| STANDARD | Permite el procedimiento convencional cuando la política no exige autorización UTXO. |
| PROTECTED | Exige certificado válido, vinculación activa, pruebas criptográficas y consumo de una autorización UTXO válida. |
| DENY | Rechaza la operación por política o por incumplimiento de cualquier condición de seguridad. |

**Regla fundamental:** una operación PROTECTED necesita cumplir simultáneamente las condiciones X.509 y NODE-PKI-GUARD. Ninguna de las dos sustituye a la otra.

Las comprobaciones ordinarias de certificados y las conexiones TLS normales no consumen UTXO automáticamente.

## 4. Componentes oficiales

### 4.1. Certificado X.509 existente

Es la credencial convencional emitida por una autoridad certificadora reconocida o por una PKI privada configurada por el servicio.

NODE-PKI-GUARD utiliza su información pública para comprobar:

- Cadena de confianza.
- Firma y autoridad emisora.
- Vigencia.
- Revocación, cuando corresponda.
- Nombre de dominio o identidad esperada.
- Huella digital del certificado.
- Huella de la clave pública.
- Key Usage y Extended Key Usage.
- Compatibilidad entre el propósito del certificado y la operación solicitada.

NODE-PKI-GUARD no modifica ni invalida las reglas originales del certificado.

### 4.2. NODE-PKI-BINDING

Es el objeto criptográfico que vincula un certificado X.509 con una identidad de NODE Core OS y define las capacidades que esa vinculación puede utilizar.

Campos mínimos propuestos:

- \`format\`: NODE-PKI-BINDING.
- \`version\`: versión del formato.
- \`binding_id\`: identificador único.
- \`node_id\`: identificador de la identidad NODE.
- \`x509_fingerprint_sha256\`: huella del certificado X.509.
- \`spki_sha256\`: huella de la información de la clave pública.
- \`purpose\`: propósitos admitidos.
- \`allowed_operations\`: operaciones autorizadas.
- \`denied_operations\`: operaciones expresamente prohibidas.
- \`constraints\`: límites y restricciones.
- \`issuer_key_id\`: identificador de la clave emisora del binding.
- \`issued_at\` y \`expires_at\`: metadatos temporales.
- \`binding_status\`: estado de la vinculación.
- \`proof_of_possession\`: evidencia de posesión de claves.

El binding deberá estar firmado por una identidad autorizada según la política de NODE Core OS.

La información pública del certificado y las capacidades declaradas deberán ser coherentes. Por ejemplo, un certificado limitado a autenticación TLS no podrá adquirir por medio del binding capacidades de firma documental que no permita su propio perfil criptográfico.

### 4.3. NODE-PKI-AUTH-UTXO

Es la unidad de autorización de un solo uso.

Cada UTXO representa un permiso concreto asociado a una operación definida. No se considera una moneda ni un activo de intercambio: es una capacidad de autorización verificable por la infraestructura de consenso.

Su estructura lógica deberá incluir:

- Identificador de autorización.
- Outpoint de origen: \`txid:vout\`.
- Identificador del binding.
- Identidad NODE autorizada.
- Tipo de operación.
- Hash de la operación.
- Destinatario o audiencia.
- Identificador y versión de política.
- Compromiso criptográfico del desafío y del contexto.
- Altura o época válida de inicio y finalización.
- Requisitos de firma.
- Indicador de uso único.

La información sensible no debe almacenarse directamente en el UTXO. Los datos públicos se limitarán a lo que los validadores necesiten para verificar las condiciones. Los documentos y pruebas adicionales podrán transportarse fuera de cadena, vinculados mediante compromisos criptográficos.

El estado de una autorización no se decide mediante un campo editable de un archivo. Su condición de disponible o consumida debe derivarse del estado validado del ledger.

Una autorización consumida no puede volver a utilizarse. Para obtener una nueva autorización deberá emitirse una nueva capacidad conforme a la política correspondiente.

## 5. Prueba dual de posesión de claves (Dual Proof-of-Possession)

NODE-PKI-GUARD incorpora un mecanismo de doble prueba de posesión para vincular de manera verificable la identidad NODE y la identidad X.509.

El solicitante deberá demostrar control de:

1. La clave privada de su identidad NODE.
2. La clave privada correspondiente a la clave pública del certificado X.509.

Ambas claves firman un mismo desafío criptográfico, con los algoritmos admitidos para cada clave.

El desafío contiene:

- Dominio: \`NODE-PKI-GUARD-DUAL-POP\`.
- Versión del protocolo.
- \`challenge_id\`.
- Nonce criptográfico aleatorio de al menos 256 bits.
- \`node_id\`.
- Huella X.509.
- Huella SPKI.
- Propósito solicitado.
- Audiencia.
- Fecha de emisión y expiración.

El contenido firmado debe tener una representación binaria inequívoca. Para objetos JSON se propone utilizar JSON Canonicalization Scheme (JCS), conforme a RFC 8785.

El verificador comprobará ambas firmas, la correspondencia entre las claves públicas y las identidades declaradas, la vigencia del desafío y su condición de no reutilizado.

Las pruebas deberán quedar ligadas al contexto de la operación. No se aceptarán firmas válidas para un propósito distinto, una audiencia distinta o una operación diferente.

## 6. Autorizaciones y capacidades

Las capacidades se definen en las políticas del sistema y no únicamente en el documento de vinculación.

Ejemplos de operaciones que podrán requerir protección:

- \`CERTIFICATE_ISSUANCE\`
- \`CERTIFICATE_RENEWAL\`
- \`CERTIFICATE_REVOCATION\`
- \`KEY_ROTATION\`
- \`PRIVILEGE_GRANT\`
- \`ADMINISTRATIVE_ACTION\`
- \`SOFTWARE_RELEASE_SIGNING\`
- \`DOCUMENT_SIGNING\`

Cada implementación deberá decidir expresamente cuáles operaciones son STANDARD, PROTECTED o DENY.

Las restricciones podrán incluir:

- Número máximo de autorizaciones por período.
- Número máximo de autorizaciones simultáneas.
- Operaciones permitidas.
- Operaciones prohibidas.
- Audiencias válidas.
- Vigencia de la autorización.
- Límites definidos por política.
- Requisitos de aprobación múltiple.

Las cuotas deberán mantenerse en el estado de consenso, vinculadas al identificador del binding y al período correspondiente. No será suficiente declarar un límite en un JSON.

## 7. Rotación segura de claves

La rotación de claves requiere un procedimiento específico para evitar que una clave nueva sustituya a la anterior sin demostrar su posesión.

Se distinguen cuatro elementos:

- \`current_spki_sha256\`: clave pública actual.
- \`current_x509_fingerprint_sha256\`: certificado actual.
- \`target_spki_sha256\`: clave pública entrante.
- \`target_x509_fingerprint_sha256\`: certificado entrante, cuando ya exista.

El procedimiento exigirá:

1. Firma de la clave actual autorizando la transición.
2. Prueba de posesión de la clave nueva.
3. Firma de la identidad NODE.
4. Autorización UTXO específica para la operación.
5. Validación de la política y del estado de consenso.
6. Confirmación final de la transición.
7. Activación de la nueva vinculación y revocación o sustitución de la anterior según la política.

La clave nueva nunca se considerará activa únicamente por haber sido incluida en una solicitud.

En operaciones críticas podrán exigirse aprobaciones adicionales mediante firmas umbral o multifirma.

## 8. Vigencia basada en consenso

La autorización utilizará el tiempo de consenso como referencia principal para determinar su vigencia.

Se propone incluir:

- \`issued_epoch\`.
- \`valid_from_epoch\`.
- \`valid_until_epoch\`.

La versión de implementación deberá definir de manera inequívoca qué representa una época. Se recomienda derivarla de alturas finalizadas del ledger, conforme a las reglas del consenso de NODE Core OS.

La autorización solo será válida dentro de su ventana de consenso.

Los campos \`issued_at\` y \`expires_at\` podrán conservarse como metadatos para validaciones externas, interfaces y auditoría, pero no sustituirán al estado autoritativo del ledger.

La ejecución protegida deberá esperar la finalidad definida por el mecanismo de consenso. La política de finalidad, reorganizaciones y confirmaciones deberá documentarse para la red concreta antes de habilitar operaciones de producción.

## 9. Integración con OpenSSL y X.509

NODE-PKI-GUARD funcionará como una capa de integración posterior a la validación convencional del certificado.

El orden de comprobación será:

1. Establecer la conexión TLS.
2. Obtener el certificado del par.
3. Verificar la cadena y las políticas de confianza.
4. Verificar el nombre del servicio cuando corresponda.
5. Comprobar vigencia y revocación según configuración.
6. Obtener la huella SHA-256 del certificado.
7. Obtener la huella SHA-256 de la clave pública.
8. Buscar el NODE-PKI-BINDING correspondiente.
9. Evaluar la política de la operación.
10. Solicitar autorización UTXO si la operación es PROTECTED.
11. Ejecutar la operación solo después de la confirmación requerida.

Las interfaces de OpenSSL relevantes incluyen \`SSL_get1_peer_certificate\`, \`SSL_get_verify_result\`, \`X509_digest\` y \`X509_pubkey_digest\`. La configuración de verificación deberá incluir expresamente la validación del nombre esperado y no depender exclusivamente del resultado de verificación de cadena.

**Restricción de integración:** el consumo UTXO no se ejecutará dentro de \`verify_callback\` ni se insertará como una operación obligatoria en cada handshake TLS. Se realizará desde el middleware de autorización de la aplicación, después de la autenticación y antes de ejecutar una operación protegida.

Así se conserva la compatibilidad con servicios X.509 existentes que todavía no implementen NODE-PKI-GUARD.

## 10. Flujo oficial de autorización

El flujo de una operación protegida será:

1. El servicio recibe una solicitud.
2. El sistema valida el certificado X.509.
3. Se verifica la vinculación NODE-PKI-BINDING.
4. Se clasifica la operación mediante la política.
5. Se genera o recupera el identificador de operación.
6. Se construye el contexto canónico y su hash.
7. Se verifican las firmas y las pruebas de posesión exigidas.
8. Se localiza la autorización UTXO correspondiente.
9. Los validadores comprueban su disponibilidad y todas sus restricciones.
10. La transacción de gasto se incorpora al ledger.
11. Se espera la finalidad establecida por consenso.
12. Se registra la autorización como consumida.
13. El executor realiza la operación externa de forma idempotente.
14. Se genera un recibo firmado y verificable.

Si alguna comprobación falla, la operación se rechaza.

## 11. Protección contra repetición e idempotencia

El protocolo distinguirá tres identificadores:

- \`operation_id\`: identifica la operación solicitada.
- \`idempotency_key\`: identifica los reintentos de esa operación.
- \`utxo_outpoint\`: identifica la autorización consumible.

El hash de la operación se calculará sobre un objeto canónico que incluya el dominio del protocolo, la identidad, el binding, el tipo de operación, la audiencia, la política, el contexto de la solicitud, el nonce y los parámetros de vigencia.

Se propone utilizar un dominio independiente para el cálculo de idempotencia:

\`NODE-PKI-GUARD-IDEMPOTENCY-v1\`

Una misma clave de idempotencia con contenido diferente deberá producir un conflicto y nunca reutilizar una autorización.

Un reintento con el mismo identificador y contenido deberá recuperar el resultado existente o continuar la reconciliación. No deberá consumir un segundo UTXO por el simple hecho de repetir la solicitud.

Si el UTXO ya fue consumido y el servicio externo falla, el permiso permanecerá consumido. La operación pasará a un estado de revisión y reconciliación. No se restaurará automáticamente la autorización.

Esta arquitectura busca garantizar el uso único de la capacidad y una ejecución controlada. No se afirmará una garantía general de ejecución exactamente una vez entre sistemas externos que no compartan una transacción atómica; para ello se requiere ejecución idempotente y mecanismos de recuperación.

## 12. Estados de una operación

Se propone el siguiente ciclo de vida:

- \`CREATED\`: solicitud recibida.
- \`VALIDATED\`: identidad, certificado y contexto validados.
- \`UTXO_SUBMITTED\`: gasto enviado al consenso.
- \`UTXO_FINALIZED\`: consumo confirmado según la finalidad definida.
- \`EXECUTING\`: operación externa en ejecución.
- \`COMMITTED\`: ejecución confirmada y recibo generado.
- \`FAILED_REQUIRES_REVIEW\`: error posterior al consumo que necesita reconciliación.

Los estados deben almacenarse de manera persistente y permitir recuperar operaciones incompletas después de reinicios.

## 13. Integración con almacenamiento local e IPFS/Kubo

NODE Core OS podrá utilizar su almacenamiento local y su almacenamiento distribuido para conservar la información asociada al protocolo.

**Almacenamiento local:**

- Estado operativo.
- Índices de operaciones.
- Claves de idempotencia.
- Referencias a UTXO.
- Estado de ejecución.
- Recibos y evidencias.
- Configuración y políticas locales.

**Almacenamiento distribuido:**

- Documentación pública del protocolo.
- Esquemas y manifiestos.
- Evidencias públicas no sensibles.
- Recibos o paquetes de auditoría cuando su publicación esté autorizada.

No se almacenarán claves privadas, secretos de sesión ni información personal innecesaria en IPFS.

La publicación de un contenido mediante IPFS permite identificar sus bytes mediante un CID, pero no demuestra por sí sola que el contenido sea auténtico, que haya sido aprobado por una autoridad o que permanezca disponible indefinidamente. La autenticidad deberá verificarse mediante firmas y compromisos criptográficos.

## 14. Evidencia y recibo de autorización

Cada operación finalizada deberá generar un recibo que contenga, como mínimo:

- Identificador de operación.
- Identificador de autorización.
- Identificador del binding.
- Huella X.509.
- Hash de operación.
- Outpoint consumido.
- Identificador de transacción.
- Estado final.
- Evidencia de finalidad según el consenso.
- Hash del resultado.
- Identidad del executor.
- Firma del emisor del recibo.

El recibo no sustituye la validación independiente del ledger. Los verificadores deberán poder comprobar la correspondencia entre el recibo, el gasto UTXO y el resultado declarado.

## 15. Seguridad y modelo de amenazas

El protocolo deberá contemplar, como mínimo, las siguientes amenazas:

| Amenaza | Control previsto |
|---|---|
| Certificado falso o no confiable | Validación X.509 y política de CA. |
| Certificado expirado o revocado | Comprobaciones de vigencia y revocación. |
| Suplantación de identidad NODE | Firma de identidad y verificación del binding. |
| Clave privada X.509 no poseída | Dual Proof-of-Possession. |
| Reutilización de autorización | Consumo UTXO y estado de consenso. |
| Doble gasto concurrente | Validación atómica del ledger. |
| Sustitución de operación | Hash canónico y dominio criptográfico. |
| Cambio no autorizado de claves | Firma de clave actual y prueba de posesión de clave nueva. |
| Uso fuera de vigencia | Restricciones de altura o época finalizada. |
| Alteración de cuotas | Contadores mantenidos por consenso. |
| Fallo después del consumo | Idempotencia y reconciliación. |
| Compromiso de una clave administrativa | Aprobación umbral para políticas críticas. |
| Filtración de información | Minimización de datos en cadena y almacenamiento distribuido. |

Los algoritmos criptográficos deberán identificarse explícitamente mediante suites versionadas y permitir migraciones controladas. No se fijará un único algoritmo para todas las claves, ya que la identidad NODE y la clave X.509 pueden utilizar familias criptográficas distintas.

## 16. Extensión TLS experimental

Se contempla una extensión TLS opcional para transportar referencias de NODE-PKI-GUARD, como:

- Versión del protocolo.
- \`binding_id\`.
- Outpoint.
- \`operation_id\`.
- Nonce.

Esta extensión será experimental y posterior a la implementación del middleware.

No constituye una autorización por sí misma ni permite consumir UTXO durante el handshake. Si se adopta, deberá vincular el contexto a la sesión mediante un mecanismo apropiado basado en TLS exporter y respetar las reglas de negociación de TLS 1.3.

Las operaciones protegidas no deberán ejecutarse con datos 0-RTT debido a sus propiedades de repetición. La extensión no será obligatoria para la compatibilidad básica del protocolo.

## 17. Requisitos de consenso

La infraestructura UTXO deberá demostrar:

- Identificación única de cada outpoint.
- Prevención de doble gasto entre nodos.
- Validación de firmas y restricciones.
- Actualización consistente del estado.
- Reglas de finalidad explícitas.
- Manejo de reorganizaciones.
- Recuperación y sincronización entre nodos.
- Registro verificable de transacciones.
- Reglas para la emisión de nuevas autorizaciones.
- Protección frente a la emisión no autorizada de capacidades.

La implementación local de un conjunto UTXO en memoria no será considerada una implementación de consenso distribuido.

La seguridad de NODE-PKI-GUARD dependerá de que estas garantías estén demostradas en la red UTXO utilizada.

## 18. Criterios de conformidad y pruebas

Una implementación no podrá declararse conforme por el simple hecho de validar sus estructuras JSON.

Se deberán implementar y superar pruebas automatizadas para:

1. Certificado X.509 válido.
2. Certificado X.509 expirado.
3. Certificado emitido por una CA no confiable.
4. Certificado revocado cuando corresponda.
5. Hostname incorrecto.
6. Binding válido e inválido.
7. Firma NODE incorrecta.
8. Firma X.509 incorrecta.
9. Reutilización de desafío.
10. Operación no permitida.
11. Autorización UTXO disponible.
12. Reutilización de UTXO consumido.
13. Doble gasto concurrente desde nodos distintos.
14. Operación fuera de la vigencia de consenso.
15. Cuota excedida.
16. Rotación con clave nueva no demostrada.
17. Reintentos con idempotencia.
18. Fallo del servicio externo después del consumo.
19. Recuperación después de reinicio.
20. Verificación independiente de recibos.

Las pruebas de consenso deberán ejecutarse en múltiples nodos y no solamente en memoria dentro de un único proceso.

## 19. Alcance y límites de la propuesta

NODE-PKI-GUARD:

- Complementa certificados X.509 y PKI.
- No reemplaza autoridades certificadoras.
- No modifica el formato estándar de los certificados existentes.
- No puede imponer sus políticas a un servicio que no lo integre.
- No convierte un certificado inválido en válido.
- No requiere un gasto UTXO por cada handshake TLS.
- No garantiza la seguridad de claves privadas ya comprometidas.
- No garantiza disponibilidad permanente por el simple uso de IPFS.
- No declara consenso ni finalidad sin una implementación verificable.

Su adopción deberá ser gradual y compatible con servicios existentes.

## 20. Plan de implementación en NODE Core OS

Se establece el siguiente orden de desarrollo:

**Fase 1 — Especificación y formatos**

- Definir los esquemas de binding y autorización.
- Establecer los identificadores y reglas de canonicalización.
- Definir los perfiles criptográficos.
- Documentar el contrato del backend UTXO.

**Fase 2 — Vinculación criptográfica**

- Implementar Dual Proof-of-Possession.
- Implementar desafíos únicos.
- Validar firmas y binding.
- Crear pruebas negativas y positivas.

**Fase 3 — Motor de autorización**

- Implementar STANDARD, PROTECTED y DENY.
- Implementar operaciones e idempotencia.
- Implementar persistencia y recibos.

**Fase 4 — Integración UTXO**

- Conectar el motor al backend real.
- Validar gasto único.
- Implementar cuotas y vigencia de consenso.
- Probar doble gasto en múltiples nodos.

**Fase 5 — Integración X.509/OpenSSL**

- Incorporar el middleware.
- Validar certificados y huellas.
- Mantener intacto el flujo convencional TLS.
- Probar operaciones protegidas de extremo a extremo.

**Fase 6 — Auditoría y compatibilidad**

- Validar recuperación y fallos.
- Revisar privacidad y amenazas.
- Ejecutar pruebas de interoperabilidad.
- Documentar resultados reproducibles.
- Evaluar extensiones TLS opcionales.

## 21. Criterio de publicación

La versión 1.0 de este documento constituye la propuesta técnica oficial de diseño de NODE-PKI-GUARD para NODE Core OS byLAEV.

Su publicación como especificación no equivale a una certificación de seguridad ni a una implementación terminada.

La denominación de versión implementada, la conformidad y la disponibilidad para producción solo podrán asignarse después de desarrollar el código, ejecutar las pruebas funcionales y distribuidas, revisar la seguridad y documentar los resultados.

El principio de desarrollo será mantener transparencia sobre el estado real de cada componente: propuesto, implementado, probado, auditado o desplegado.

## 22. Referencias técnicas

- RFC 5280 — Internet X.509 Public Key Infrastructure Certificate and CRL Profile. https://www.rfc-editor.org/rfc/rfc5280
- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3. https://www.rfc-editor.org/rfc/rfc8446
- RFC 8785 — JSON Canonicalization Scheme (JCS). https://www.rfc-editor.org/rfc/rfc8785
- NIST SP 800-57 Part 1 Revision 5 — Recommendation for Key Management. https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final
- JSON Schema Draft 2020-12. https://json-schema.org/draft/2020-12
- OpenSSL Documentation. https://docs.openssl.org/

---

**NODE-PKI-GUARD — byLAEV**  
**NODE Core OS**

*Certificados existentes. Autorizaciones verificables. Capacidades de un solo uso.*

---

## Estado del producto dentro del catálogo

Este documento registra una propuesta de certificado complementario de PKI/X.509. No añade por sí solo un perfil al emisor de credenciales NODE existente, no crea una CA, no emite certificados X.509, no implementa un ledger UTXO y no demuestra consenso distribuido.

La implementación deberá desarrollarse en componentes separados, con contratos explícitos y pruebas reproducibles. La incorporación futura de un identificador al formato de certificados de identidad de NODE requerirá una decisión de compatibilidad y cambios específicos en el código y sus pruebas.

---

## Implementation tracking — English

The first local implementation is under review in [Pull Request #227](https://github.com/byLAEV/Node-Core-OS/pull/227).

- [NODE-PKI-GUARD implementation module](../../../../node_core/security/node_pki_guard.py)
- [NODE-PKI-BINDING JSON Schema](../../../../schemas/node-pki-binding.schema.json)
- [NODE-PKI-AUTH-UTXO JSON Schema](../../../../schemas/node-pki-auth-utxo.schema.json)
- [Local unit tests](../../../../tests/test_node_pki_guard.py)
- [Implementation boundary and runbook](../../../../docs/NODE-PKI-GUARD-IMPLEMENTATION.md)
- [GitHub Actions local conformance workflow](../../../../.github/workflows/node-pki-guard.yml)

Current implementation scope: local cryptographic primitives and policy evaluation only. It does not yet provide a production X.509 trust validator, UTXO ledger, distributed consensus, transaction finality, or production executor. The pull request and CI results must be reviewed before this proposal is described as implemented or conformant.


---

## NODE-PKI-GUARD v1.1 implementation adapters

The implementation branch now includes the following additional modules:

- \`node_core/security/node_pki_guard_x509.py\` — explicit OpenSSL X.509 chain, TLS purpose, hostname/IP, and optional CRL validation.
- \`node_core/security/node_pki_guard_utxo.py\` — backend contract for atomic authorization spending, durable idempotency, and finality-proof verification.
- \`tests/test_node_pki_guard_x509.py\` — OpenSSL-backed certificate validation tests.
- \`tests/test_node_pki_guard_utxo.py\` — backend contract and finality orchestration tests.

These adapters do not constitute a production ledger or distributed consensus implementation. Review the implementation and CI results in [Pull Request #227](https://github.com/byLAEV/Node-Core-OS/pull/227) before declaring conformance.
