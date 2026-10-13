# Node Core OS P2P Contracts — auditoría técnica y plan de implementación

- **Estado:** documento de planificación; no es una implementación.
- **Aplicación prevista:** Node Core OS P2P Contracts.
- **Alcance actual:** auditoría de interfaces existentes y preparación de la primera versión.
- **HashPaper:** fuera del alcance funcional de este trabajo. Su código, formatos, pruebas, instalación y actualización no deben modificarse como parte de P2P Contracts.

## 1. Control previo: estado de HashPaper

El aviso de desarrollo de HashPaper se incorporó a `applications/hashpaper/README.md` mediante el pull request #77, fusionado en `main` el 12 de octubre de 2026. El cambio fue únicamente documental.

Los siete checks consultados para el commit de la rama de documentación finalizaron con `success`, incluidos los tests de HashPaper en Python 3.10, 3.11, 3.12 y 3.13, los tests de terminal GNU/Linux y dos pruebas de instalación de Ubuntu 24.04. Esto valida los checks de ese commit; no constituye una auditoría completa de HashPaper ni de P2P Contracts.

## 2. Hallazgos confirmados del repositorio

### 2.1 Plataforma y dependencias

- `docs/DEVELOPMENT.md` y `docs/DEPENDENCIES.md` establecen GNU/Linux en terminal como entorno soportado.
- Python 3.10+ es la base declarada; CI valida varias versiones, incluida 3.12.
- El runtime de Node Core OS declara uso de la biblioteca estándar de Python y no depende actualmente de paquetes Python de terceros.
- Termux/Android no es una plataforma oficialmente soportada por el contrato actual del repositorio. Cualquier adaptación deberá evaluarse por separado, no darse por garantizada.

### 2.2 Almacenamiento local

`node_core/storage.py` contiene `StorageManager`, con inicialización, resolución segura de rutas relativas, lectura, escritura y eliminación. La resolución comprueba que la ruta no escape del almacenamiento raíz.

P2P Contracts debe reutilizar el almacenamiento configurado por Node Core OS cuando sea apropiado. No debe inventar rutas absolutas ni escribir fuera de la raíz gestionada.

### 2.3 Contenido, CID y Kubo/IPFS

`node_core/content.py` contiene `ContentRegistry` y `ContentManager`. Las operaciones expuestas incluyen añadir contenido, recuperar por CID a un destino, pin/unpin, publicar/despublicar, compartir referencias, consultar registros y listar contenido.

`node_core/ipfs.py` contiene `KuboManager`, con operaciones de servicio Kubo, `add_file`, `cat`, pin/unpin y listado de pins.

Consecuencias de diseño:

- Preferir `ContentManager` para operaciones de contenido de la aplicación, en lugar de usar el RPC administrativo de Kubo directamente desde P2P Contracts.
- Revisar el comportamiento exacto de las interfaces antes de invocarlas; sus nombres no sustituyen la validación de entradas y resultados.
- Distinguir entre guardar localmente, añadir a IPFS, registrar un CID, publicar una referencia y fijar contenido.
- No afirmar que el contenido está fijado o publicado si la operación correspondiente no lo confirma.
- No usar el registro local como prueba de que el contenido sigue disponible en la red.

### 2.4 Identidad

`node_core/identity/profile.py` implementa almacenamiento local de un perfil de identidad declarada. El propio módulo indica que los datos no se publican desde ese almacén y que los valores introducidos no se verifican como verdaderos.

El Peer ID de Kubo identifica un nodo técnico. El perfil declarado, el Peer ID y una clave OpenPGP son conceptos distintos; P2P Contracts deberá definir cómo se vinculan sin afirmar verificación civil que no existe.

### 2.5 Red

`node_core/network.py` proporciona identidad de nodo, listado de pares conectados, estado de red y conexión a un par mediante una multiaddress. `docs/BASIC_NODE_NETWORK.md` advierte que la conectividad y el ping no son mensajería autenticada de aplicación ni un protocolo de consenso.

Por tanto, P2P Contracts no debe asumir que la conectividad básica propaga automáticamente solicitudes o manifiestos. La recuperación y la publicación de documentos deben implementarse y probarse explícitamente.

### 2.6 API pública

`docs/API-CONTRACT.md` define un contrato propuesto, no una API pública ya implementada. No debemos depender de endpoints hipotéticos. La integración inicial debe usar interfaces existentes verificadas o proponer una ampliación separada con sus pruebas.

### 2.7 HashPaper

HashPaper dispone de una aplicación integrada, un manifiesto funcional detallado y adaptadores propios. La arquitectura describe paquetes transparentes que incluyen el texto original y señala que el cifrado no está implementado.

Esta información se registra únicamente como contexto de auditoría. No se debe reutilizar HashPaper como núcleo de P2P Contracts ni modificarlo para desarrollar la nueva aplicación.

## 3. Diseño de la primera versión

