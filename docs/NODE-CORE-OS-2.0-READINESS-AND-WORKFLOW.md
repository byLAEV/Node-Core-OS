# Node Core OS byLAEV 2.0 — Auditoría y plan de entrega

**Estado:** auditoría inicial completada; release NO preparada.  
**Baseline auditado:** `main` = `2c2ef95521d60dfbdda05b2c55e1b80ac707bf03`; `VERSION` = `1.5.6`; release pública más reciente observada = `v1.5.6`.  
**Objetivo:** instalar el Lobby desde un comando de terminal Linux y utilizar el Lobby existente como administrador local de instalación, apertura, diagnóstico, reparación, actualización y mantenimiento de Node Core OS.

## 1. Producto y flujo objetivo

1. Un comando oficial, específico por plataforma, instala solamente el Lobby y sus dependencias mínimas.
2. El Lobby inicia un servicio loopback en `127.0.0.1:8765`; nunca expone por defecto su API administrativa a interfaces públicas.
3. Se instala un acceso directo apropiado para el entorno: XDG Desktop Entry para escritorios Linux con soporte gráfico; Termux:Widget para Termux cuando esté disponible; en entornos sin escritorio se ofrece un comando CLI estable.
4. El Lobby detecta SO/distribución, arquitectura, versión, gestor de paquetes, usuario, permisos, espacio, conectividad, herramientas y capacidades del terminal.
5. El diagnóstico es inicialmente de solo lectura. Después presenta el plan exacto de paquetes y cambios; la instalación de paquetes del sistema requiere consentimiento explícito y elevación limitada solo cuando sea necesaria.
6. El Lobby prepara dependencias y verifica cada paso. No debe asumir que todas las distribuciones usan el mismo gestor ni invocar `sudo` silenciosamente.
7. Solo cuando el preflight está aprobado descarga el paquete oficial de Node Core OS y verifica metadatos, versión, procedencia y SHA-256/SHA-512 antes de ejecutar el instalador canónico.
8. El núcleo instala su runtime, Kubo/IPFS, almacenamiento local, configuración e identidad técnica existente; registra únicamente certificados/credenciales que sean realmente instalables y verificables. Los ocho perfiles de seguridad del catálogo son perfiles de evaluación, no ocho certificados X.509 que se deban instalar.
9. El Lobby permite abrir el núcleo, consultar salud real, reparar configuración/servicios, actualizar y mantener, preservando `storage/`, `ipfs/`, configuración, identidad y datos persistentes.
10. El usuario puede exportar un informe de diagnóstico y evidencias sin exponer claves privadas, tokens ni secretos.

## 2. Hallazgos de la auditoría

### 2.1 Base existente reutilizable

