# Node Core OS — Formato de certificado de identidad de nodo

**Estado:** borrador técnico v1.0 para implementación y revisión externa.  
**Ámbito:** identidad criptográfica de nodos y perfiles de evaluación de seguridad.  
**No es:** un certificado X.509, una norma internacional aprobada ni una acreditación independiente.

## Objetivo

Definir un sobre portátil, verificable por software y apto para intercambiarse entre implementaciones Node Core OS. El formato usa JSON Web Signature (JWS) compacto con EdDSA/Ed25519, usando las convenciones JOSE de RFC 7515 y RFC 8037. Las fechas usan NumericDate de JWT (RFC 7519). La interoperabilidad requiere publicar el perfil, mantener pruebas de conformidad y acordar cómo se distribuyen las claves de confianza y las revocaciones.

## Formato de transporte

Un certificado es un token compacto de tres segmentos:

\`BASE64URL(protected-header).BASE64URL(claims).BASE64URL(signature)\`

Cabecera protegida obligatoria:

\`\`\`json
{"alg":"EdDSA","kid":"issuer-key-2026-01","typ":"NODECORE-CERT+JWT"}
\`\`\`

No se aceptan algoritmos alternativos, \`none\`, cabeceras críticas desconocidas ni una clave de emisor que no figure en el almacén de confianza local.

Ejemplo ilustrativo de claims (valores ficticios; no es una credencial válida):

\`\`\`json
{
  "iss": "did:nodecore:issuer-example",
  "sub": "node-example-001",
  "jti": "00000000-0000-4000-8000-000000000001",
  "iat": 1790000000,
  "nbf": 1790000000,
  "exp": 1792592000,
  "node_core": {
    "format": "node-core-os-node-identity",
    "version": "1.0",
    "profile": "identity-key-protection",
    "subject_public_key": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  }
}
\`\`\`

La clave pública de sujeto es una clave Ed25519 raw de 32 bytes representada en hexadecimal. La clave privada del nodo nunca se incluye en el certificado. La firma la produce la clave privada del emisor; el verificador debe disponer de la clave pública de ese emisor por un canal de confianza independiente.

## Perfiles v1.0

| Identificador | Alcance de evaluación |
|---|---|
| \`sybil-resistance\` | Controles contra identidades/nodos múltiples falsos |
| \`p2p-partition-eclipse-resistance\` | Diversidad de pares y resistencia a aislamiento/eclipse |
| \`byzantine-collusion-resistance\` | Detección/mitigación de comportamiento bizantino y colusión |
| \`identity-key-protection\` | Vinculación de clave, custodia, rotación y revocación |
| \`software-supply-chain-integrity\` | Procedencia, dependencias, artefactos y actualizaciones |
| \`availability-ddos-resistance\` | Límites de recursos y disponibilidad bajo carga |
| \`ipfs-content-integrity\` | Verificación de CID, importación y tratamiento de contenido |
| \`privilege-and-pool-isolation\` | Menor privilegio, límites de confianza y aislamiento de pools |

**Importante:** el campo \`profile\` etiqueta el propósito o el perfil evaluado; por sí solo no demuestra que un nodo haya pasado pruebas. Para expresar resultados de evaluación, emita un artefacto de evaluación separado con versión del plan, herramientas, commit, fecha, límites, resultados y firma del evaluador. No use “aprobado” sin evidencia reproducible y criterios de aceptación publicados.

## Reglas de emisión y verificación

1. Emisor autorizado crea una credencial con identificador único \`jti\`.
2. El emisor firma header y payload con Ed25519. No comparta ni suba la clave privada al repositorio.
3. El verificador comprueba firma, \`kid\` confiable, formato, perfil, fechas y revocación.
4. Valide también el vínculo entre \`sub\` y la clave pública conforme al protocolo de enrolamiento de la red. Una firma válida no equivale a autorización para todas las acciones.
5. Rechace credenciales vencidas, revocadas, con formato desconocido o emisor no confiable. La tolerancia de reloj debe ser pequeña y configurable por despliegue.
6. El estado de revocación debe tener procedencia, firma, fecha de actualización y política para actuar cuando esté obsoleto o no disponible.
7. No incluya datos personales ni secretos en \`metadata\`; se trata de un documento portable y potencialmente público.

## Ciclo de vida

- **Vigencia máxima v1.0:** 90 días. La política de emisión por defecto del código es 30 días.
- **Rotación:** emitir una nueva credencial y actualizar la distribución de confianza antes de retirar la antigua.
- **Revocación:** distribuir una lista autenticada de \`jti\` revocados; la función de verificación recibe el conjunto de IDs ya obtenido por el despliegue. La distribución firmada y la persistencia del registro son responsabilidad de una siguiente fase.
- **Compromiso del emisor:** retirar la clave del almacén de confianza, publicar el incidente y reemitir las credenciales afectadas.
- **Auditoría:** conservar el certificado, la clave identificadora del emisor, el resultado de verificación y el hash del informe de evaluación según política de retención.

## Modelo de confianza

Este formato no crea una autoridad mundial ni establece por sí solo quién puede emitir credenciales. Cada instalación debe configurar explícitamente sus emisores confiables. Para confianza entre organizaciones se necesita una política pública de enrolamiento, rotación, revocación, resolución de identificadores, gobernanza y gestión de incidentes.

El certificado acredita únicamente que una clave de emisor de confianza firmó unas afirmaciones concretas y que estas pasan las verificaciones criptográficas y temporales implementadas. No prueba que la entidad sea honesta, que el nodo esté libre de malware, que el contenido IPFS sea verdadero, ni que el sistema resista ataques en producción.

## Referencias normativas

- RFC 7515 — JSON Web Signature (JWS): https://www.rfc-editor.org/rfc/rfc7515
- RFC 7519 — JSON Web Token (JWT): https://www.rfc-editor.org/rfc/rfc7519
- RFC 8037 — CFRG Elliptic Curve Diffie-Hellman and Signatures in JOSE: https://www.rfc-editor.org/rfc/rfc8037
- RFC 5280 — X.509 PKI Certificate and CRL Profile (referencia de interoperabilidad distinta; este formato no es X.509): https://www.rfc-editor.org/rfc/rfc5280
