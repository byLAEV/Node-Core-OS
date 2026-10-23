# Filosofía y Metodología del Diseñador byLAEV

**Documento de principios de diseño, metodología de desarrollo y visión humana de Node Core OS byLAEV**

## 1. Propósito

La Filosofía y Metodología del Diseñador byLAEV establece los principios que orientan la concepción, el desarrollo, la verificación y la evolución de Node Core OS. Su propósito es mantener una relación clara entre lo que se desea construir, lo que está diseñado, lo que existe en el código y lo que ha sido demostrado mediante pruebas.

Node Core OS byLAEV busca proporcionar infraestructura digital reutilizable para administrar almacenamiento local, contenido descentralizado, identidades técnicas y humanas, evidencias, protocolos y aplicaciones. La visión contempla cooperación entre nodos y servicios distribuidos, sin confundir una propuesta arquitectónica con una funcionalidad ya disponible.

Este documento define una metodología de trabajo y una orientación filosófica. No declara que todas las capacidades descritas estén implementadas. El estado real de cada función debe establecerse mediante el código, los contratos, las pruebas y la evidencia del repositorio.

## 2. Principio fundamental: la verdad antes que la apariencia

El diseño debe favorecer la transparencia, la comprobación y la explicación honesta de los resultados. Una interfaz atractiva, una documentación extensa, un mensaje de éxito o una cantidad elevada de nodos no sustituyen una comprobación funcional.

Por tanto:

- No se declarará una función como implementada solo porque exista un documento, una interfaz, una propuesta o un archivo de configuración.
- No se declarará una prueba como aprobada si no existe un resultado verificable que lo demuestre.
- No se confundirá una operación iniciada con una operación completada.
- No se ocultarán errores, limitaciones conocidas ni resultados contradictorios para presentar una apariencia de éxito.
- Los datos de prueba, las entradas, las salidas, los estados y los registros técnicos deben ser inspeccionables durante el desarrollo, siempre que ello no exponga secretos, credenciales productivas o información personal que deba protegerse.
- Toda afirmación técnica importante debe poder relacionarse con código, pruebas, registros o una fuente identificable.

La transparencia exige mostrar lo que realmente sucede, no divulgar indiscriminadamente datos sensibles. Durante el desarrollo se favorecerán los datos sintéticos, las claves de prueba y los registros detallados. Las protecciones de privacidad se incorporarán de forma explícita y verificable, no mediante censura arbitraria de los resultados técnicos.

## 3. Principios de diseño

### 3.1 Claridad y simplicidad funcional

Las implementaciones deben usar estructuras, comandos y lenguajes comprensibles. La simplicidad no significa eliminar validaciones necesarias ni reducir una solución hasta hacerla incompleta. Significa que cada componente debe tener un propósito definido, límites explícitos y comportamiento que pueda probarse.

Se prefiere una implementación más extensa, pero completa y verificable, antes que una solución improvisada, opaca o aparentemente breve que falle en condiciones reales.

### 3.2 Honestidad sobre el estado de cada capacidad

La documentación debe distinguir entre:

- **Propuesto:** existe una idea o especificación, pero no una implementación completa.
- **En desarrollo:** hay trabajo de implementación pendiente.
- **Implementado:** existe código que realiza la función definida.
- **Verificado:** las pruebas especificadas han pasado en un entorno declarado.
- **Limitado:** la función existe, pero tiene restricciones documentadas.
- **Fallido:** una operación o prueba no cumplió sus criterios.
- **Indeterminado:** la evidencia disponible no permite confirmar el resultado.

Estos estados no son intercambiables. En particular, ausencia de error visible no significa éxito y falta de información no significa aprobación.

### 3.3 Control de la persona usuaria

Las personas deben poder comprender qué información se guarda, dónde se almacena, qué operación se ejecuta, qué servicio recibe datos y si una acción publica o comparte contenido. Ninguna publicación distribuida debe producirse silenciosamente por el mero hecho de guardar información local.

### 3.4 Mínimo privilegio

