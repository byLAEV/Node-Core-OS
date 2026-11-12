# LAEV HUC-RSP 0.7 — Peer, View Change and Membership Protocol

## 1. Objetivo

HUC 0.7 añade transporte P2P directo, recuperación conservadora de vista y cambio autenticado de membresía al estado replicado UTXO lógico de HUC. No utiliza blockchain, minería, token ni tarifa de protocolo.

El transporte puede mover propuestas, votos, commits, mensajes de cambio de vista, solicitudes de membresía, paquetes de membresía y estados replicados. Las decisiones de validez siguen dependiendo de firmas, manifiestos fijados, reglas de transición y quórums; el peer que transporta un mensaje no se convierte por eso en autoridad.

## 2. Identidad, red y peer map

Cada validador tiene un ID, una clave Ed25519 privada local y un descriptor público. Un manifiesto de red fija:

- `network_id`, `membership_epoch`, conjunto de validadores;
- hashes/keys públicas de cada validador;
- `fault_tolerance=f` y `quorum=2f+1`;
- cuando se configura PKI, la CA X.509 y la política HUC-CC.

El manifiesto se fija mediante SHA-256 distribuido por canal externo. Un peer map separa identidad de red: enlaza cada validator ID con host y puerto. También se valida y se fija localmente mediante su SHA-256.

El peer map no sustituye la confianza del manifiesto. Ambos pins deben distribuirse por un canal institucional autenticado, no aceptar ciegamente el valor recibido desde el mismo peer que se está verificando.

## 3. Transporte de mensajes

El transporte 0.7 utiliza TCP y mensajes JSON con delimitación newline. Cada sobre contiene payload firmado Ed25519 con separación de dominio, identidad de origen, tipo de mensaje, ID único, marca temporal, destino lógico y cuerpo. El receptor:

1. limita tamaño y tiempo de lectura;
2. valida que el origen pertenece al manifiesto vigente;
3. verifica la firma del sobre;
4. rechaza ID de mensaje repetido mediante caché anti-replay;
5. valida y ejecuta el tipo de mensaje;
6. firma la respuesta.

Tipos de mensajes principales:

| Mensaje | Función |
|---|---|
| `PING` | Estado y vista del peer |
| `PROPOSAL` | Verificar propuesta y emitir voto |
| `COMMIT` | Validar y aplicar commit |
| `VIEW_CHANGE_REQUEST` | Solicitar mensaje firmado de nueva vista |
| `NEW_VIEW_CERTIFICATE` | Instalar certificado de vista |
| `STATE_EXPORT` / `STATE_SYNC` | Exportar y sincronizar estado |
| `MEMBERSHIP_PROPOSAL` | Validar propuesta y votar el cambio de comité |
| `MEMBERSHIP_STAGE` | Recibir y validar paquete de transición |

La firma de aplicación autentica el mensaje y protege su integridad; no cifra el contenido. Para transporte por redes no confiables se configura TLS o una VPN. El servidor no permite bind remoto sin TLS, salvo opción explícita para una VPN/red privada de laboratorio. TLS proporciona confidencialidad e integridad del canal y autenticación del servidor según la configuración PKI; en despliegues interinstitucionales se recomienda autenticación mutua TLS además de las firmas Ed25519 de aplicación.

## 4. Peer communication y operación

El peer map incluye un endpoint por miembro de la época vigente. Cada nodo inicia un servidor TCP y puede contactar directamente a cualquier otro. No existe nodo relay o servidor central obligatorio. El proponente es una función de protocolo, no una autoridad permanente: los pares validan su firma y su derecho a proponer en la vista actual.

Para un commit:

1. El proponente crea una propuesta vinculada al `network_id`, vista, secuencia, hash padre, X.509 y HUC-CC.
2. La difunde por TCP.
3. Cada peer verifica la vista, el estado local, el certificado, las reglas UTXO y cualquier pin de confianza antes de votar.
4. El proponente/cliente reúne firmas distintas hasta `2f+1`.
5. Se ensambla un certificado de commit y se difunde a todos los peers disponibles.
6. Cada peer valida el commit de forma independiente y aplica localmente.

El nodo que reúne firmas solo agrega evidencia existente; no puede crear un commit sin quórum.

## 5. Estado UTXO lógico

| Operación | Entrada | Salida | Resultado |
|---|---|---|---|
| ISSUE | Ninguna | Outpoint nuevo | ACTIVE |
| RENEW | Outpoint anterior activo | Outpoint nuevo | Anterior SUPERSEDED; nuevo ACTIVE |
| REVOKE | Outpoint activo | Ninguna | REVOKED |

El historial sigue siendo append-only. La salida consumida permanece representada por la operación que la consumió y no se elimina del historial.

## 6. View Change 0.7

### 6.1 Propósito

Si el proponente preferido no responde, los validadores pueden emitir mensajes firmados `VIEW_CHANGE` hacia `view+1`. El certificado de vista requiere quórum `2f+1` de mensajes válidos que coincidan en red, vista destino y cabeza comprometida. El nuevo proponente se elige determinísticamente sobre la lista ordenada de IDs:

`primary(view) = sorted(validators)[view mod n]`.

El certificado de vista se propaga a los peers y cada réplica lo verifica antes de instalarlo.

### 6.2 Recuperación conservadora

Cada mensaje incluye secuencia/hash de cabeza y, si existe, el lock local de la siguiente propuesta: ID, voto firmado y propuesta. Si los mensajes del quórum contienen un único lock compatible, la propuesta se conserva como `recovery_proposal_id` y debe completarse antes de aceptar otra operación normal. Si aparecen locks incompatibles, el sistema se detiene y requiere reconciliación manual; no descarta locks ni libera votos por expiración simple.

### 6.3 Límite

Este View Change es una recuperación conservadora de laboratorio, no una implementación completa de PBFT, Tendermint o HotStuff. No define todas las fases prepare/commit, certificados prepared completos, elección segura de propuesta entre múltiples niveles de preparación, timeouts adaptativos ni pruebas formales. Los protocolos PBFT requieren transportar y verificar evidencia preparada al cambiar de vista; HUC debe desarrollar esa especificación y auditarla antes de declarar BFT completo.

## 7. Membership Protocol

### 7.1 Solicitud de incorporación

El nodo nuevo genera su propia clave Ed25519 y un descriptor público. Firma una solicitud de incorporación con nonce, ID de red y época: prueba posesión de su clave privada. La clave privada nunca se envía a los miembros actuales.

### 7.2 Propuesta y voto

Un validador de la red actual propone altas y/o retiros. La propuesta incorpora:

- red anterior y epoch actual;
- snapshot y hash del estado comprometido;
- altas, solicitudes de incorporación y prueba de posesión;
- retiros;
- membresía objetivo, tolerancia y quórum objetivo.

Cada miembro actual valida el mismo estado, red, pruebas de posesión y cardinalidad de la nueva membresía. Cada miembro registra anti-equivocación por epoch de membresía y firma un voto. El paquete se certifica con quórum del comité anterior.

### 7.3 Cardinalidad y checkpoint

El perfil mantiene `n=3f+1`. Para cuatro miembros, un reemplazo A por E mantiene cuatro miembros y `f=1`, quorum 3. Agregar un único miembro sin retiro produciría cinco validadores y se rechaza por el perfil actual. La transición certificada contiene red anterior, red objetivo, quorum previo y checkpoint del estado.

### 7.4 Distribución y activación

El proponente difunde la propuesta por P2P; los nodos responden con votos. Una vez ensamblado el certificado de membresía, el paquete se distribuye por P2P a los nodos retenidos, que lo guardan en su inbox. Los miembros retenidos activan localmente el nuevo epoch. El nuevo miembro, que todavía no forma parte del peer map anterior, recibe el paquete completo mediante un canal de invitación autenticado y ejecuta `join-successor`. El miembro retirado no puede activar la red sucesora.

### 7.5 Continuidad

La nueva época conserva el snapshot/checkpoint anterior y continúa la secuencia de commits; las salidas UTXO no se recrean ni pierden su historial.

## 8. Quórum y tolerancia

Perfil inicial: `n=3f+1`, `q=2f+1`. Para `n=4`, `f=1`, `q=3`. El supuesto de seguridad requiere como máximo un validador bizantino, claves no comprometidas y persistencia correcta de los bloqueos.

Tres votos de cuatro permiten progresar cuando un nodo no está disponible. Dos nodos desconectados dejan solo dos votos y no alcanzan quórum. El quórum no significa que cada operación tenga que ser aprobada por todos los miembros.

## 9. Sincronización

Un nodo solicita a un peer el estado público comprimido. El receptor valida manifiesto y epoch, checkpoint de membresía, secuencia, hash de cabeza y todos los commits. Rechaza rollback, historial divergente y red desconocida. El snapshot es una caché; la fuente verificable es la secuencia de commits firmados y los checkpoints certificados.

## 10. Límites de despliegue

- La demostración ejecuta cuatro servidores en loopback; no demuestra conectividad entre instituciones reales ni atravesamiento NAT/firewalls.
- No hay descubrimiento automático, relay ni NAT traversal. Los endpoints se registran en peer map.
- El servicio P2P requiere TLS o VPN para redes no confiables. La prueba loopback no cifra el transporte.
- View Change 0.7 solo conserva un lock común y aborta ante conflicto; no es BFT completo.
- Membership requiere una invitación autenticada para el nodo nuevo.
- No hay actualización automática del peer map desde DNS, PKI o un directorio institucional.
- El sistema no resuelve identidad civil ni políticas legales de emisión.
- No hay timestamp independiente, HSM/KMS ni revocación automática de claves de validadores.

## 11. Evolución

- 0.8: protocolo BFT completo con certificados prepared/commit, cambio de vista formal y pruebas adversariales/propiedad.
- 0.9: transporte robusto con autenticación mutua TLS, health-checks, timeouts, reconexión, NAT/relay opcional y gestión de certificados de nodos.
- 1.0: auditoría externa, formalización del protocolo, perfiles interoperables, HSM/KMS, observabilidad, recuperación ante desastres y operación interinstitucional controlada.
