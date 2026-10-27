# Simulación de identidad empresarial y defensa coordinada

## Objetivo

Probar en GitHub Actions, con identidades, certificados, activos y ataques sintéticos, el ciclo propuesto para Node Core OS byLAEV:

1. Una pool empresarial emite un certificado firmado para un activo (dominio Web2 o dispositivo).
2. El certificado vincula de forma explícita el activo, la pool emisora, la clave pública del activo, el perfil de seguridad y la vigencia.
3. El activo instala el certificado y produce un reporte firmado.
4. La pool verifica firma, vínculo entre activo y certificado, emisor y vigencia.
5. El activo reporta un incidente sintético con hash SHA-256 de la evidencia.
6. Nodos de identidad de confianza firman votos sobre el mismo incidente.
7. La simulación acepta la recomendación de contención solo cuando hay un quórum de al menos dos nodos distintos y confiables.

## Ejecutar localmente

Requiere Python 3.10+ y la dependencia `cryptography`.

```bash
python -m pip install cryptography
python scripts/enterprise_identity_defense_simulation.py
python -m unittest discover -s tests -p 'test_enterprise_identity_defense_simulation.py' -v
```

En GitHub, el workflow `.github/workflows/enterprise-identity-defense-simulation.yml` se ejecuta en los cambios relevantes, en pull requests y manualmente desde Actions mediante **Run workflow**.

## Qué valida

- Certificado empresarial firmado y con vigencia.
- Asociación del certificado con una clave pública y un activo específico.
- Reporte de instalación firmado y rechazo de reportes alterados.
- Rechazo de certificados vencidos o presentados para otro activo.
- Reporte sintético de incidente autenticado.
- Votos firmados por nodos confiables.
- El mismo nodo no puede alcanzar el quórum repitiendo su voto.
- Los votos manipulados o no confiables no alcanzan el quórum.
- El umbral de quórum no puede ser uno.

## Límites importantes

Esta es una **simulación local de protocolo**, no una red distribuida real. No contacta dominios, no escanea objetivos, no genera tráfico de ataque y no modifica dispositivos ni firewalls. La recomendación de contención es un resultado simulado: no bloquea tráfico ni reconfigura activos.

Las claves se generan en memoria en cada ejecución y no se persisten. El ejemplo de certificado es un objeto firmado por la aplicación, no un certificado X.509 desplegable en producción. La lista de nodos confiables se inyecta como dato de prueba; todavía no existe aquí descubrimiento de peers, consenso distribuido, almacenamiento persistente de pool, revocación en tiempo real, renovación automática ni canal de respuesta a incidentes en producción.

El quórum solo es significativo si la política de confianza y la independencia de las identidades se establecen fuera de esta prueba. Tres claves diferentes no demuestran por sí solas que pertenezcan a tres organizaciones independientes ni que sean resistentes a Sybil.

## Siguiente fase recomendada

1. Integrar la simulación con los módulos de identidad y transporte existentes sin sustituirlos.
2. Definir un almacén persistente e idempotente de activos y reportes por pool.
3. Añadir revocación, rotación y renovación de certificados con pruebas anti-replay.
4. Definir el formato firmado de solicitud de ayuda y las respuestas de los nodos.
5. Probar particiones de red, nodos comprometidos, informes contradictorios, expiración, replay y pérdida de conectividad.
6. Implementar adaptadores reales de contención solo después de revisión, autorización explícita y pruebas aisladas.

Los resultados de CI deben describirse como pruebas del alcance anterior; no deben anunciarse como protección real contra ataques hasta que exista una integración desplegada y evaluada en un entorno controlado.
