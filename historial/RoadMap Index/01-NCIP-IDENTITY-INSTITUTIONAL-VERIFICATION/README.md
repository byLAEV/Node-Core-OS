# RMI-001 — NCIP: Identity and Institutional Verification

**Nombre de trabajo:** Node Core Identity Protocol (NCIP)  
**Estado:** PENDING_RESEARCH  
**Prioridad propuesta:** Alta — requiere confirmación y desglose.  
**Tipo:** Investigación, especificación, interoperabilidad e implementación futura.

## 1. Objetivo

Investigar, diseñar y eventualmente implementar en Node Core OS byLAEV una infraestructura interoperable para que un nodo pueda asociar una identidad declarada con evidencias de un documento personal y solicitar, cuando exista autorización y un mecanismo oficial, la verificación de ese documento ante la autoridad emisora.

La infraestructura deberá permitir que instituciones emisoras autorizadas puedan integrarse con Node Core OS mediante APIs, conectores o mecanismos de verificación que efectivamente ofrezcan.

Node Core OS actúa como infraestructura de conexión y verificación de evidencias; no se atribuye la autoridad legal de emitir identidades ni de certificar por sí mismo documentos gubernamentales.

## 2. Resultado deseado

Un nodo podrá:
1. Registrar una identidad declarada y asociarla a su identificador de nodo.
2. Registrar una referencia segura a un documento y sus evidencias.
3. Identificar país, jurisdicción, tipo de documento y autoridad emisora declarada.
4. Solicitar una verificación mediante un conector autorizado, si la institución ofrece ese servicio.
5. Recibir y conservar una respuesta verificable con procedencia, fecha, alcance y limitaciones.
6. Compartir con otros nodos únicamente resultados y evidencias que el titular esté autorizado a divulgar.

## 3. Verificaciones que deben mantenerse separadas

- **Autoridad emisora:** confirmar que la entidad declarada es competente para emitir ese tipo de documento.
- **Autenticidad documental:** comprobar que el documento o credencial fue emitido por la autoridad indicada.
- **Estado documental:** comprobar vigencia, expiración, cancelación o revocación cuando la fuente lo permita.
- **Correspondencia de atributos:** comprobar coincidencias de datos dentro de los límites legales y técnicos del servicio.
- **Vinculación con el titular:** demostrar que quien presenta la evidencia es el titular legítimo. La autenticidad del documento por sí sola no demuestra esta relación.

Los resultados no deben reducirse a un booleano. Deben contemplar, como mínimo, estados confirmados, parciales, pendientes, inconclusos, no verificados, expirados, revocados y no disponibles.

## 4. Alcance de investigación

### 4.1 Mapeo geográfico y de autoridades

- [ ] Definir la jerarquía geográfica: mundo, regiones, países, territorios y jurisdicciones.
- [ ] Definir el universo de países y áreas cubierto y la fuente de referencia.
- [ ] Identificar, por jurisdicción, autoridades de identificación personal.
- [ ] Identificar, por jurisdicción, autoridades emisoras de pasaportes.
- [ ] Identificar registros civiles y otras autoridades relevantes cuando proceda.
- [ ] Distinguir autoridad legal, operador del servicio, entidad de personalización y fabricante del documento.
- [ ] Registrar fuentes gubernamentales oficiales, fecha de consulta y nivel de confianza.
- [ ] Documentar jurisdicciones donde la competencia esté distribuida o no exista un documento nacional único.

### 4.2 Investigación de servicios institucionales

Para cada autoridad:
- [ ] Sitio y dominio oficial.
- [ ] Competencia legal y tipos de documentos.
- [ ] API pública, privada, portal o mecanismo alternativo de verificación.
- [ ] Documentación técnica y ambiente sandbox, si existe.
- [ ] Métodos de autenticación y seguridad.
- [ ] Permisos, convenios, requisitos legales y proceso de alta.
- [ ] Datos que acepta y devuelve.
- [ ] Capacidades: emisión, autenticidad, vigencia, revocación, coincidencia de atributos y titularidad.
- [ ] Límites de uso, cuotas, disponibilidad y condiciones económicas.
- [ ] Restricciones de privacidad, residencia y conservación de datos.
- [ ] Estado de verificación de cada dato y fecha de revisión.

No se debe asumir que una institución tiene una API individual de consulta por el hecho de tener un portal o servicios digitales públicos.

### 4.3 Diseño de Node Core OS

