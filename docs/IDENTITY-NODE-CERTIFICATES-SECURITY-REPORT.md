# Informe técnico oficial: Certificados e identidad de la red de nodos de Node Core OS byLAEV

**Autor y responsable del diseño:** Lerry Alexander Elizondo Villalobos — **byLAEV**  
**Proyecto:** Node Core OS byLAEV  
**Fecha de revisión:** 27 de octubre de 2026  
**Estado del documento:** Informe técnico basado en el código y en las ejecuciones de CI enlazadas abajo. No constituye una certificación independiente ni una garantía de seguridad de producción.  
**Repositorio:** https://github.com/byLAEV/Node-Core-OS  
**Cambio de referencia:** merge commit [73c2d2237139b7c373d5fea230d3787a541833ff](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)

---

## 1. Resumen ejecutivo

Node Core OS incorpora una identidad técnica persistente para los nodos, basada en claves Ed25519, y una capa de transporte TLS que asocia un certificado de nodo con la clave pública de esa identidad. El trabajo de seguridad incorporado en el PR #150 añade pruebas adversariales sintéticas, pruebas de un servicio HTTPS de laboratorio, validación de un perfil web, validación HTTPS con comprobaciones estándar de cadena y hostname, primitivas locales de eventos firmados y revocación, reglas locales de corroboración y pruebas limitadas de abuso de API.

La suite de certificados de GitHub Actions finalizó correctamente en el commit `024c563bedf3cffda2af391931d4ebcafc1dbd62`. El PR #150 se fusionó en `main` mediante el merge commit indicado arriba. La ejecución de CI demuestra que los casos automatizados de esa versión terminaron sin fallos; no demuestra ausencia de vulnerabilidades, resistencia a todos los ataques ni disponibilidad de una defensa distribuida completa.

**Conclusión principal:** la contribución técnica es añadir identidad de nodo verificable y componentes de seguridad comprobables junto a TLS, no sustituir HTTPS/X.509 ni garantizar por sí sola protección contra phishing, DDoS, malware o vulnerabilidades de aplicación.

## 2. Propósito y alcance

El sistema está diseñado para terminales GNU/Linux ejecutadas como usuario normal. El workflow específico de Termux `termux-live-peer.yml` se retiró del PR porque no correspondía al objetivo de plataforma de estas pruebas.

Este informe cubre:

- Identidad criptográfica de nodo y vinculación con certificado.
- Pruebas de rechazo de certificados o metadatos manipulados.
- Laboratorio HTTPS local con identidades sintéticas.
- Perfil de vinculación entre certificado web y nodo.
- Validación HTTPS con cadena de confianza y hostname.
- Eventos de seguridad firmados, instantáneas locales de revocación y corroboración.
- Pruebas acotadas de abuso de API.
- Límites, amenazas pendientes y procedimiento de reproducción.

No cubre una auditoría independiente de todo el repositorio, pruebas de penetración sobre servicios públicos, una certificación formal PKI, un análisis criptográfico académico ni una prueba de defensa en televisores, consolas u otros dispositivos comerciales.

## 3. Conceptos y modelo de confianza

### 3.1 Identidad de nodo

La implementación técnica usa Ed25519 y deriva un identificador de nodo con prefijo `sha256:` a partir de la clave pública. La clave privada permite firmar mensajes y demostrar control de esa clave. La clave pública y el identificador permiten verificar que la firma corresponde a la identidad técnica declarada.

Esto no prueba por sí solo:

- la identidad civil de una persona;
- que una persona sea única;
- que el operador sea honesto o confiable;
- que el equipo no esté comprometido;
- que los datos firmados sean verdaderos;
- que el nodo tenga autorización para cualquier acción.

Referencias:
- [Implementación de identidad de nodo](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/identity/node_identity.py)
- [Pruebas de asociaciones de identidad](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_associations.py)
- [Pruebas de función de identidad](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_identity_function.py)

### 3.2 Certificado de transporte TLS de nodo