- El instalador canónico de Node Core OS está en `installer/install.sh`, con módulos para detección, compatibilidad, dependencias, Kubo, filesystem, aplicación y verificación.
- El actualizador protegido está en `installer/update.sh` y existen pruebas de preservación y recuperación.
- La compatibilidad declarativa de terminales está en `compatibility/manifest.json`; GNU/Linux usa detección por capacidades y evita invocar gestores del host. Termux tiene perfil propio `pkg` y ARM64.
- La rama de trabajo del Lobby (#217) contiene un servicio local, UI web, inventario de solo lectura, preparación/ejecución verificada de paquetes, certificado TLS loopback, gestión explícita de confianza de peers y accesos Termux:Widget.
- Hay pruebas de instalador real Ubuntu, Debian y Fedora, matrices Python, Kubo/P2P y preservación de datos.
- El catálogo distingue certificados técnicos, almacenes de confianza y ocho perfiles de seguridad no instalables. Esta distinción debe conservarse.

### 2.2 Bloqueos de lanzamiento comprobados

1. `main` todavía declara `VERSION=1.5.6`; no existe una release 2.0.
2. El workflow de publicación actual se construyó alrededor de dos archivos: instalador y actualizador. La 2.0 necesita que el bootstrap de Lobby sea el punto de instalación inicial y que el paquete del núcleo se descargue desde Lobby. No se debe seguir publicando el modelo antiguo como si ya fuera el nuevo.
3. El workflow de publicación verificada tiene valores por defecto fijados a `v1.5.6`, un commit histórico y un artefacto/digest histórico. Requiere diseño de entrada sin valores obsoletos y validación de evidencia del candidato exacto.
4. #217 es una rama de 223 commits que diverge de main; el compare actual muestra 4 commits detrás y 223 delante. No se debe fusionar como bloque único sin rebase/reconciliación y revisión de diff.
5. El bootstrap de #217 usa por defecto `feature/termux-local-lobby` y solo admite Termux ARM64 nativo. Una instalación oficial no puede apuntar a una rama de feature.
6. El workflow #217 tiene validaciones automatizadas satisfactorias en Linux, pero la validación física nativa Android/Termux está `skipped`; no cuenta como evidencia aprobada.
7. La UI del Lobby en #217 está diseñada explícitamente como Termux environment manager. No se ha demostrado todavía el mismo servicio/instalador para GNU/Linux genérico, terminales móviles Linux y distintos emuladores de terminal.
8. El instalador del Lobby en #217 es específico de Termux (`pkg`, `~/.shortcuts`, shebang Termux). Faltan instaladores/launchers XDG para escritorio Linux y perfil genérico.
9. El flujo documentado de #217 condiciona la primera instalación a una prueba/identidad Bitcoin. Esto es ajeno al alcance de release 2.0 definido aquí y debe separarse. La 2.0 conserva la identidad técnica Ed25519 que el núcleo ya inicializa; no exige onboarding Bitcoin ni nuevas funciones de identidad.
10. El gestor de certificados del Lobby gestiona TLS local del Lobby y confianza explícita de peers; no equivale a instalar certificados de identidad firmados en el núcleo. Debe conectarse con el formato/verificador existente de `node_core/security/node_identity_certificate.py`, con trust anchors configurados explícitamente, validación de firma, emisor, vigencia, perfil y revocación. No inventar una CA raíz ni confiar en certificados por estar en el catálogo.
11. El workflow `termux-lobby.yml` invoca `package-installers.yml` como reusable; se debe mantener `workflow_call` y verificar que los artefactos correspondan al mismo SHA candidato.
12. #218 agrega una app APK/Android separada, no es el bootstrap CLI multiplataforma pedido. Su check de build falló porque solicita el paquete Android SDK obsoleto `tools` y licencia SDK preview. No es un bloqueo para la ruta Termux/CLI de 2.0 salvo que se declare APK como plataforma soportada.
13. #213 diverge 103 commits detrás de main y trata de preparar 1.5.7. No fusionar esa rama antigua directamente ni introducir release 1.5.7 como paso obligatorio para 2.0; seleccionar cambios útiles y portarlos en una rama actual.
14. #214 trata correcciones de relay/P2P, es draft y diverge 4 commits detrás. Integrar solo si las correcciones son necesarias para la estabilidad de 2.0 y tras ejecutar sus pruebas específicas.
15. La consulta de rulesets no devolvió reglas; el conector no pudo leer branch protection. Confirmar en GitHub UI que main exige checks, review y conversación resuelta. No asumir que están configurados.

## 3. Estrategia de integración de PR

- #212 ya está integrado en main (commit `2c2ef955...`).
- #213: congelar como fuente histórica. Comparar cambios uno por uno; portar solo detección Android/Termux, actualización y pruebas que sigan siendo necesarias. Descartar VERSION/CHANGELOG 1.5.7 obsoletos para esta entrega.
- #214: mantener draft hasta que sus cambios relay/P2P se validen sobre main actual. Portar por commit si procede.
- #217: conservar como fuente funcional del Lobby, no fusionar su rama divergente en bloque. Extraer por módulos: server/UI, bootstrap, instalador, manifest, pruebas y workflow. Separar Bitcoin identity onboarding del flujo de instalación 2.0. Eliminar dependencias de branch feature.
- #218: mantener separado del objetivo de CLI/Lobby. Corregir Android SDK build solo si se decide expresamente que APK es un entregable 2.0; Termux:Widget y accesos XDG son el objetivo inmediato.
- Todo cambio portado se implementa en PR nuevo basado en main actualizado. Un PR se fusiona solo cuando no sea draft, esté actualizado, tenga revisión requerida, threads resueltos, checks aplicables verdes y mergeabilidad limpia.

## 4. Fases del Workflow de entrega

### F0 — Gobernanza y baseline
- Confirmar protección de main, checks requeridos y permisos.
- Congelar baseline SHA y generar inventario de PR, ramas, workflows, releases y artefactos.
- Definir la matriz de plataformas oficialmente soportadas: Ubuntu LTS x86_64/aarch64, Debian estable x86_64/aarch64, Fedora soportada x86_64/aarch64 y Termux ARM64 nativo. Añadir otras solo tras evidencia.

### F1 — Integración del Lobby existente
- Portar Lobby actual a rama actual basada en main.
- Mantener la interfaz existente; adaptar backend/instaladores por plataforma.
- Bootstrap remoto por tag estable o commit de release, nunca branch feature.
- Servicio local loopback, autenticación de sesión, protección CSRF/Host/Origin, TLS local y no shell arbitrario.
- Acceso directo XDG, Termux:Widget y fallback CLI.
- Desacoplar onboarding Bitcoin/identidad extendida del botón de instalación.

### F2 — Preflight y preparación de terminal
- Inventario de solo lectura con informe exportable.
- Resolver paquetes por gestor/distro, versiones y arquitectura.
- Mostrar plan antes de cambios; consentimiento explícito.
- No ejecutar gestor de paquetes como root ni elevar toda la aplicación; usar un helper acotado/acción confirmada cuando el sistema lo exija.
- Validar Python, cryptography, curl/wget, tar, checksum, OpenSSL, Kubo, espacio, permisos y conectividad.

### F3 — Instalación del núcleo desde Lobby
- Descarga de metadatos firmados/verificables y paquete exacto.
- Verificar SHA-256/SHA-512 y estructura de archivo contra traversal, symlinks y archivos especiales.
- Ejecutar exclusivamente el instalador canónico.
- Instalar Kubo/IPFS y comprobar daemon/API, storage local, launcher, configuración y ownership.
- Instalar/verificar certificados y trust material compatibles con el núcleo; perfiles documentales no se instalan como certificados.

### F4 — Operación y reparación
- Estado real de Lobby, Node Core, Kubo, almacenamiento, certificados y procesos.
- Abrir Node Core OS desde el Lobby en terminal/sesión adecuada.
- Reparar solo componentes identificados; backup/rollback antes de mutaciones.
- Actualización atómica, preservación de datos e identidad y recuperación ante interrupción.
- Mantenimiento y reportes de auditoría sin secretos.

### F5 — Compatibilidad y aceptación E2E
- Linux: Ubuntu, Debian, Fedora; x86_64 y aarch64 según runner disponible.
- Termux: ARM64 físico; validar Android/Termux, almacenamiento, background lifecycle, Widget, puertos y Kubo.
- Terminales Linux móviles adicionales: registrar como perfiles separados, no inferir compatibilidad por ser Linux.
- Ejecutar instalación limpia, update, reparación inducida, reinicio, apertura, uninstall seguro y preservación.
- Verificar cada check contra el SHA exacto del PR y repetir después del merge sobre main.

### F6 — Release candidate y publicación 2.0
- Actualizar VERSION, changelog, documentación y contrato de compatibilidad.
- Crear paquete Lobby bootstrap, paquete núcleo y paquete updater según el diseño final.
- Manifiesto de artefactos, SHA-256/SHA-512, source commit, SBOM y procedencia.
- Probar desde una terminal limpia el comando oficial, Lobby, instalación del núcleo, operación, reparación y actualización.
- Solo publicar `v2.0.0` desde main protegido cuando todos los gates estrictos pasen.

## 5. Criterios de aceptación no negociables

- [ ] Comando oficial instala solo Lobby en cada perfil soportado.
- [ ] Lobby inicia en 127.0.0.1:8765 y no escucha en interfaces externas.
- [ ] Icono/launcher funciona para escritorio Linux y Termux:Widget; fallback CLI documentado.
- [ ] Diagnóstico no modifica el sistema.
- [ ] Preflight detecta paquetes faltantes y presenta un plan de instalación.
- [ ] Dependencias se instalan con consentimiento y gestor correcto.
- [ ] Paquete del núcleo se valida antes de ejecutar.
- [ ] Instalación incluye runtime, Kubo/IPFS, almacenamiento, configuración e identidad técnica actual.
- [ ] Certificados instalados en núcleo se verifican criptográficamente y están vinculados a trust anchors explícitos; no se instalan los ocho perfiles documentales como X.509.
- [ ] Abrir Node Core OS desde Lobby funciona.
- [ ] Estado, reparación y mantenimiento reportan resultados reales.
- [ ] Actualización conserva storage, ipfs, config, identidad y certificados.
- [ ] Fallo de actualización puede recuperarse sin borrar datos.
- [ ] E2E en plataformas declaradas pasa y no se marca skipped como success.
- [ ] Todos los PR necesarios están merged a main; no hay PR críticos abiertos.
- [ ] main tiene workflows verdes sobre el SHA exacto de publicación.
- [ ] Release v2.0.0 tiene paquetes y hashes verificados, documentación y evidencia.

## 6. Matriz de compatibilidad propuesta

| Perfil | Estado actual de evidencia | Gate 2.0 |
|---|---|---|
| Ubuntu 24.04 x86_64 | Instalador del núcleo E2E pasa | Lobby + core E2E |
| Debian 13 x86_64 | Instalador del núcleo E2E pasa | Lobby + core E2E |
| Fedora 44 x86_64 | Instalador del núcleo E2E pasa | Lobby + core E2E |
| GNU/Linux aarch64 | Declarado en manifest; evidencia E2E no confirmada | Runner ARM64 real |
| Termux Android ARM64 | Workflow automatizado pasa; runner físico skipped | Dispositivo físico |
| Otras terminales móviles Linux | No demostradas | Perfil y runner/dispositivo separados |

## 7. Riesgos y decisiones de diseño

- La instalación genérica Linux de paquetes del host no debe ser silenciosa. Diagnóstico read-only, plan visible y consentimiento explícito.
- El Lobby no debe requerir root para su propio servicio ni ejecutar shell arbitrario recibido desde el navegador.
- HTTPS con certificado self-signed protege el transporte local, pero el navegador puede no confiar en él. Documentar la primera confianza; no degradar silenciosamente a HTTP para endpoints mutables.
- Los secretos no deben aparecer en reportes, logs, URLs, historial ni archivos temporales persistentes.
- El servidor loopback debe comprobar Host/Origin y no aceptar DNS rebinding ni acceso remoto.
- Los certificados de nodo JWS Ed25519 requieren claves de emisor y trust anchors explícitos; no existe una raíz de confianza que pueda inferirse del repositorio.
- No usar pruebas simuladas como sustituto de pruebas físicas. Una prueba omitida en plataforma objetivo bloquea declarar esa plataforma soportada.

## 8. Orden de PR propuesto

1. PR-A: especificación 2.0, matriz de compatibilidad, contrato de aceptación y workflow de auditoría.
2. PR-B: Lobby bootstrap estable + instaladores por plataforma + launchers.
3. PR-C: preflight y preparación de dependencias Linux/Termux.
4. PR-D: instalación núcleo + Kubo + certificados/verificación.
5. PR-E: apertura, estado, reparación, mantenimiento y update-preservation.
6. PR-F: matriz E2E, paquetes, SBOM/procedencia y release gate.
7. Release candidate: v2.0.0-rc.1 en entorno de prueba; luego release v2.0.0.

Este documento describe el estado comprobado y el trabajo propuesto. No declara implementadas las capacidades que aún no tienen código y evidencia.


## Priority execution register

See [PR priority register and fastest safe path](NODE-CORE-OS-2.0-PRIORITY-REGISTER.md) for the current per-PR audit, concrete conflicts/errors, check results, release blockers, and ordered execution plan.