Cada aplicación, proceso y nodo debe disponer únicamente de los permisos necesarios para una función concreta. Una identidad válida no concede autoridad ilimitada; una conexión de red no convierte a un nodo en confiable; pertenecer a un grupo profesional no autoriza a actuar fuera de su competencia.

### 3.5 Compatibilidad e interoperabilidad

Las interfaces públicas deben definir entradas, salidas, errores, permisos, versiones y condiciones de compatibilidad. Los adaptadores de protocolos externos deben respetar las reglas del sistema al que se conectan.

### 3.6 Seguridad verificable

Las decisiones de seguridad deben partir de un modelo de amenazas, requisitos concretos y pruebas. Las técnicas criptográficas avanzadas, incluidas las pruebas de conocimiento cero, se incorporarán cuando exista una necesidad definida y puedan explicarse y verificarse sus garantías. No se presentarán como protección efectiva antes de su implementación y evaluación.

## 4. Metodología de desarrollo

El desarrollo de Node Core OS debe seguir un proceso reproducible.

### 4.1 Inspeccionar antes de modificar

Antes de añadir una función se deben revisar la estructura real del repositorio, los módulos relacionados, los contratos existentes, las dependencias, los instaladores, la documentación y las pruebas. La nueva implementación debe integrarse con la arquitectura existente en lugar de crear interfaces paralelas sin justificación.

### 4.2 Definir el contrato funcional

Antes de programar, describir:

1. El problema que se desea resolver.
2. Los actores y permisos que participan.
3. Las entradas válidas e inválidas.
4. Las salidas esperadas.
5. Los cambios que se producirán en el almacenamiento.
6. Los servicios externos involucrados.
7. Los errores previsibles y su tratamiento.
8. Los criterios de aceptación.
9. Las pruebas necesarias para demostrar el resultado.
10. Las limitaciones conocidas.

Si un requisito no puede expresarse con suficiente precisión para probarlo, debe aclararse antes de considerar terminada la implementación.

### 4.3 Implementar sin improvisar

La implementación debe respetar el contrato, reutilizar las funciones existentes cuando corresponda y evitar duplicar responsabilidades. No se deben inventar comandos, bibliotecas, endpoints, estados, resultados de pruebas ni capacidades de servicios externos.

Los cambios deben ser pequeños cuando eso facilite la revisión, pero nunca deben fragmentar artificialmente una función hasta dejarla sin un flujo completo verificable.

### 4.4 Probar casos positivos y negativos

Las pruebas deben incluir, según corresponda:

- Funcionamiento esperado con entradas válidas.
- Rechazo de entradas inválidas.
- Permisos insuficientes.
- Dependencias ausentes o no disponibles.
- Fallos de almacenamiento.
- Interrupciones de red y tiempos de espera.
- Respuestas vacías, incompletas o malformadas.
- Repetición de operaciones y prevención de efectos duplicados.
- Conservación de datos preexistentes.
- Compatibilidad con instalaciones y versiones admitidas.
- Confirmación del estado final mediante una evidencia independiente de la mera intención de ejecutar.

Una prueba debe fallar cuando no pueda confirmar el resultado requerido. No debe convertir un error, un timeout o una respuesta ambigua en una aprobación.

### 4.5 Integración continua y revisión

Los workflows de GitHub Actions deben ejecutar comprobaciones reproducibles y devolver códigos de salida correctos. Los logs deben conservar información suficiente para investigar los fallos sin revelar secretos.

Las modificaciones deben revisarse mediante ramas y pull requests cuando corresponda. Antes de integrar cambios se revisarán el diff, las pruebas, los logs y los checks obligatorios. Un pull request no debe fusionarse mientras existan checks obligatorios pendientes o fallidos, salvo que una política explícita y autorizada defina otra cosa.

Un check verde demuestra únicamente lo que ese check ha probado. Una ejecución en CI no demuestra por sí sola condiciones físicas, jurídicas o de producción que el entorno de prueba no puede observar.

### 4.6 Verificación después de la corrección

Cuando se corrige un error, no basta con ejecutar una prueba aislada que ahora pase. Deben repetirse las pruebas relevantes de regresión y comprobarse el último commit que se pretende integrar. Los resultados deben asociarse al commit exacto, a la ejecución concreta y a los logs disponibles.