- [ ] Auditar el modelo de identidad y asociación nodo-entidad existente.
- [ ] Auditar el registro actual de evidencias y referencias documentales.
- [ ] Identificar permisos, solicitudes y mecanismos de autorización ya implementados.
- [ ] Definir brechas sin duplicar capacidades existentes.
- [ ] Diseñar API pública y versionada de Node Core OS.
- [ ] Diseñar registro mundial de emisores.
- [ ] Diseñar contrato común para conectores institucionales.
- [ ] Diseñar modelo de solicitud, respuesta, procedencia y evidencia.
- [ ] Diseñar consentimiento, autorización, auditoría y revocación.
- [ ] Definir comportamiento ante timeout, desconexión, límites de consulta y respuestas ambiguas.

### 4.4 Seguridad y privacidad

- [ ] No publicar documentos personales ni datos sensibles en IPFS.
- [ ] Minimizar los datos enviados a cada institución.
- [ ] Utilizar datos ficticios en fixtures y pruebas iniciales.
- [ ] Proteger credenciales y secretos de conectores.
- [ ] Autenticar y validar criptográficamente las respuestas cuando el mecanismo lo permita.
- [ ] Prevenir repetición de solicitudes y respuestas.
- [ ] Definir expiración, retención y eliminación de datos.
- [ ] Registrar auditoría sin exponer información personal innecesaria.
- [ ] Evaluar divulgación selectiva y pruebas de conocimiento cero cuando aporten valor y sean viables.

## 5. Entregables previstos

Los siguientes son entregables de planificación; todavía no representan especificaciones aprobadas ni software implementado.

1. GLOBAL-ISSUER-MAPPING.md — metodología y resultados del mapeo mundial.
2. GLOBAL-ISSUER-REGISTRY.json — catálogo estructurado de autoridades.
3. INSTITUTIONAL-API-INVENTORY.md — APIs, documentación y mecanismos investigados.
4. NCIP-ARCHITECTURE.md — arquitectura y límites de confianza.
5. NCIP-API-SPECIFICATION.md — contrato de la API ofrecida por Node Core OS.
6. NCIP-PERMISSIONS-AND-CONSENT.md — permisos, consentimiento y autorización.
7. NCIP-VERIFICATION-PROTOCOL.md — flujo y semántica de verificación.
8. CONNECTOR-DEVELOPMENT-GUIDE.md — contrato para adaptadores institucionales.
9. NCIP-THREAT-MODEL.md — amenazas, controles y privacidad.
10. NCIP-TEST-PLAN.md — pruebas unitarias, integración, interoperabilidad y resiliencia.

## 6. País piloto propuesto

Costa Rica se propone como primer caso de investigación, no como integración ya acordada.

La investigación deberá separar:
- Identificación personal y Registro Civil: Tribunal Supremo de Elecciones.
- Pasaportes: Dirección General de Migración y Extranjería.

Fuentes oficiales iniciales:
- https://www.tse.go.cr/
- https://www.migracion.go.cr/

Debe confirmarse con cada institución qué servicios de verificación existen, quién puede acceder, bajo qué base legal y con qué mecanismos técnicos.

## 7. Criterios de aceptación

La iniciativa no se considerará completada hasta que:
- El inventario defina claramente su cobertura geográfica y fuentes.
- Cada institución tenga evidencia oficial de su competencia.
- Las APIs y mecanismos estén clasificados como públicos, restringidos, no disponibles o pendientes de confirmar.
- El contrato NCIP defina solicitudes, respuestas, errores, permisos y procedencia.
- Los conectores tengan pruebas reproducibles con datos ficticios.
- Una integración real se pruebe únicamente con autorización institucional.
- Se demuestre que un fallo o falta de respuesta nunca se interpreta como verificación positiva.
- Se distinga autenticidad documental de vinculación entre persona y documento.

## 8. Dependencias y riesgos

- Legislación y protección de datos aplicable en cada jurisdicción.
- Convenios, permisos y credenciales que exijan las instituciones.
- Heterogeneidad de APIs y estándares nacionales.
- Ausencia de servicios de consulta individual.
- Calidad, disponibilidad y autenticidad de las respuestas.
- Protección de información personal y biométrica.
- Costos, cuotas y restricciones de uso institucional.

## 9. Principio de transparencia

Cada hallazgo deberá señalar si está confirmado por fuente oficial, inferido, propuesto o pendiente de comprobar. No se registrará una API como disponible sin documentación o confirmación institucional. No se registrará una integración como funcional sin prueba y autorización verificables.

## 10. Próximo trabajo

La primera tarea es completar la auditoría de los componentes de identidad ya existentes en Node Core OS y establecer la metodología del inventario mundial antes de diseñar endpoints definitivos.