El transporte TLS asocia el certificado presentado por un nodo con la identidad de clave pública que el nodo tiene almacenada. Las pruebas comprueban que se rechacen, entre otros casos, un certificado asociado a otro nodo, PEM malformado, metadatos manipulados, una firma alterada, un certificado vencido y una firma propia inválida.

La validación específica de Node Core OS no debe confundirse con una PKI pública completa. El laboratorio de transporte usa confianza explícita en certificados sintéticos y vinculación de identidad de nodo. Esa estrategia es útil para probar confianza entre nodos conocidos, pero no reemplaza la validación estándar de certificados web de un navegador.

Referencia:
- [Transporte TLS de nodo](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/p2p/tls_transport.py)

### 3.3 HTTPS estándar

HTTPS/X.509 aporta autenticación del servidor y cifrado del canal cuando el cliente valida correctamente la cadena de certificación, el periodo de validez y el hostname solicitado. Node Core OS debe conservar esas garantías cuando interactúe con sitios web convencionales.

La prueba de HTTPS estándar usa una CA y certificados sintéticos creados para el test y conecta únicamente a loopback. Verifica la aceptación del caso legítimo y el rechazo de casos negativos, incluidos hostname incorrecto, CA no confiable y certificado aún no vigente. Es una prueba de integración local; no es una prueba contra un sitio público.

Referencia:
- [Pruebas HTTPS con validación estándar](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_standard_https_validation.py)

### 3.4 Perfil de vinculación de certificado web

El perfil web permite crear y comprobar una asociación firmada entre un certificado, un nombre DNS y una identidad de nodo. Las pruebas incluyen vinculación válida, firma de vinculación modificada, huella de certificado distinta, DNS incorrecto, certificado expirado, ausencia de EKU de autenticación de servidor y ausencia de SAN.

Una vinculación con la identidad de nodo es una señal adicional de atribución técnica. No convierte automáticamente el certificado en uno de confianza pública ni debe utilizarse para saltarse las comprobaciones normales de cadena, hostname o política de confianza del cliente.

Referencia:
- [Perfil de TLS web](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/identity/web_tls_profile.py)
- [Pruebas del perfil TLS web](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_web_tls_profile.py)

## 4. Componentes de seguridad cubiertos por pruebas

### 4.1 Pruebas adversariales de certificados

Los casos cubren la identidad válida vinculada a la clave del nodo, certificado de otro nodo, PEM corrupto, alteración de metadatos, alteración de firma, certificado vencido y certificado con firma propia inválida.

- [Código de pruebas](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_security.py)
- [Ejecución de GitHub Actions, commit de merge](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)

### 4.2 Laboratorio de página web HTTPS protegida

El laboratorio levanta un servicio HTTP sobre TLS en `127.0.0.1`, con certificados temporales. Comprueba acceso de un nodo cliente confiable, rechazo de un certificado de cliente no confiable y rechazo de un servidor impostor cuyo certificado no coincide con el certificado esperado por el cliente.

El propio test declara que evalúa transporte con certificados de confianza explícita y vinculación de identidad; no es una prueba de PKI de navegador.

- [Código del laboratorio web](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_certificate_web_lab.py)

### 4.3 Eventos firmados, instantáneas de revocación y corroboración

El módulo de defensa distribuida proporciona primitivas para:

- crear y verificar eventos de seguridad firmados;
- validar emisor autorizado, firma, fechas y huella de evidencia;
- crear y verificar instantáneas firmadas de revocación con secuencia;
- rechazar instantáneas no autorizadas, vencidas o con secuencia no superior a la última secuencia conocida;
- decidir localmente si hay suficientes reportantes distintos con eventos firmados válidos para cumplir un umbral de corroboración.

