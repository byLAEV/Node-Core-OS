# Node Core OS

**Node Core OS** es una infraestructura personal para que una persona pueda disponer de un núcleo propio desde el cual conservar, administrar, verificar, corroborar y utilizar sus recursos digitales, su identidad, sus registros, su evidencia y, progresivamente, su reputación.

El proyecto parte de una idea fundamental:

> **La persona debe disponer de una infraestructura propia antes de depender de aplicaciones, servicios o sistemas externos para representar quién es, qué ha hecho, qué hace o qué quiere hacer.**

Node Core OS administra dos tipos fundamentales de almacenamiento:

- **Almacenamiento local** — recursos conservados directamente en el Node.
- **Almacenamiento descentralizado** — recursos gestionados mediante tecnologías como Kubo/IPFS.

Sobre esta base pueden operar posteriormente protocolos, servicios y aplicaciones distribuidas o descentralizadas.

Pero el objetivo de Node Core OS no es únicamente almacenar archivos.

Su objetivo final es construir una **infraestructura personal de evidencia, identidad, reputación y participación**, en la que la persona conserve la capacidad de decidir qué registrar, para qué registrarlo, qué corroborar, qué compartir y cuándo utilizarlo.

---

# 1. Idea fundamental

Node Core OS no se concibe primero como una aplicación.

Se concibe como un **núcleo de infraestructura personal**.

La relación fundamental es:

```text
PERSONA
   │
   ▼
NODE CORE OS
   │
   ├── Almacenamiento local
   ├── Almacenamiento descentralizado
   ├── Registros
   ├── Evidencia
   ├── Identidad
   ├── Corroboración
   ├── Reputación
   ├── Protocolos
   └── Aplicaciones
```

La infraestructura debe existir antes de que las aplicaciones determinen cómo utilizarla.

Por eso:

> **Node Core OS no pretende definir de antemano qué debe hacer una persona. Pretende darle un lugar propio desde el cual pueda decidir qué hacer.**

---

# 2. La persona como núcleo

El Node existe para servir a una persona o entidad que decide utilizarlo.

La infraestructura debe permitir conservar una continuidad digital de aquello que la persona considere importante:

- quién es;
- qué identificadores utiliza;
- qué registros ha generado;
- qué hechos puede demostrar;
- qué actividades ha realizado;
- qué relaciones ha establecido;
- qué conocimientos o capacidades puede acreditar;
- qué reputación se ha construido en determinados contextos;
- qué quiere hacer en el futuro.

Esto no significa que Node Core OS deba publicar toda esa información.

Al contrario:

> **Conservar no significa publicar. Registrar no significa compartir. Poseer evidencia no significa estar obligado a presentarla.**

La persona debe conservar el control sobre el uso de sus registros.

---

# 3. Sistema de solicitudes

Uno de los principios fundamentales de Node Core OS es:

> **Nada debe ocurrir por decisión autónoma del sistema cuando implique representar, propagar, evaluar o utilizar información personal. Debe existir una solicitud o una autorización definida por la persona.**

La solicitud es una unidad fundamental del sistema.

Una interacción conceptual puede ser:

```text
PERSONA
   │
   │ "Necesito registrar una evidencia"
   ▼
SOLICITUD
   │
   ▼
NODE CORE OS
   │
   ├── determina qué información es necesaria
   ├── registra los datos solicitados
   ├── conserva la evidencia
   ├── solicita corroboraciones cuando corresponda
   └── prepara el resultado
   │
   ▼
RESULTADO
   │
   ▼
PERSONA
   │
   └── decide si lo utiliza, comparte o conserva
```

Una solicitud puede expresar:

- actor;
- intención;
- propósito;
- contexto;
- alcance;
- duración;
- información requerida;
- evidencia requerida;
- corroboraciones requeridas;
- política de almacenamiento;
- postura de privacidad;
- resultado esperado.

La solicitud expresa **qué quiere conseguir la persona**.

Las aplicaciones pueden generar solicitudes, pero no deben recibir por ello acceso ilimitado al Node.

---

# 4. Registros

Los registros son una pieza fundamental de la continuidad de una persona.

Un registro no debería ser tratado simplemente como un archivo.

Conceptualmente puede contener:

