# LAEV HUC-RSP 0.6 — Replicated State Protocol

## 1. Objetivo

HUC-RSP replica el estado lógico UTXO de certificados entre instituciones sin blockchain, minería, token ni comisiones de protocolo. No existe un coordinador fijo ni un líder con autoridad exclusiva de ordenamiento: cualquier participante puede proponer, cualquier validador puede votar, cualquier nodo puede ensamblar el certificado de quórum y cada réplica aplica localmente el mismo commit.

El transporte de esta versión usa archivos JSON/ZIP intercambiables por cualquier canal seguro (carpeta compartida, correo institucional cifrado, mensajería segura o API externa). El protocolo no exige un servidor de transporte central. La comunicación P2P automática queda para una versión posterior.

## 2. Perfil de membresía y quórum

La versión 0.6 utiliza un conjunto fijo de validadores:

- `n = 3f + 1` validadores.
- `q = 2f + 1` firmas distintas para un commit.
- Perfil inicial recomendado: `f = 1`, cuatro validadores y quórum de tres.
- Cada validador posee una clave privada Ed25519 propia, generada en su dispositivo.
- El manifiesto público de red fija la membresía, las claves públicas, el umbral y, en modo HUC integrado, la CA X.509 y la política HUC-CC.

Para el perfil 4/3, dos certificados de commit de propuestas contradictorias en el mismo slot tendrían al menos dos validadores en común. Bajo la hipótesis de como máximo un validador bizantino y con bloqueo persistente de voto único, al menos uno de esos validadores comunes es honesto y no firma ambas propuestas. Esta es la base de seguridad del perfil.

## 3. Ciclo de una operación

1. **Propuesta:** cualquier participante crea una propuesta con `network_id`, `epoch`, `sequence`, hash del estado padre, operación, hash X.509, hash HUC-CC y evidencia pública.
2. **Validación local:** cada validador comprueba que su estado local coincide con el padre y que la transición es válida.
3. **Voto:** el validador verifica X.509 y HUC-CC si la red está en modo PKI, y firma un mensaje con separación de dominio.
4. **Bloqueo anti-equivocación:** antes de emitir el voto, guarda de forma durable el `proposal_id` elegido para ese slot (`epoch:sequence`). No firma otra propuesta para el mismo slot.
5. **Certificado de commit:** cualquier nodo reúne `2f+1` votos Ed25519 distintos y construye un commit verificable.
6. **Aplicación:** cada réplica comprueba el commit, el quórum y el estado padre; después aplica la transición a su propio ledger.
7. **Sincronización:** una réplica atrasada importa el ledger firmado desde un par y lo reproduce desde génesis. Rechaza rollback y bifurcaciones.

No se utiliza un coordinador para decidir el orden. El orden queda determinado por el encadenamiento `sequence + previous_state_hash` aceptado mediante quórum.

## 4. Máquina UTXO lógica

| Acción | Entrada | Salida | Estado resultante |
|---|---|---|---|
| ISSUE | Ninguna | Outpoint nuevo | ACTIVE |
| RENEW | Outpoint anterior activo | Outpoint nuevo | Anterior SUPERSEDED; nuevo ACTIVE |
| REVOKE | Outpoint activo | Ninguna | REVOKED |

El identificador de salida de ISSUE/RENEW se deriva del `proposal_id` y `vout=0`. El historial es append-only. La salida consumida permanece documentada en los eventos anteriores.

## 5. Evidencia X.509 + HUC-CC

Cuando se crea la red con `--ca-certificate` y `--consensus-policy`, el manifiesto público incluye y fija por hash:

- certificado raíz X.509;
- política HUC-CC y las claves públicas de sus autoridades.

En ese perfil cada propuesta lleva el PEM X.509 y el JSON HUC-CC. Cada validador, no solamente quien propone, comprueba:

- firma X.509 bajo la CA fijada en el manifiesto;
- vigencia del X.509 y de la CA;
- hash DER del certificado;
- vinculación del HUC-CC al certificado;
- política, identificador, vigencia y umbral del HUC-CC;
- firmas de las autoridades HUC-CC.

Hay dos quórums separados: HUC-CC acredita las autorizaciones propias del certificado; HUC-RSP obtiene un commit 2f+1 de los validadores de estado. No se deben confundir.

El modo sin `pki` sirve para ensayos genéricos de estado basados en hashes. No debe utilizarse para emitir/verificar certificados HUC reales porque los validadores no inspeccionarán el contenido X.509/HUC-CC.

## 6. Anti-equivocación y seguridad de quórum

Cada nodo mantiene `vote-locks.json`. Para el mismo `epoch:sequence`, solo puede firmar un `proposal_id`. El bloqueo se escribe antes de entregar la firma y se conserva tras reiniciar el proceso.

La seguridad presupone:

- al menos `3f+1` validadores correctamente enrolados;
- como máximo `f` validadores bizantinos;
- claves privadas protegidas y claves públicas fijadas fuera de banda;
- los validadores honestos no borran ni restauran sus bloqueos de voto;
- los commits y las transiciones se verifican antes de aplicarse.

La pérdida o compromiso de un número mayor que `f` de claves invalida el modelo de confianza.

## 7. Liveness y resolución de conflictos

Esta versión prioriza seguridad y detención segura. Si dos propuestas distintas para el mismo slot reciben votos divididos (por ejemplo 2/2 en una red 4/3), ninguna obtiene quórum y los nodos honestos conservan sus bloqueos. El slot queda detenido; no se liberan votos automáticamente.

No hay todavía protocolo de view-change, recuperación BFT ni cambio automático de membresía. La recuperación requiere una procedimiento de gobernanza fuera de banda; la siguiente iteración debe especificar view-change y desbloqueo seguro antes de uso operativo.

Un nodo no disponible: los otros tres pueden seguir en el perfil 4/3. Dos nodos no disponibles: no hay quórum. Un validador bizantino más otro nodo caído puede detener el progreso aunque la seguridad se conserve.

## 8. Sincronización

Un paquete de estado contiene el manifiesto público y el ledger de commits. El nodo receptor:

1. comprueba que el manifiesto corresponde a su red fijada;
2. reproduce cada commit y verifica los votos;
3. comprueba que su historial local sea prefijo exacto del historial recibido;
4. rechaza un paquete más corto (rollback) o con otro commit en una posición ya conocida (fork);
5. actualiza el ledger y reconstruye el snapshot.

El snapshot es una caché derivada; el ledger de commits firmado es la fuente de reproducción.

## 9. Qué no es HUC-RSP 0.6

- No es una blockchain ni una cadena de bloques.
- No es una criptomoneda ni tiene tokens o tarifas.
- No implementa una red P2P o API de transporte; intercambia paquetes firmados.
- No es todavía un protocolo BFT completo con view-change y recuperación.
- No valida la identidad civil detrás del nombre del certificado; eso pertenece a la política de emisión/RA.
- No proporciona timestamp de tercero independiente.

## 10. Próxima evolución

- HUC-RSP 0.7: view-change seguro, recuperación de slots bloqueados, protocolo de membresía y pruebas de red asíncrona.
- HUC-RSP 0.8: transporte autenticado entre pares, descubrimiento y replicación automática.
- HUC-RSP 1.0: revisión formal de seguridad, RFC 8785/JCS multi-lenguaje, HSM/KMS, auditoría externa e interoperabilidad.
