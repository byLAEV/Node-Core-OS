# Arquitectura HUC 0.6

## Diagrama lógico

```text
          INSTITUCIÓN A       INSTITUCIÓN B
          clave privada A     clave privada B
                \                 /
                 \               /
                 PROPUESTA / VOTOS FIRMADOS
                          |
                 cualquier participante
                    ensambla COMMIT
                          |
                3 firmas de 4 validadores
                          |
          +---------------+---------------+
          |               |               |
       NODO A          NODO B          NODO C          NODO D
       aplica           aplica          aplica          aplica/sync
          |               |               |               |
          +---------------+---------------+---------------+
                          |
                 ESTADO REPLICADO HUC
```

No existe un coordinador permanente ni una réplica que tenga autoridad unilateral para definir el orden. Una propuesta contiene el hash del estado padre y la secuencia siguiente; el commit necesita un certificado de quórum verificable por cualquier réplica.

## Capas

1. **X.509:** identidad y clave pública del sujeto bajo la CA fijada.
2. **HUC-CC:** autorización y política de consenso vinculadas al certificado por hash.
3. **HUC-RSP:** propuestas, votos, certificados de commit y replicación entre instituciones.
4. **Estado UTXO lógico:** máquina determinista ISSUE/RENEW/REVOKE.
5. **Verificador local:** verifica CA, X.509, HUC-CC, commit y estado replicado.

## Por qué cuatro nodos y tres firmas

Para tolerancia bizantina `f=1`, el perfil usa `n=3f+1=4` y `q=2f+1=3`. Dos quórums de tamaño tres sobre cuatro validadores siempre comparten al menos dos nodos. Si como máximo uno es bizantino y cada validador honesto persiste un solo voto por slot, dos propuestas contradictorias no pueden obtener ambos certificados de commit.

## No hay autoridad de ordenamiento única

- Cualquier cliente/nodo puede proponer.
- Cada nodo vota independientemente contra su estado local.
- Cualquier nodo puede ensamblar el commit a partir de votos.
- Cada réplica aplica el mismo objeto de commit y reproduce el mismo estado.
- Una réplica atrasada obtiene el historial desde otro par y verifica todo antes de aceptar.

El nodo que reúne los votos es un agregador de mensajes, no una autoridad de secuenciación. No puede crear un commit sin las firmas de quórum.

## Supuesto de seguridad

El mecanismo es un certificado de quórum con anti-equivocación persistente. No implementa todas las fases de PBFT/HotStuff ni view-change. La seguridad descrita se limita al modelo estático de miembros, claves no comprometidas por encima de `f`, votos durables y quórums definidos. Si hay división de votos, el sistema se detiene de forma segura en vez de desbloquear automáticamente.

## Transporte y replicación

El protocolo serializa las propuestas, votos, commits y paquetes de estado en JSON/ZIP. Los archivos pueden circular por cualquier canal. En 0.6 no se implementa un servicio de red ni P2P; la replicación es real a nivel de estado persistido en diferentes directorios/servidores, pero el transporte se hace mediante paquetes exportados/importados.

## Evidencia y verificación

El manifiesto público de red puede incluir el certificado CA y política HUC-CC. Ese manifiesto es fijado por SHA-256 fuera de banda. En modo PKI, cada validador comprueba de forma independiente X.509 y HUC-CC antes de votar. El commit de HUC-RSP requiere por separado 2f+1 validadores de estado.