```text
RECORD
├── Identidad asociada
├── Intención
├── Propósito
├── Contexto
├── Importancia
├── Tiempo
├── Duración
├── Proveniencia
├── Integridad
├── Relaciones
├── Evidencia
├── Corroboraciones
└── Política de almacenamiento
```

No todos los registros necesitan tener la misma duración.

Un registro puede ser:

- temporal;
- efímero;
- persistente;
- histórico;
- archivado;
- canónico;
- derivado.

La arquitectura debe permitir que la persona determine qué registros deben permanecer y cuáles no.

---

# 5. Almacenamiento local y descentralizado

El almacenamiento es la primera infraestructura de Node Core OS.

```text
                    NODE CORE OS
                         │
                  Storage Layer
                         │
                ┌────────┴────────┐
                ▼                 ▼
          Local Storage       Kubo / IPFS
```

## Local Storage

Permite conservar directamente en el Node:

- archivos;
- configuraciones;
- claves;
- registros;
- bases de datos;
- estados;
- datos temporales;
- información privada.

## Kubo / IPFS

Kubo proporciona la implementación IPFS utilizada por Node Core OS.

Permite trabajar con:

- contenido direccionado por CID;
- almacenamiento distribuido;
- recuperación de contenido;
- pinning;
- publicación;
- intercambio entre Nodes.

Kubo es una infraestructura utilizada por Node Core OS, no la definición completa del sistema.

---

# 6. Contenido y evidencia

Un archivo puede convertirse en una referencia de contenido independiente de su ubicación local:

```text
Archivo
  │
  ▼
Add
  │
  ▼
IPFS
  │
  ▼
CID
  │
  ├── Pin
  ├── Retrieve
  ├── Publish
  └── Share
```

Esto permite que la evidencia pueda ser referenciada mediante mecanismos de integridad y contenido sin depender exclusivamente de una ruta del sistema de archivos.

Una evidencia puede posteriormente asociarse con:

- una identidad;
- una solicitud;
- un evento;
- una acción;
- un protocolo;
- un contexto;
- una corroboración.

---

# 7. Identidad

La identidad de Node Core OS no debe reducirse a un nombre de usuario.

La identidad debe poder representar una continuidad de identificadores, registros, credenciales y evidencias asociadas con una misma persona o entidad.

Conceptualmente:

```text
INDIVIDUO
   │
   ├── Identidad individual
   │
   ├── Identidad personal
   │
   └── Identidad profesional
          │
          ├── Postura pública
          └── Postura privada
```

Estas identidades no necesariamente significan personas diferentes.

Pueden representar distintas formas legítimas de la misma individualidad dentro de distintos contextos.

La arquitectura debe permitir establecer relaciones entre:

```text
Identidad
   │
   ├── Identificadores
   ├── Claves
   ├── Credenciales
   ├── Registros
   ├── Evidencias
   └── Relaciones
```

La criptografía puede demostrar control sobre un identificador o una clave.

Pero el control criptográfico, por sí solo, no demuestra que exista una única persona física detrás de todos los identificadores.

Por ello Node Core OS contempla una capa adicional de **corroboración y consistencia**.

---

# 8. Individualidad y consistencia

Una de las ideas centrales de la propuesta es que una misma identidad no debería poder recibir atribuciones mutuamente incompatibles como si todas pertenecieran a una única continuidad individual.

La identidad debe poder ser examinada mediante restricciones:

- temporales;
- espaciales;
- físicas;
- matemáticas;
- causales;
- lógicas;
- contextuales.

Ejemplo conceptual:

Si una misma identidad aparece realizando una actividad físicamente incompatible con otra actividad atribuida a esa misma identidad en el mismo intervalo temporal, existe una contradicción que debe ser investigada.

```text
IDENTIDAD
   │
   ├── Evento A
   │      │
   │      └── ubicación / tiempo
   │
   └── Evento B
          │
          └── ubicación / tiempo
                 │
                 ▼
             CONSISTENCIA
                 │
          ┌──────┴──────┐
          ▼             ▼
      Compatible    Contradicción
```

Esto no significa que las leyes físicas por sí solas demuestren quién es una persona.

Significa que pueden funcionar como una **capa de detección de contradicciones y corroboración**.

