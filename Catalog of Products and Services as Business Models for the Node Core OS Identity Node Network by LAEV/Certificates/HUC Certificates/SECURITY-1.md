# Seguridad y modelo de amenazas — LAEV HUC 0.7

## Clasificación

Prototipo de laboratorio para investigación y pruebas de interoperabilidad. No utilizar para TLS público, identidad legal, control de acceso crítico, pagos, cumplimiento normativo ni producción sin auditoría independiente.

## Activos

- Claves privadas Ed25519 de validadores.
- Claves privadas de autoridades HUC-CC.
- Clave privada de la CA X.509.
- Claves privadas de titulares.
- Manifiesto de red, peer map y sus hashes fijados.
- Locks de voto, locks de vista, logs y checkpoints de membresía.
- Datos de certificados y evidencia de revocación.

## Controles implementados

- Identidad independiente por nodo y firmas Ed25519.
- Sobre de mensaje firmado con domain separation, identidad de origen, message ID, timestamp y validación anti-replay.
- Manifiesto de red y peer map fijados por hash.
- Límites de tamaño y timeout de lectura en el servidor.
- TLS requerido para binds no-loopback, salvo override explícito destinado a laboratorio/VPN.
- Quórum `2f+1`, bloqueos persistentes anti-equivocación y commits verificables.
- Cambio de vista firmado; preservación de una propuesta bloqueada común y parada ante locks incompatibles.
- Solicitudes de incorporación con prueba de posesión de clave.
- Reconfiguración firmada por quórum del comité anterior y checkpoint del estado.
- Sincronización que valida red, epoch, secuencia, commits, checkpoint y rechaza rollback/fork.
- Cada validador en modo PKI valida X.509 y HUC-CC antes de votar.

## Límites importantes

1. **P2P físico no probado:** la demo ejecuta cuatro procesos TCP en loopback. La conectividad real entre instituciones, Internet, NAT, firewalls, latencia y pérdida de paquetes no está certificada.
2. **Confidencialidad:** los sobres Ed25519 no cifran datos. El transporte no-TLS solo es apropiado para loopback o VPN privada confiable. Para producción usar TLS y preferiblemente mTLS, con CA, SAN y rotación apropiados.
3. **View Change no es BFT completo:** HUC 0.7 conserva un único lock común y se detiene ante locks incompatibles. No incluye todos los certificados prepared/commit ni el algoritmo formal de new-view de PBFT/HotStuff.
4. **Membresía:** el quórum del comité anterior aprueba el sucesor. El nuevo miembro recibe el paquete por canal de invitación autenticado. La configuración de peers debe actualizarse y fijarse después de la activación.
5. **Membresía estática por epoch:** no hay un protocolo de reconfiguración concurrente ni dos comités activos en paralelo con handoff formal completo.
6. **Clave privada:** el prototipo almacena claves sin cifrado de contraseña por simplicidad de laboratorio. Producción requiere HSM/KMS, controles por rol, backup y rotación.
7. **Rollback local:** los locks requieren persistencia durable y backups protegidos. Un operador con acceso total al almacenamiento puede intentar restaurar copias viejas; checkpoints externos/auditoría ayudan a detectar eso.
8. **Disponibilidad:** sin 3 votos de 4 no hay commit. El sistema prioriza seguridad sobre disponibilidad en particiones.
9. **Identidad:** una firma demuestra control de clave, no identidad civil ni autorización legal de la organización.
10. **Offline:** un verificador conoce el último estado sincronizado; no puede descubrir una revocación posterior mientras permanece desconectado.

## Requisitos antes de producción

- Especificación BFT formal (prepare/commit, prepared certificates, view-change, recovery, membership epochs) y revisión criptográfica externa.
- Pruebas property-based, fuzzing, fallos Byzantine, equivocation, replay, partición, reordenamiento, crash/restart y pérdida de almacenamiento.
- TLS/mTLS interinstitucional, validación estricta de SAN, CA y revocación de certificados TLS.
- HSM/KMS, rotación y revocación de claves, backup seguro y procedimientos de recuperación.
- Servicio de descubrimiento/relays o conectividad VPN administrada para redes con NAT.
- Políticas de privacidad, identidad, gobierno, responsabilidades legales y retención.
- Auditoría independiente, observabilidad, rate limits, hardening del sistema operativo y plan de incidentes.
