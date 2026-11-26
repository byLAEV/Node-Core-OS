# NODE-PKI-GUARD v1.0 — Auditoría técnica inicial

- Proyecto: NODE Core OS byLAEV
- PR revisado: [#227](https://github.com/byLAEV/Node-Core-OS/pull/227)
- Rama revisada: `feature/node-pki-guard-implementation-v1`
- Commit base de esta auditoría: `18e6701f2244d25c918d424b7d873c63c3508e25`
- Fecha de revisión: 2026-11-11
- Estado del PR en la revisión: abierto, borrador
- Archivos modificados por el PR en ese momento: 16

## 1. Resultado ejecutivo

El PR #227 contiene una base criptográfica y de autorización UTXO útil. No contiene todavía un ciclo de vida PKI X.509 completo ni permite emitir NODE-PKI-GUARD v1.0.

La conclusión no es reconstruir el trabajo existente. Es conservarlo, corregir sus límites y completar las capas que faltan.

## 2. Evidencia de CI

El workflow `NODE-PKI-GUARD Local Conformance` asociado al commit auditado terminó con conclusión `success`.

Resultados que aparecen en los logs de GitHub Actions:

- 38 pruebas NODE-PKI-GUARD: PASS.
- 9 pruebas de `tests.test_node_identity_certificate`: PASS.
- Compilación de los módulos de seguridad y pruebas incluidos en el workflow: PASS.
- El job aplicó además la comprobación de ejecución no-root: PASS.

Advertencia observada: `tests/test_node_pki_guard_x509.py` usa `datetime.utcnow()`, que genera una advertencia de obsolescencia en Python 3.12. No falló el workflow.

Estos resultados demuestran las pruebas ejecutadas en CI para ese commit. No demuestran por sí solos conformidad PKI integral, resistencia multiproceso, recuperación ante fallos ni seguridad de producción.

## 3. Componentes existentes

| Componente | Archivo | Estado observado |
|---|---|---|
| Primitivas criptográficas | `node_core/security/node_pki_guard.py` | Implementado; pruebas unitarias PASS |
| Binding NODE-PKI-BINDING | `node_pki_guard.py` + schema | Validación estructural y firma de emisor |
| Autorización NODE-PKI-AUTH-UTXO | `node_pki_guard.py` + schema | Validación estructural y de contexto |
| Dual Proof-of-Possession | `node_pki_guard.py` | Ed25519, RSA-PSS-SHA256 y ECDSA-SHA256 |
| Política STANDARD / PROTECTED / DENY | `node_pki_guard.py` | Evaluación fail-closed |
| Validación X.509 con OpenSSL | `node_core/security/node_pki_guard_x509.py` | Cadena, propósito TLS, identidad DNS/IP y CRL opcional |
| Contrato backend UTXO | `node_core/security/node_pki_guard_backend.py` | Interfaz abstracta compartida |
| Coordinador UTXO | `node_core/security/node_pki_guard_utxo.py` | Comprueba solicitud, idempotencia y evidencia de commit |
| Backend SQLite | `node_core/security/backends/standalone_sqlite.py` | Gasto local atómico, WAL y persistencia |
| Pruebas | `tests/test_node_pki_guard*.py` | 38 pruebas de CI aprobadas |
| Arquitectura dual | `ARCHITECTURE-DUAL-MODEL.md` | Especificación; no equivale a adapter Network implementado |

### 3.1 Garantías que sí están representadas en el código

- SQLite configura WAL, claves foráneas, `busy_timeout` y `synchronous=FULL`.
- El gasto local usa `BEGIN IMMEDIATE` y una actualización condicional del outpoint.
- El backend exige una única fila afectada para la transición UNSPENT → SPENT.
- La solicitud de gasto tiene hash canónico con separación de dominio.
- Existe una restricción única global para la clave de idempotencia en SQLite.
- El coordinador diferencia evidencia LOCAL_ACID de NETWORK_CONSENSUS.
- El adaptador OpenSSL no incorpora silenciosamente el almacén de confianza del sistema.
- La documentación reconoce que SQLite local no representa consenso distribuido.

## 4. Bloqueos para v1.0

Los siguientes puntos impiden declarar terminada la primera versión:

| ID | Bloqueo | Evidencia / razón | Prioridad |
|---|---|---|---|
| B01 | Emisión X.509 desde CSR | El PR no agrega un servicio emisor que valide CSR, aplique un perfil y firme un certificado con una CA | CRÍTICA |
| B02 | Renovación de certificados | No existe flujo de renovación vinculado a una nueva autorización y a una transición verificable | ALTA |
| B03 | Revocación y suspensión persistentes | El adaptador X.509 consulta una CRL suministrada; no administra estados ni genera/publica CRL | CRÍTICA |
| B04 | Recibos firmados | SQLite guarda un JSON y su SHA-256; ese hash no es una firma criptográfica del emisor | CRÍTICA |
| B05 | Anti-replay persistente | `ChallengeRegistry` mantiene IDs en memoria; un reinicio pierde ese registro | ALTA |
| B06 | Máquina de estados de ejecución | El coordinador consume y verifica commit, pero no implementa executor, outbox ni recuperación del efecto externo | CRÍTICA |
| B07 | Recuperación tras reinicio | Las pruebas actuales no demuestran recuperación de una operación interrumpida entre gasto y efecto externo | ALTA |
| B08 | Validación de restricciones | `constraints` se valida como objeto, pero sus reglas no se aplican en la evaluación de autorización | ALTA |
| B09 | Semántica de firmas requeridas | `required_signatures` se comprueba como lista no vacía; el flujo no implementa un verificador general de cada requisito declarado | ALTA |
| B10 | Pruebas multiproceso | La prueba concurrente observada usa hilos; falta competencia entre procesos independientes sobre el mismo archivo SQLite | ALTA |
| B11 | Registro confiable de autorizaciones | El backend documenta que el caller debe validar la autorización antes de registrarla; falta una fachada de servicio que imponga y pruebe ese límite | ALTA |
| B12 | Versionado de producto | El protocolo declara `1.0`, el PR se titula v1.1 y la arquitectura está en revisión 1.2; falta una matriz explícita de versión de protocolo, adapter, esquema y release | ALTA |

## 5. Límites que deben conservarse

- No se debe presentar `LOCAL_ACID` como finalidad de consenso.
- No se debe implementar un adapter Network fingiendo consenso con SQLite, locks locales o memoria.
- No se debe ejecutar una operación externa antes de que el backend confirme y verifique el commit requerido.
- Después de consumir una autorización, un fallo externo no debe restaurar el UTXO automáticamente.
- Un recibo local verificable debe incluir una firma verificable con una clave pública confiable, no solamente un hash almacenado junto al JSON.
- La validez X.509 y la autorización NODE son controles distintos; el segundo nunca debe convertir un certificado inválido en válido.

## 6. Secuencia de trabajo para completar v1.0

1. Congelar un perfil v1.0 pequeño: CA emisora única, CSR, emisión, renovación, revocación, suspensión/liberación, SQLite local y validación independiente.
2. Definir el modelo persistente de certificados, operaciones, desafíos, idempotencia y recibos mediante migraciones versionadas.
3. Implementar una fachada de servicio que valide binding, autorización, firmas requeridas y política antes de registrar o consumir una capacidad UTXO.
4. Implementar el ciclo de ejecución recuperable: ACCEPTED → SPENT → EXECUTING → COMMITTED / FAILED_REQUIRES_REVIEW.
5. Implementar emisión desde CSR con validación de firma del CSR, perfil permitido, SAN/EKU/KeyUsage, vigencia subordinada a la CA y serial único.
6. Implementar renovación y cambios de estado como operaciones administrativas autorizadas, con historial inmutable.
7. Implementar recibos firmados y un verificador independiente.
8. Agregar pruebas de multiproceso, repetición después de reinicio y fallos entre consumo y ejecución.
9. Ejecutar CI completa, revisar los artefactos y emitir el certificado de alcance v1.0 únicamente con evidencia PASS.

## 7. Criterio de estado

- **Implementado:** existe código ejecutable para el comportamiento.
- **Probado:** existen pruebas automáticas que cubren el comportamiento declarado.
- **Verificado:** una prueba independiente valida la salida o evidencia.
- **Pendiente:** falta código, prueba o verificación.
- **Excluido de v1.0:** se reserva para versiones posteriores y no puede anunciarse como incluido.

## 8. Dictamen

El PR #227 aporta una base inicial aprobada por su workflow local de conformidad. No está listo para emitir NODE-PKI-GUARD v1.0 porque todavía faltan emisión X.509, gestión real del ciclo de vida, recibos firmados, anti-replay durable y ejecución recuperable.

La siguiente prioridad de implementación es el **servicio de ciclo de vida y ejecución de operaciones PKI**, después de fijar el modelo persistente y sus contratos. No se recomienda ampliar OCSP, CA subordinadas ni Network antes de cerrar ese flujo Standalone.

---

**Auditoría inicial — NODE-PKI-GUARD v1.0**  
**NODE Core OS byLAEV**

## 9. Follow-up implementation — constrained X.509 issuance primitive

After the initial audit, the branch received:

- `node_core/security/node_pki_guard_issuer.py`: a constrained PKCS#10 CSR issuance primitive.
- `tests/test_node_pki_guard_issuer.py`: 14 positive and negative issuer tests.
- Updated local conformance workflow to execute the issuer tests and compile the new module.
- Updated implementation contract documenting the issuer's security boundary.

The issuer verifies CSR proof-of-possession, a pinned self-signed CA certificate, CA BasicConstraints and KeyUsage, CA private-key correspondence, SAN allowlists, permitted key algorithms, profile-controlled extensions and certificate validity bounds.

**This does not close B01 as a complete PKI service.** The primitive is not yet connected to binding/authentication validation, required-signature enforcement, UTXO authorization consumption, durable idempotency, certificate persistence, revocation state, operation recovery or signed administrative receipts. It must not be exposed as a production issuance endpoint.

The 14 tests have been added to GitHub Actions, but their execution result must be confirmed from the workflow run for the latest branch commit. Until then, the new issuer is **implemented, awaiting CI verification and integration**.

The next implementation unit is the PKI application service and durable lifecycle repository. It must enforce authorization before issuance, persist the exact result under an idempotency key, and recover safely after a process restart. A consumed UTXO must never be restored automatically when certificate issuance or persistence fails.