- [Implementación de defensa y registros firmados](https://github.com/byLAEV/Node-Core-OS/blob/main/node_core/security/distributed_defense.py)
- [Pruebas de defensa distribuida](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_distributed_defense.py)

**Límite esencial:** estas primitivas y sus tests no demuestran por sí solos la distribución efectiva de revocaciones entre nodos, persistencia antirretroceso después de reiniciar, convergencia bajo particiones de red ni ejecución automática de cuarentena. La función de corroboración evalúa evidencia local; no demuestra independencia humana o administrativa de los reportantes. Distintas claves pueden estar controladas por una sola entidad.

### 4.4 Abuso limitado de API

La suite incluye entradas malformadas, solicitudes de tamaño excesivo y escenarios de límite de frecuencia en un handler sintético de loopback. Sirve para verificar el comportamiento de ese laboratorio, no para afirmar que todos los endpoints reales de Node Core OS estén protegidos.

- [Pruebas del laboratorio de abuso de API](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_api_abuse_lab.py)

### 4.5 Transporte TLS P2P

- [Pruebas de transporte TLS P2P](https://github.com/byLAEV/Node-Core-OS/blob/main/tests/test_p2p_tls_transport.py)

## 5. Resultado reproducible de CI

El workflow de GitHub Actions define los comandos y límites del laboratorio:

- [Workflow de pruebas adversariales](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Ejecución principal de certificados: #40450438209](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)
- [Ejecución adicional de certificados: #40450434087](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450434087)
- [CI general GNU/Linux: #40450438106](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438106)
- [Integración Kubo de usuario: #40450438099](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438099)
- [Tres nodos Ubuntu y contratos P2P: #40450438116](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438116)
- [Pruebas E2E de tres nodos: #40450438162](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438162)
- [Pruebas E2E del instalador: #40450438183](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438183)
- [Dominios independientes de red: #40450438270](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438270)
- [PR #150 fusionado](https://github.com/byLAEV/Node-Core-OS/pull/150)
- [Commit de merge](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)

El workflow ejecuta, con Python 3.12 y dependencias del repositorio, las siguientes suites y luego compila los módulos para detectar errores sintácticos:

```bash
python -m unittest discover -s tests -p 'test_certificate_security.py' -v
python -m unittest discover -s tests -p 'test_certificate_web_lab.py' -v
python -m unittest discover -s tests -p 'test_web_tls_profile.py' -v
python -m unittest discover -s tests -p 'test_standard_https_validation.py' -v
python -m unittest discover -s tests -p 'test_distributed_defense.py' -v
python -m unittest discover -s tests -p 'test_api_abuse_lab.py' -v
python -m unittest discover -s tests -p 'test_p2p_tls_transport.py' -v
python -m compileall -q node_core/security node_core/identity tests
```

### Reproducir en GNU/Linux como usuario normal

Desde un checkout limpio del repositorio y dentro de un entorno virtual de Python, sin ejecutar como root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m unittest discover -s tests -p 'test_certificate_security.py' -v
python -m unittest discover -s tests -p 'test_certificate_web_lab.py' -v
python -m unittest discover -s tests -p 'test_web_tls_profile.py' -v
python -m unittest discover -s tests -p 'test_standard_https_validation.py' -v
python -m unittest discover -s tests -p 'test_distributed_defense.py' -v
python -m unittest discover -s tests -p 'test_api_abuse_lab.py' -v
python -m unittest discover -s tests -p 'test_p2p_tls_transport.py' -v
python -m compileall -q node_core/security node_core/identity tests
```

Los tests están diseñados para identidades y certificados sintéticos, carpetas temporales y conexiones locales. No se deben interpretar como permiso para probar sistemas de terceros.

## 6. Comparación técnica con certificados HTTPS/X.509 convencionales

| Capacidad | HTTPS/X.509 estándar | Node Core OS en el alcance probado |
|---|---|---|
| Validar cadena, fechas y hostname | Sí, si el cliente está configurado correctamente | Se prueba la validación estándar en laboratorio local |
| Asociar un certificado con una identidad técnica de nodo | No es una función universal del X.509 básico | Se prueba una vinculación de clave/identidad de nodo y un perfil web |
| Firmar eventos de seguridad con claves de nodo | No es función básica de un certificado TLS | Hay primitivas y pruebas locales de eventos firmados |
| Distribuir y aplicar revocaciones entre nodos | Depende del sistema de PKI y distribución utilizado | Las primitivas locales están probadas; la propagación distribuida completa no |
| Detener phishing, DDoS, malware o fallos de aplicación | No por sí solo | No demostrado por estos certificados o tests |
| Acreditar que una clave pertenece a una persona única | No | Tampoco lo demuestra la identidad técnica de nodo |

Por tanto, no se afirma que Node Core OS sea criptográficamente superior a X.509 ni que sustituya la infraestructura de confianza web. La posible contribución diferenciadora es la capa de identidad de nodo y evidencia firmada que podría complementar el TLS convencional y, tras completar la integración, ayudar a coordinar decisiones de confianza entre nodos.

## 7. Amenazas y trabajo pendiente

Antes de una declaración de preparación para producción, deben completarse y documentarse al menos estos trabajos:

1. **Revocación distribuida:** transporte autenticado de instantáneas, persistencia de la secuencia aceptada, pruebas contra repetición y rollback, nodos desconectados y recuperación tras reinicio.
2. **Contención operativa:** integrar la decisión local con una política de autorización, cuarentena reversible, registro de auditoría y procedimiento de recuperación.
3. **Resistencia Sybil:** definir cómo se autoriza a los reportantes y cómo se evita contar varias claves bajo el mismo control como corroboración verdaderamente independiente.
4. **Abuso de API real:** probar endpoints integrados en un entorno aislado, medir carga, límites, latencia y disponibilidad, y documentar qué componentes quedan fuera.
5. **PKI y ciclo de vida:** documentar emisión, renovación, custodia de claves, expiración, revocación, recuperación y respuesta ante compromiso de clave.
6. **Revisión independiente:** revisión del modelo de amenazas, código criptográfico, manejo de secretos, configuración TLS y dependencias por un profesional o equipo independiente.
7. **Pruebas comparativas:** comparar en las mismas condiciones HTTPS estándar y HTTPS más la capa de Node Core OS, usando métricas de falsos positivos, falsos negativos, latencia de revocación y disponibilidad.

## 8. Declaración de seguridad y uso

Este informe documenta el estado de código y pruebas referenciados, no una garantía absoluta de seguridad. Un certificado válido acredita únicamente las afirmaciones que su formato, emisor, cadena de confianza y política de validación permiten verificar. Una firma demuestra control de la clave correspondiente y la integridad del mensaje firmado; no garantiza la veracidad de su contenido.

La protección de un servicio requiere además autenticación y autorización correctas, configuración TLS, actualizaciones, control de acceso, límites de recursos, observabilidad, mitigación de abuso, copias de seguridad y respuesta a incidentes. Ningún certificado aislado elimina todos los vectores de ataque.

No se recomienda instalar estos certificados como autoridad de confianza global ni desplegarlos en televisores, consolas o servicios de producción sin un perfil de interoperabilidad, un proceso de emisión y revocación y una evaluación específica de cada plataforma.

## 9. Autoría

**Lerry Alexander Elizondo Villalobos — byLAEV**  
Autor y responsable del diseño de Node Core OS byLAEV.

Este documento atribuye la autoría del diseño y la responsabilidad del proyecto a byLAEV. Los resultados de CI son resultados automatizados del repositorio, no una certificación externa independiente.

---

**Referencias principales**
- [Repositorio Node Core OS byLAEV](https://github.com/byLAEV/Node-Core-OS)
- [PR #150 — pruebas adversariales de certificados](https://github.com/byLAEV/Node-Core-OS/pull/150)
- [Workflow de pruebas de certificados](https://github.com/byLAEV/Node-Core-OS/blob/main/.github/workflows/certificate-adversarial-tests.yml)
- [Ejecución de certificados #40450438209](https://github.com/byLAEV/Node-Core-OS/actions/runs/40450438209)
- [Commit de merge](https://github.com/byLAEV/Node-Core-OS/commit/73c2d2237139b7c373d5fea230d3787a541833ff)
