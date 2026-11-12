# LAEV HUC 0.7 — Arquitectura

## Diagrama de componentes

```text
        INSTITUCIÓN A             INSTITUCIÓN B
     clave Ed25519 privada     clave Ed25519 privada
              \                    /
               \                  /
                +--- HUC PEER TCP-+
                |                 |
          INSTITUCIÓN C       INSTITUCIÓN D
       clave Ed25519 privada  clave Ed25519 privada
                |                 |
                +--------+--------+
                         |
       +-----------------+------------------+
       |                 |                  |
   HUC-RSP            HUC-VIEW           HUC-MEMBERSHIP
   ISSUE/RENEW/       cambio de vista    altas/retiros y
   REVOKE + commit    recuperación       epoch handoff
       |                 |                  |
       +-----------------+------------------+
                         |
                 ESTADO UTXO REPLICADO
                         |
             verificador X.509 + HUC-CC
```

## Componentes

1. **X.509:** identidad/atributos y clave pública del titular.
2. **HUC-CC:** política y autorizaciones complementarias.
3. **HUC-RSP:** propuesta, voto, commit, secuencia y estado UTXO lógico.
4. **HUC-Peer:** transporte TCP, sobres firmados, anti-replay y distribución.
5. **HUC-View:** cambio de vista firmado, rotación del proponente y preservación de lock.
6. **HUC-Membership:** prueba de posesión, voto del comité anterior, certificado de membresía, checkpoint y nueva época.

## Descentralización lograda

- Ninguna clave privada de validador abandona el nodo que la creó.
- El peer transporta mensajes firmados, no toma decisiones de confianza en lugar de los validadores.
- Cualquier participante puede iniciar el ciclo de propuesta; el proponente primario cambia por vista para operaciones normales.
- Cualquier nodo puede agregar votos y propagar el certificado de commit.
- Cada réplica valida localmente y conserva su propio estado.
- El alta/retiro está autorizado por el quorum de la red anterior y conserva el checkpoint.

## Perfil 4/3

El comité de cuatro usa `f=1`, quorum `2f+1=3`. Un nodo caído permite continuar con los otros tres. Dos nodos caídos impiden el quorum. Los supuestos dependen de claves protegidas, manifiesto fijado, anti-equivocación persistente y no más de un validador bizantino.

## View Change conservador

La rotación del proponente requiere tres mensajes firmados. Los locks se incluyen en los mensajes; un lock común se lleva a la nueva vista y se completa antes de otra propuesta normal. Locks incompatibles provocan detención segura. No se eliminan por timeout. Esto es una capa de recuperación de laboratorio y no debe describirse como PBFT/HotStuff completo.

## Membresía por epoch

El comité actual aprueba una red sucesora. Para `n=4`, se requiere mantener cuatro validadores: la demo reemplaza A por E. El certificado de membresía incluye la propuesta, votos, red destino y checkpoint. Los nodos retenidos reciben el paquete sobre P2P; el nuevo miembro lo recibe mediante una invitación autenticada porque no pertenece a la red anterior.

## Transporte y seguridad

El P2P es TCP con mensajes JSON, firmas Ed25519 y anti-replay. La firma de aplicación garantiza integridad/autenticidad del mensaje de validador, no confidencialidad. Para enlaces no confiables usar TLS o VPN. Se recomienda mTLS en despliegue real. El peer map y la red deben fijarse por hashes mediante un canal separado.

## Fuera de alcance

No hay blockchain, token, tarifa, minería, consenso PoW, descubrimiento descentralizado, NAT traversal, relays, BFT completo ni formalización matemática. El prototipo no ha sido sometido a auditoría externa ni probado en instituciones reales.