La finalidad es impedir que el sistema acepte como coherente una historia de identidad que contiene hechos imposibles o incompatibles.

---

# 9. Evidencia

La evidencia es la relación entre una afirmación y los registros que permiten sostenerla.

Una cadena conceptual puede ser:

```text
IDENTIDAD
   ↓
REGISTRO
   ↓
EVIDENCIA
   ↓
CORROBORACIÓN
   ↓
CONSISTENCIA
   ↓
HISTORIA
   ↓
REPUTACIÓN
```

La arquitectura debe poder responder preguntas como:

- ¿Qué se afirma?
- ¿Quién lo registró?
- ¿Cuándo se registró?
- ¿Cuál es su origen?
- ¿Qué evidencia existe?
- ¿Qué identidad está asociada?
- ¿Quién lo corroboró?
- ¿En qué contexto?
- ¿Existen contradicciones?
- ¿Sigue siendo válido?

La reputación no debería aparecer mágicamente como un número.

Debe poder derivarse de una historia de evidencia.

---

# 10. Reputación

Node Core OS distingue:

```text
IDENTIDAD
    │
    └── ¿Quién?

EVIDENCIA
    │
    └── ¿Qué puede demostrarse?

REPUTACIÓN
    │
    └── ¿Qué puede inferirse sobre el historial en un contexto?
```

La reputación no debe ser necesariamente una puntuación universal.

Puede existir una reputación contextual:

- personal;
- profesional;
- contractual;
- de servicio;
- de participación;
- de confiabilidad;
- de cumplimiento;
- de actividad en un protocolo.

Por tanto:

> **La reputación pertenece al contexto y debe poder ser explicada mediante evidencia.**

Una reputación puede ser aceptada por un sistema y no necesariamente por otro.

Node Core OS no pretende convertirse en un juez universal de reputación.

---

# 11. Corroboración distribuida

La red de Node Core OS puede utilizar otros Nodes para corroborar información.

La idea no es:

> "La red decide quién eres."

La idea es:

> **"La red permite comprobar qué evidencia existe sobre una identidad y qué otros Nodes pueden corroborarla."**

Conceptualmente:

```text
IDENTIDAD
   │
   ▼
Solicitud de corroboración
   │
   ▼
Red de Nodes
   │
   ├── Evidencias
   ├── Manifiestos
   ├── Firmas
   ├── CIDs
   ├── Versiones
   ├── Atestaciones
   └── Inconsistencias conocidas
   │
   ▼
Resultado de corroboración
   │
   ▼
Persona
```

La propagación tampoco debe confundirse con publicación.

Puede propagarse:

- un CID;
- un hash;
- una firma;
- un manifiesto;
- una atestación;
- una referencia;
- una prueba;
- metadatos mínimos.

Mientras que el contenido original puede permanecer local o protegido.

---

# 12. Privacidad

La descentralización no significa que todo deba hacerse público.

Node Core OS debe permitir separar:

```text
CONSERVAR
   ≠
PROPAGAR
   ≠
PUBLICAR
   ≠
AUTORIZAR
   ≠
UTILIZAR
```

La persona puede conservar una evidencia localmente y, cuando sea necesario, presentar solamente una prueba o referencia suficiente para un propósito concreto.

Este principio permite construir sistemas donde la infraestructura distribuida pueda corroborar sin requerir necesariamente la exposición completa de los datos personales.

---

# 13. Decisión individual

El objetivo no es obligar a una persona a construir una reputación ni obligarla a participar en sistemas externos.

El objetivo es permitir que tenga la infraestructura preparada.

Una persona puede necesitar en algún momento:

- demostrar quién es;
- demostrar que realizó una actividad;
- demostrar experiencia;
- demostrar una relación contractual;
- demostrar una trayectoria;
- cumplir requisitos para un servicio;
- participar en un protocolo;
- solicitar una oportunidad;
- establecer confianza con otra persona;
- demostrar continuidad histórica.

Node Core OS busca que esa persona no tenga que empezar desde cero cada vez.

Debe existir un lugar propio donde pueda conservar:

> **quién soy, qué he hecho, qué hago y qué quiero hacer.**

Después, la decisión de utilizar esa información pertenece a la persona.

---