La versión inicial de P2P Contracts será transparente y estará orientada a demostrar el funcionamiento y la trazabilidad con datos de prueba. Las solicitudes, respuestas, propuestas, aceptaciones y evidencias seleccionadas se publicarán abiertamente.

Usar identidades ficticias y operaciones simuladas al principio. No publicar claves privadas, credenciales, secretos ni datos personales reales. Una vez distribuido contenido en IPFS, eliminar una referencia local no garantiza que desaparezcan las copias distribuidas.

### 3.1 Documentos separados

El protocolo deberá definir como mínimo:

1. Solicitud.
2. Respuesta vinculada a una solicitud.
3. Propuesta vinculada a la solicitud y, cuando corresponda, a una respuesta.
4. Aceptación explícita de una versión concreta de propuesta.
5. Evidencia de ejecución, clasificada como declaración o verificación.
6. Manifiesto de estado publicado de la aplicación.

No sobrescribir silenciosamente documentos históricos. Una modificación debe generar una nueva revisión con referencia al antecedente.

### 3.2 Manifiesto general de estado

El manifiesto sirve para comunicar a la red general de Node Core OS el estado publicado de P2P Contracts y las necesidades públicas seleccionadas que los participantes quieren dar a conocer. No es una votación ni una aprobación colectiva de contratos.

El manifiesto debe referenciar documentos públicos seleccionados, no copiar todos los expedientes operativos. Los nodos generales deben poder conservar y verificar el manifiesto sin instalar la aplicación ni descargar todas las solicitudes y negociaciones.

Campos a especificar antes de implementar: versión de esquema, versión de aplicación, secuencia, referencia al manifiesto anterior, referencias a actualización, solicitudes públicas seleccionadas, evidencias seleccionadas, autor/procedencia, fecha y firma.

### 3.3 Integridad y firma

Antes de incorporar OpenPGP, especificar la representación exacta de los documentos que se firma y probar una serialización estable. Una firma válida acredita la firma de una clave, no por sí sola la identidad civil del titular ni la ejecución de una transacción.

Las claves privadas permanecen locales. La biblioteca OpenPGP se seleccionará solo tras comprobar mantenimiento, licencia, compatibilidad con la plataforma objetivo y casos de prueba.

### 3.4 Versiones y sincronización

No elegir el manifiesto más reciente únicamente por timestamp. Usar secuencia y referencia al anterior; verificar CID/contenido, firmas y procedencia; detectar conflictos entre manifiestos. Si no se puede comprobar el estado más reciente, informar sincronización parcial o pendiente, no sincronización completa.

## 4. Secuencia de desarrollo recomendada

### Fase 0 — Auditoría de interfaces
- Leer la implementación completa y las pruebas de `StorageManager`, `ContentManager`, `KuboManager`, identidad y red.
- Identificar cómo se inicializan y obtienen estas dependencias desde el runtime.
- Confirmar las operaciones de contenido y sus errores.
- Entregable: tabla de interfaces, precondiciones, resultados y pruebas existentes.

### Fase 1 — Esquemas documentales
- Definir esquemas JSON versionados y ejemplos válidos/ inválidos.
- Definir identificadores, referencias, estados y transiciones permitidas.
- Especificar manifiesto, secuencia y reglas de conflicto.
- Entregable: especificación antes del código.

### Fase 2 — Motor local
- Crear y validar solicitudes, respuestas, propuestas, aceptaciones y evidencias ficticias.
- Guardar los documentos usando el almacenamiento configurado.
- Crear un índice local reconstruible y conservar historial.
- Añadir pruebas unitarias para datos inválidos y referencias inexistentes.

### Fase 3 — Publicación distribuida
- Publicar documentos mediante la capa de contenido existente.
- Recuperarlos por CID y comprobar que el contenido corresponde al documento esperado.
- Probar pinning y fallos de Kubo.
- Evitar estados de éxito falsos cuando una operación falla a mitad del flujo.

### Fase 4 — Manifiesto de estado
- Generar y publicar el primer manifiesto.
- Generar versiones posteriores enlazadas a la anterior.
- Validar cada referencia y detectar secuencias conflictivas.
- Mantener los documentos operativos separados del manifiesto general.

### Fase 5 — OpenPGP
- Elegir la biblioteca después de evaluar compatibilidad y mantenimiento.
- Definir la canonicalización y el contenido firmado.
- Firmar y verificar documentos.
- Probar firma inválida, documento alterado y clave desconocida.

### Fase 6 — Sincronización
- Recuperar manifiestos candidatos, verificar su contenido y procedencia.
- Seguir referencias anteriores y detectar conflictos.
- Recuperar los documentos necesarios para el ámbito del nodo.
- Registrar estados sincronizado, parcial, pendiente, conflicto o error.