## 5. Entorno de ejecución y privilegios

La directriz de desarrollo de este proyecto establece como entorno objetivo las terminales GNU/Linux ejecutadas por una persona usuaria normal.

Los instaladores, comandos y procedimientos nuevos deben funcionar sin root, sin `sudo` y sin `su`. No deben requerir privilegios elevados para ocultar errores de permisos o modificar áreas del sistema que pertenecen a la administración del equipo.

Termux y los entornos Android no forman parte del objetivo de implementación de esta metodología. Los cambios deben validar el entorno GNU/Linux admitido y explicar de forma clara cuándo una plataforma no está soportada.

Las operaciones deben utilizar rutas y archivos propiedad de la persona usuaria, respetar los permisos del sistema y fallar de forma explícita si no pueden completar una tarea sin privilegios adicionales. No se debe simular una instalación correcta cuando algún paso requerido no se ha completado.

## 6. Almacenamiento local y almacenamiento descentralizado

Node Core OS contempla dos dominios de almacenamiento que deben mantenerse conceptualmente separados.

### 6.1 Almacenamiento local

El almacenamiento local permite gestionar archivos, configuración, registros y datos de las aplicaciones bajo el control de la instalación. Las operaciones locales deben documentar qué archivos crean, modifican o eliminan y cómo se recuperan ante un fallo.

### 6.2 Kubo e IPFS

Kubo/IPFS proporciona mecanismos de direccionamiento por contenido y distribución de contenido. Su integración no debe confundirse con una garantía automática de privacidad, permanencia, disponibilidad o eliminación global.

Un identificador de contenido (CID) identifica contenido direccionado por contenido; por sí solo no prueba quién lo creó, si sus afirmaciones son verdaderas ni si el contenido debe considerarse confiable. Añadir, fijar, publicar, compartir, desfijar y eliminar son operaciones distintas y deben tener resultados claramente diferenciados.

El contenido privado, personal o confidencial no debe publicarse en una red pública por defecto. La publicación debe ser una decisión explícita, con una explicación de sus consecuencias.

La arquitectura también contempla un objetivo de aislamiento físico reforzado para el núcleo. Si una instalación se configura para permanecer físicamente desconectada de redes, Kubo/IPFS y cualquier función que requiera conectividad deben ejecutarse fuera de ese límite o permanecer deshabilitados. No se afirmará que existe aislamiento físico solo porque una prueba de software pase.

## 7. Identidad, evidencia y autorización

Node Core OS debe distinguir los siguientes conceptos:

- Identidad técnica de un nodo.
- Identidad personal declarada.
- Identidad jurídica de una entidad.
- Credenciales emitidas por terceros.
- Evidencias presentadas y verificadas.
- Control de una clave criptográfica.
- Propiedad, representación y custodia.
- Permisos concedidos para una operación.
- Decisiones y resultados registrados.

Una clave criptográfica puede demostrar control de esa clave y permitir verificar firmas, pero no demuestra por sí sola la identidad civil, la singularidad humana, la competencia profesional ni la autoridad jurídica de su titular.

La información declarada por una persona no debe presentarse como verificada sin evidencia y procedimiento adecuados. Una verificación debe indicar su alcance, emisor, fecha, vigencia y limitaciones.

La representación de una persona, empresa o nodo debe ser explícita, limitada por operación, alcance y vigencia, y revocable conforme a su política. La identidad no debe convertirse en una autorización general.

## 8. Blockchain y protocolos externos

Node Core OS aspira a complementar las capacidades operativas de Bitcoin y otras redes blockchain sin reemplazar ni modificar las reglas nativas de sus protocolos.

Cada red debe integrarse mediante un adaptador que respete sus propias reglas, estados y condiciones de confirmación. Deben distinguirse, cuando correspondan, los estados de operación preparada, firmada, difundida, incluida en un bloque, confirmada y fallida.

Una transacción difundida no equivale a una transacción confirmada. Una confirmación tampoco debe describirse como irreversibilidad absoluta sin considerar el protocolo, la profundidad de confirmación y el contexto.