# 14. Arquitectura

La arquitectura general mantiene tres niveles visibles:

```text
Node Core OS
│
├── Node Core BIOS
├── Node Core
└── Applications
```

## Node Core BIOS

BIOS administra la infraestructura:

- Storage;
- Kubo/IPFS;
- Network;
- Services;
- Configuration;
- Security;
- Diagnostics;
- Updates;
- Lifecycle.

> **BIOS configura el Node.**

## Node Core

Node Core proporciona las capacidades operativas:

- Storage;
- Files;
- IPFS;
- CID;
- Publish;
- Retrieve;
- Pin;
- Unpin;
- Share;
- Identity;
- Evidence;
- Reputation;
- Protocols;
- Services;
- Utilities.

> **Node Core utiliza el Node.**

## Applications

Las aplicaciones consumen las capacidades del Node.

```text
Applications
      │
      ▼
Protocols
      │
      ▼
Node Core
      │
      ▼
Node Core Runtime
      │
      ├── Local Storage
      ├── Kubo / IPFS
      ├── Network
      └── Services
```

Una instalación puede existir sin aplicaciones.

---

# 15. Sistema de aplicaciones y protocolos

Node Core OS pretende ser una infraestructura sobre la cual otros proyectos puedan construir.

Una aplicación puede solicitar capacidades del Node sin administrar directamente todos sus detalles internos.

```text
Node Core OS
      │
      ▼
Node Core
      │
      ├── Storage
      ├── Identity
      ├── Evidence
      ├── Reputation
      ├── Network
      └── Services
              │
              ▼
          Protocolos
              │
              ▼
         Aplicaciones
```

Esto permite que distintos protocolos y aplicaciones compartan una infraestructura común.

El objetivo final es que **otros sistemas puedan incorporar Node Core OS allí donde lo necesiten**, en lugar de exigir que una persona migre toda su infraestructura personal hacia cada aplicación.

En otras palabras:

> **Si la montaña no va a Mahoma, la montaña viene a Mahoma.**

Node Core OS busca que la infraestructura personal pueda llegar al sistema que la necesita y que el sistema pueda utilizar las capacidades del Node sin apropiarse del núcleo personal.

---

# 16. Principios de arquitectura

## 1. La persona es el centro

La infraestructura existe para preservar la capacidad de decisión de la persona.

## 2. El Node es infraestructura

El Node debe ser útil antes de instalar aplicaciones.

## 3. Las solicitudes son fundamentales

Las operaciones que representan la voluntad de la persona deben partir de solicitudes explícitas o autorizaciones definidas.

## 4. Local y descentralizado son complementarios

El almacenamiento local y Kubo/IPFS cumplen funciones diferentes y pueden coexistir.

## 5. Registrar no significa publicar

La evidencia puede conservarse sin ser automáticamente propagada.

## 6. Identidad no es reputación

La identidad representa continuidad e identificación; la reputación deriva de evidencia contextual.

## 7. Reputación debe ser explicable

Toda reputación significativa debe poder relacionarse con evidencia y corroboraciones.

## 8. La consistencia importa

Las contradicciones temporales, espaciales, físicas, matemáticas o lógicas pueden utilizarse para detectar atribuciones incompatibles.

## 9. La red corrobora, no gobierna la identidad

La red puede aportar evidencia y corroboración sin convertirse en una autoridad universal sobre la persona.

## 10. Las aplicaciones son una capa superior

Las aplicaciones deben utilizar Node Core y no reemplazarlo.

## 11. La privacidad es una propiedad arquitectónica

Debe existir una diferencia entre conservar, compartir, propagar, publicar y autorizar.

## 12. La infraestructura debe ser reutilizable

Node Core OS debe poder convertirse en una base que otros proyectos puedan integrar o implementar.

---

# 17. Modelo completo

La visión completa puede expresarse así:

```text
                              PERSONA
                                 │
                                 ▼
                         ┌───────────────┐
                         │ NODE CORE OS  │
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             SOLICITUDES                 INFRAESTRUCTURA
                    │                         │
                    │              ┌──────────┼──────────┐
                    │              ▼          ▼          ▼
                    │           LOCAL       KUBO       NETWORK
                    │          STORAGE      / IPFS
                    │              │          │
                    └──────────────┴──────────┘
                                 │
                                 ▼
                              REGISTROS
                                 │
                                 ▼
                              EVIDENCIA
                                 │
                                 ▼
                           CORROBORACIÓN
                                 │
                                 ▼
                              IDENTIDAD
                                 │
                                 ▼
                             HISTORIA
                                 │
                                 ▼
                             REPUTACIÓN
                                 │
                                 ▼
                              PROTOCOLOS
                                 │
                                 ▼
                            APLICACIONES
                                 │
                                 ▼
                         USO DECIDIDO POR
                             LA PERSONA
```

---

# 18. Meta final de Node Core OS

La meta final de Node Core OS es construir una infraestructura que permita a una persona disponer de un **núcleo digital propio**, basado en almacenamiento local y descentralizado, desde el cual pueda conservar y administrar sus registros, identidad, evidencia y reputación.

Ese núcleo debe permitir que la persona:

- construya su continuidad digital;
- conserve evidencia de su propia historia;
- pueda corroborar información cuando sea necesario;
- pueda demostrar determinados hechos sin exponer necesariamente toda su información;
- pueda mantener distintas identidades contextuales sin perder la relación con su individualidad;
- pueda detectar contradicciones en la historia atribuida a una identidad;
- pueda participar en redes distribuidas sin entregar automáticamente el control de su información;
- pueda decidir cuándo utilizar su identidad o reputación;
- pueda responder a requisitos de otras personas, organizaciones, servicios, territorios o protocolos;
- pueda mantener su infraestructura aun cuando cambien las aplicaciones que utiliza.

La meta no es crear una identidad obligatoria.

La meta no es crear una reputación universal.

La meta no es crear una red que juzgue a las personas.

La meta es crear **la infraestructura que permita a una persona decidir si quiere participar en aquello que el mundo le exige o le ofrece, teniendo consigo la información y la evidencia necesarias para hacerlo**.

---

# 19. Meta de exportación e interoperabilidad

Una vez consolidado el núcleo, Node Core OS debe poder convertirse en un estándar o arquitectura reutilizable para otros proyectos.

El objetivo es que:

```text
OTRO PROYECTO
      │
      ▼
Integra / implementa
      │
      ▼
NODE CORE OS
      │
      ├── Storage
      ├── Identity
      ├── Evidence
      ├── Reputation
      ├── Protocols
      └── Services
      │
      ▼
APLICACIÓN / PROTOCOLO
```

Esto permitiría que Node Core OS no sea un sistema aislado.

Podría convertirse en una **capa de infraestructura personal exportable**, capaz de ser implementada donde sea necesaria y de incorporar aplicaciones o protocolos donde el usuario los necesite.

---

# 20. Plataforma oficial

**Node Core OS es estrictamente un proyecto GNU/Linux orientado al terminal.**

El alcance oficial del repositorio comprende:

```text
GNU/Linux
   │
   ▼
Terminal
   │
   ▼
Node Core OS
```

El proyecto no define como objetivo oficial una aplicación gráfica de escritorio, una aplicación móvil, una aplicación web, Windows o macOS.

La operación debe ser posible sin root y sin depender de una instalación global del sistema.

---

# 21. Instalación y contrato de dependencias

Node Core OS se instala y opera desde un terminal GNU/Linux.

El instalador del repositorio está diseñado para:

- no requerir root;
- no requerir sudo;
- no requerir systemd;
- utilizar rutas pertenecientes al usuario;
- instalar dentro de `~/.node-core/`;
- instalar y verificar una versión fijada de Kubo;
- inicializar el repositorio de Kubo;
- crear el lanzador de Node Core OS;
- verificar la instalación.

La descarga de dependencias debe priorizar fuentes oficiales y mecanismos de recuperación adecuados, sin imponer límites arbitrarios al tiempo total de transferencia de archivos grandes.

La documentación técnica relacionada se encuentra en:

- `docs/DEPENDENCIES.md`
- `docs/INSTALLER.md`
- `installer/install.sh`

Termux no es un objetivo oficial del proyecto. Las restricciones conocidas de entornos como Termux se consideran únicamente como referencia para evitar asumir privilegios, gestores de servicios o ubicaciones del sistema que no son necesarios.