### Fase 7 — Prueba de tres nodos
- Nodo A publica solicitud pública.
- Nodo B descubre y responde.
- A publica una propuesta; las partes registran sus decisiones.
- Se añade evidencia simulada de ejecución.
- Se publica un nuevo manifiesto.
- Nodo C, sin instalar P2P Contracts, descubre las referencias públicas seleccionadas y verifica el manifiesto.

### Fase 8 — Instalación y actualización
- Solo después de pasar las pruebas funcionales, integrar la aplicación con el sistema de distribución.
- Comprobar que los datos existentes, el repositorio Kubo y HashPaper permanecen intactos.
- Documentar instalación, actualización, rollback y errores.

## 5. Pruebas mínimas de aceptación

- Un documento inválido se rechaza antes de publicarse.
- Una respuesta no puede referenciar una solicitud inexistente.
- Una aceptación referencia una propuesta concreta e inmutable.
- Una publicación fallida no se reporta como exitosa.
- Un documento recuperado se verifica contra su CID y su esquema.
- Un manifiesto con referencia ausente o firma inválida se rechaza.
- Una bifurcación de secuencia se informa, no se resuelve silenciosamente.
- El nodo general puede recuperar el manifiesto sin descargar el expediente completo.
- El nodo participante puede reconstruir la secuencia pública de solicitud a evidencia.
- La falta de conexión produce estado parcial/pendiente.
- Las pruebas no utilizan fondos reales.
- La instalación y actualización no alteran HashPaper ni sus datos.

## 6. Límites y decisiones pendientes

Antes de escribir la aplicación, la siguiente tarea es cerrar la Fase 0 y luego aprobar los esquemas de la Fase 1. Se completó una revisión adicional de `node_core/runtime.py`, `node_core/config.py`, `node_core/evidence.py` y las pruebas `tests/test_runtime.py`, `tests/test_network.py`, `tests/test_ipfs_daemon.py` y `tests/test_identity_profile.py`. `NodeRuntime` inicializa y expone `config`, `storage`, `kubo`, `network`, `content`, `evidence` e interfaces de identidad; `ContentManager` se construye con `KuboManager`, `StorageManager` y la gateway configurada. Hay pruebas unitarias con Kubo simulado para contenido y evidencia, pruebas de red con Kubo simulado y pruebas de almacenamiento del perfil. La aplicación deberá obtener las interfaces desde la integración de runtime prevista, sin crear otra instancia independiente de Kubo ni acceder directamente al RPC administrativo.

No se afirma que P2P Contracts, sus manifiestos, OpenPGP ni su sincronización ya existan. Este documento fija la auditoría inicial y el orden de trabajo para construirlos mediante cambios pequeños y verificables.

## 8. Alcance de la versión inicial y política OpenPGP futura

La primera versión funcional de P2P Contracts será exclusivamente pública y transparente. Primero se implementarán y probarán las solicitudes, respuestas, propuestas, aceptaciones, evidencias, publicación y trazabilidad entre nodos. La primera versión no tendrá modo privado funcional, no requerirá importar claves y no integrará OpenPGP para comunicaciones. La opción privada se pospone hasta que la modalidad pública funcione y el usuario autorice expresamente comenzar esa fase.

Para la futura modalidad privada, Node Core OS y P2P Contracts no generarán claves privadas nuevas. La opción preferida es que el usuario introduzca o cargue una clave privada OpenPGP existente cada vez que la operación lo necesite, sin almacenamiento persistente. La clave se procesará temporalmente en memoria durante el tiempo mínimo posible y no se copiará a archivos temporales, logs, manifiestos ni IPFS. La contraseña de desbloqueo, si existe, también se solicitará de forma segura y no se almacenará.

Antes de implementar se comprobará que la biblioteca elegida admite ese flujo y se documentarán sus límites de gestión de memoria. No se prometerá que el lenguaje puede borrar todas las copias de memoria de forma perfecta. Un fingerprint/hash de la clave privada sirve para identificar o comparar la clave, pero no permite firmar ni descifrar y no sustituye la clave privada.

En la futura opción privada, los contactos se añadirán mediante claves públicas OpenPGP existentes, validadas y mostradas por fingerprint. La comunicación privada se cifrará para las claves públicas de los destinatarios antes de transmitirla o publicarla en IPFS. Si se requiere firma de autoría, se usará la clave privada existente que el remitente aporte para esa operación. No habrá fallback a texto claro: si falla el cifrado, no se envía el mensaje.

Esta fase privada queda fuera de la implementación actual. La modalidad pública no debe manejar claves privadas y debe advertir claramente que el contenido publicado es público. HashPaper permanece fuera de alcance y no se modifica.

## 9. Regla de no regresión de HashPaper

Durante el desarrollo de P2P Contracts:

- No modificar el código fuente de HashPaper.
- No cambiar sus formatos documentales.
- No cambiar sus pruebas, dependencias, instalador ni actualizador.
- No cambiar ni borrar los datos locales de HashPaper.
- Cualquier necesidad de integración se debe plantear como cambio separado y requerirá autorización y pruebas de regresión explícitas.
