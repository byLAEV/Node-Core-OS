# Portal público de Node Core OS byLAEV

Sitio estático, adaptable a móviles, para presentar el proyecto, sus dominios de almacenamiento, documentación, descargas oficiales y ejecuciones recientes de GitHub Actions. El portal no ejecuta instaladores en el navegador ni afirma que una función esté terminada únicamente porque aparezca documentada.

## Archivos

- `index.html`: portada en español, arquitectura, áreas de trabajo, pruebas, descargas y estado de CI.
- `identity.html`: explicación de arquitectura de identidad y evidencias, con límites explícitos entre propuestas y funciones verificadas.
- `remembering.html`: principios de memoria, olvido, restricciones, expiración y límites de la distribución.
- `menus.html`: guía visual de menús documentados; la interfaz gráfica es ilustrativa y no controla un nodo en ejecución.
- `assets/styles.css`: estilos adaptables, foco accesible y soporte de movimiento reducido.
- `assets/app.js`: consulta la API pública de GitHub para mostrar ejecuciones de CI, instalador E2E y pruebas P2P de tres nodos. No incluye tokens ni secretos.

## Previsualización local

Desde la raíz del repositorio:

```bash
python3 -m http.server 8000 --directory web-test-bench
```

Abre `http://localhost:8000`. El panel de ejecuciones requiere conexión a la API pública de GitHub.

## Validación

Ejecuta desde la raíz del repositorio:

```bash
python3 scripts/validate_web_test_bench.py
node --check web-test-bench/assets/app.js
```

La validación estructural no sustituye una prueba completa en navegador ni los workflows reales de instalación y P2P.

## Publicación

El workflow `.github/workflows/pages.yml` valida el portal y publica el directorio `web-test-bench` en GitHub Pages al recibir cambios en `main`. En Settings → Pages, la fuente de publicación debe ser **GitHub Actions**. Confirma el resultado de la ejecución de Pages después del commit.

## Estado en vivo y límites

- Los estados y enlaces de ejecución proceden de la API pública de GitHub.
- El sitio muestra hasta cuatro ejecuciones recientes por workflow configurado.
- La API puede limitar solicitudes o no estar disponible temporalmente; los enlaces directos siguen siendo útiles.
- Las fechas se presentan en la zona horaria de Costa Rica.
- El portal no inicia ni reejecuta workflows. Usa GitHub Actions y sus controles de acceso.
- Los resultados aplican al commit probado por cada ejecución; no prueban funciones que el workflow no cubra.
- Descubrimiento de pares no es autorización; presencia online no demuestra confianza; firmas locales no prueban por sí solas consenso distribuido.
- IPFS no cifra automáticamente los datos. Eliminar una referencia local o quitar un pin no garantiza la eliminación de copias remotas.
- La versión 1.5.4 declara Ubuntu 24.04 x86-64 como objetivo; Termux/Android requieren validación independiente.

## Accesibilidad y seguridad

Los enlaces externos abren con `rel="noopener noreferrer"`. Los resultados se crean con APIs DOM y texto sin interpretar datos de GitHub como HTML. No se incorpora credencial alguna al JavaScript público.