---

# 22. Estado del proyecto

El repositorio se encuentra en desarrollo.

Este README distingue deliberadamente entre:

- **Implementado** — funcionalidad disponible actualmente.
- **En desarrollo** — funcionalidad que está siendo implementada.
- **Objetivo arquitectónico** — parte del diseño que todavía debe materializarse.
- **Futuro** — extensiones que dependen de capas anteriores.

El núcleo inicial continúa siendo:

```text
Instalación
   ↓
Boot
   ↓
Node Core OS
   ↓
BIOS
   ↓
Local Storage
   ↓
Kubo / IPFS
   ↓
Node Core
   ↓
Add → CID → Pin → Retrieve
```

Sobre este fundamento se desarrollarán progresivamente:

```text
Registros
   ↓
Identidad
   ↓
Evidencia
   ↓
Corroboración
   ↓
Reputación
   ↓
Protocolos
   ↓
Aplicaciones
   ↓
Interoperabilidad
```

La arquitectura descrita en este documento representa la **dirección final de diseño** y no implica que todos sus componentes estén implementados actualmente.

---

# 23. Roadmap conceptual

## Fase 1 — Infraestructura del Node

- instalación rootless;
- runtime;
- configuración;
- almacenamiento local;
- Kubo/IPFS;
- ciclo de vida de servicios;
- red;
- diagnósticos.

## Fase 2 — Node Core

- abstracción de almacenamiento;
- archivos;
- CID;
- Add;
- Retrieve;
- Pin / Unpin;
- Publish;
- Share;
- utilidades.

## Fase 3 — Sistema de solicitudes y registros

- modelo de Request;
- registros;
- intención;
- propósito;
- contexto;
- duración;
- políticas de almacenamiento;
- control de acceso.

## Fase 4 — Identidad

- identidad del Node;
- identidad individual;
- identidad personal;
- identidad profesional;
- posturas públicas y privadas;
- identificadores;
- claves;
- credenciales;
- registros vinculados.

## Fase 5 — Evidencia y corroboración

- modelo de evidencia;
- proveniencia;
- atestaciones;
- corroboraciones;
- consistencia temporal;
- consistencia espacial;
- consistencia causal;
- consistencia lógica y matemática;
- detección de contradicciones.

## Fase 6 — Reputación

- historial;
- reputación contextual;
- relaciones de confianza;
- derivación desde evidencia;
- verificación;
- explicación de reputación.

## Fase 7 — Red de Nodes

- propagación;
- descubrimiento;
- corroboración entre Nodes;
- manifiestos;
- referencias;
- pruebas;
- sincronización;
- mecanismos de confianza distribuida.

## Fase 8 — Protocolos

- modelo de protocolo;
- ciclo de vida;
- servicios;
- comunicación entre Nodes;
- coordinación distribuida;
- identidad y reputación específicas del protocolo.

## Fase 9 — Aplicaciones

- instalación;
- permisos;
- almacenamiento;
- identidad;
- solicitudes;
- servicios;
- networking;
- ciclo de vida.

## Fase 10 — Estándar e interoperabilidad

- API;
- esquemas;
- formatos de exportación;
- mecanismos de integración;
- implementación de Node Core OS dentro de otros proyectos;
- implementación de aplicaciones y protocolos sobre Node Core OS.

---

# 24. Principio final

Node Core OS puede resumirse en una sola dirección:

```text
PERSONA
   ↓
SOLICITUD
   ↓
NODE CORE OS
   ↓
REGISTRO
   ↓
EVIDENCIA
   ↓
CORROBORACIÓN
   ↓
IDENTIDAD / HISTORIA / REPUTACIÓN
   ↓
PROTOCOLO
   ↓
APLICACIÓN
   ↓
DECISIÓN DE LA PERSONA
```

El Node no decide quién debe ser una persona.

No decide qué reputación debe tener.

No decide qué debe publicar.

No decide en qué debe participar.

**Proporciona la infraestructura para que la persona pueda decidirlo con información, evidencia, continuidad y capacidad de corroboración.**

Ese es el objetivo final de **Node Core OS**.

---

# Project

**Node Core OS**  
byLAEV

Repository: https://github.com/byLAEV/Node-Core-OS/