Node Core OS puede coordinar servicios, evidencias, almacenamiento, interfaces y aplicaciones complementarias, pero no debe atribuir al protocolo nativo funciones que pertenecen a la infraestructura externa.

## 9. Consenso, evidencia y cooperación profesional

El consenso debe definirse para una pregunta y un propósito concretos. El número de participantes no demuestra por sí solo independencia, competencia ni veracidad. Deben documentarse quién participa, qué credenciales se requieren, qué fuentes se utilizan, cómo se declaran conflictos de interés y cómo se registran acuerdos, desacuerdos, abstenciones e insuficiencia de evidencia.

La infraestructura puede organizar grupos o pools de identidades profesionales por profesión, especialidad, credenciales, jurisdicción o afinidad temática. Una identidad puede participar en varios pools sin convertirse en una identidad colectiva ni perder responsabilidad individual.

Los profesionales del derecho y otras disciplinas pueden cooperar para comparar fuentes, revisar argumentos, estudiar casos y facilitar acceso a especialistas acreditados. Sin embargo, un consenso técnico o profesional no sustituye una sentencia, una resolución administrativa, una ley ni una decisión de una autoridad competente.

Los casos deben distinguir alegaciones, pruebas, opiniones profesionales, conclusiones de análisis y decisiones oficiales. El reconocimiento jurídico entre territorios exige examinar la legislación aplicable, la jurisdicción, la vigencia de las fuentes, los tratados y los procedimientos pertinentes.

La cooperación internacional debe fundamentarse en la honestidad, el respeto de los derechos humanos, la evidencia, la responsabilidad profesional y la exposición explícita de los desacuerdos. La pertenencia a una comunidad no convierte automáticamente una afirmación en verdadera ni confiere autoridad fuera de la competencia acreditada.

## 10. Privacidad, transparencia y ciclo de vida de los datos

La transparencia técnica debe coexistir con la protección legítima de las personas. Durante el desarrollo, los datos sintéticos permiten registrar entradas, salidas y errores con gran detalle sin exponer información real innecesaria.

El diseño debe diferenciar:

- Conservar un registro.
- Utilizarlo como contexto.
- Restringir su acceso.
- Expirar o revocar una credencial.
- Eliminar datos de los sistemas bajo control propio.
- Desfijar contenido de un nodo IPFS.
- Publicar o compartir información.

Estas operaciones no son equivalentes. Eliminar una copia local no garantiza que otros participantes hayan eliminado sus copias. Un hash tampoco anonimiza necesariamente la información ni demuestra la verdad del contenido.

Los datos personales y expedientes confidenciales deben someterse a minimización, controles de acceso, retención justificada y procedimientos adecuados de eliminación. La aplicación futura de pruebas de conocimiento cero debe responder a necesidades específicas de privacidad o divulgación selectiva y no utilizarse como una afirmación genérica de seguridad.

## 11. Errores, estados y comunicación

Todo flujo importante debe tener estados explícitos. Cuando resulte apropiado, puede emplear estados como `PENDING`, `VALIDATING`, `RUNNING`, `SUCCEEDED`, `FAILED` e `INDETERMINATE`.

Cada estado debe tener una definición verificable. Por ejemplo:

- `PENDING`: la operación está registrada, pero todavía no ha comenzado.
- `VALIDATING`: se comprueban entradas, requisitos y permisos.
- `RUNNING`: la operación está en ejecución.
- `SUCCEEDED`: se verificó el resultado requerido.
- `FAILED`: se comprobó que la operación no cumplió su objetivo.
- `INDETERMINATE`: no existe evidencia suficiente para afirmar éxito o fallo definitivo.

Los mensajes al usuario deben explicar qué ocurrió, qué no se pudo confirmar y cuál es el siguiente paso seguro. Un timeout no prueba que una operación remota no haya ocurrido; antes de repetir una acción con efectos externos se debe comprobar su estado o aplicar mecanismos de idempotencia cuando estén disponibles.

## 12. Evolución de la seguridad

La metodología favorece una progresión consciente:

1. Definir los requisitos y el modelo de amenazas.
2. Construir una implementación funcional y comprensible.
3. Probar los flujos normales y los fallos.
4. Revisar permisos, datos, límites y superficies de ataque.
5. Corregir y repetir las pruebas de regresión.
6. Medir las garantías obtenidas y documentar las limitaciones.
7. Incorporar mecanismos criptográficos avanzados cuando exista una justificación técnica concreta.
8. Verificar que las garantías anunciadas correspondan a una implementación real.

Las pruebas de conocimiento cero pueden ser adecuadas para demostrar una propiedad sin revelar determinados datos subyacentes, pero no garantizan por sí solas que la información de origen sea verdadera, que un emisor esté autorizado o que el sistema completo sea seguro. Sus circuitos, supuestos, verificadores, parámetros y límites deben someterse a revisión específica.

## 13. Reglas de contribución al repositorio

Toda contribución debería cumplir estas reglas:

1. Revisar primero la arquitectura y el contrato existente.
2. Definir criterios de aceptación antes de implementar.
3. Mantener los cambios enfocados y revisables.
4. No añadir dependencias sin justificar su necesidad.
5. No introducir secretos, claves productivas ni datos personales de prueba reales.
6. No declarar soporte de una plataforma sin verificarlo.
7. No ocultar fallos ni convertir estados desconocidos en éxito.
8. Añadir o actualizar pruebas y documentación cuando cambie un contrato.
9. Revisar los logs y el commit exacto que se va a integrar.
10. No fusionar cambios con checks obligatorios pendientes o fallidos.
11. Diferenciar claramente entre código implementado, diseño propuesto y trabajo futuro.
12. Preservar los datos existentes y explicar los cambios incompatibles antes de ejecutarlos.

Los comandos de instalación y mantenimiento deben estar pensados para terminales GNU/Linux y ejecutarse como usuario normal, sin privilegios elevados.

## 14. Responsabilidad del diseñador

Diseñar no consiste únicamente en escribir código. También implica definir límites, reconocer incertidumbres, explicar consecuencias y asumir responsabilidad por las afirmaciones técnicas que se hacen sobre el resultado.

El diseñador debe estar dispuesto a corregir sus decisiones cuando la evidencia las contradiga. La fidelidad a una idea no debe tener prioridad sobre la comprobación de que funciona, y el deseo de mostrar progreso no debe justificar la presentación de resultados no demostrados.

Una buena arquitectura no elimina todos los errores; permite identificarlos, delimitarlos, investigarlos y corregirlos sin ocultar su existencia.

## 15. Visión de Node Core OS byLAEV

La visión de Node Core OS es ofrecer una infraestructura digital en la que personas, organizaciones, nodos y aplicaciones puedan coordinar capacidades mediante reglas explícitas, almacenamiento controlable, protocolos documentados y evidencias examinables.

La infraestructura debe poder evolucionar sin confundir identidad con autorización, almacenamiento con publicación, firma con verdad, consenso con decisión oficial ni diseño con implementación terminada.

La cooperación profesional e internacional puede ampliar el conocimiento disponible, facilitar el análisis de problemas y mejorar la interoperabilidad. Para que esa cooperación sea responsable, sus participantes deben poder identificar las fuentes, examinar las evidencias, declarar límites y conservar la posibilidad de disentir.

## 16. Declaración final

La metodología del diseñador byLAEV se resume en los siguientes compromisos:

- Diseñar con claridad.
- Implementar con rigor.
- Mostrar los datos técnicos con transparencia responsable.
- Probar antes de afirmar.
- Reconocer los errores y corregirlos.
- Respetar los permisos y la privacidad.
- Mantener separadas las propuestas y las capacidades verificadas.
- Construir cooperación sobre evidencia, honestidad y responsabilidad.
- Favorecer soluciones funcionales y reproducibles antes que demostraciones aparentes.

**La verdad fortalece la comunidad. La evidencia permite examinar las afirmaciones. El conocimiento profesional hace posible una cooperación responsable. El código y las pruebas determinan qué funciona realmente.**
