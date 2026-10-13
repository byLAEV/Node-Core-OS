# Node Core OS P2P Contracts

## Estado

Primera prueba local en desarrollo. Incluye un formulario de solicitud pública de intercambio BTC por otro activo, documentos JSON con hashes, manifiesto local encadenado, registro local de evidencias y consulta por ID. Todavía no transmite mensajes entre nodos ni publica documentos en IPFS.

## Primera función

El formulario permite indicar la cantidad de BTC ofrecida, el activo y la cantidad que se desea recibir, la red correspondiente, la descripción de condiciones y uno o varios métodos de contacto. Los tipos de contacto admitidos son correo electrónico, teléfono, clave pública PGP, oficina, protocolo externo u otro.

El identificador técnico del nodo se obtiene de la identidad de Kubo. Si existe un perfil de identidad local, sus campos se muestran para que el usuario seleccione cuáles autoriza a incluir. La solicitud no debe publicarse ni compartirse sin consentimiento explícito sobre los datos que contiene.

Esta versión guarda los documentos y el manifiesto únicamente en el almacenamiento local de Node Core OS. No está visible para otros nodos todavía.

## Evidencia y consulta

La aplicación permite agregar un registro de respuesta o resultado vinculado por el ID de solicitud. La consulta por ID busca en el manifiesto local, verifica los hashes de la solicitud y de las evidencias relacionadas y muestra si la solicitud sigue abierta o tiene un resultado final registrado.

Los resultados son declaraciones no verificadas. Un resultado marcado como intercambio completado significa que alguien registró esa declaración; no prueba por sí solo que se haya liquidado una transferencia de BTC u otro activo.

## Almacenamiento

Los documentos se guardan bajo la raíz de almacenamiento de Node Core OS, en los directorios p2p_contracts/requests, p2p_contracts/evidence y p2p_contracts/manifests. No se guardan dentro del árbol de código que reemplaza el actualizador.

## Ejecutar las pruebas

Desde la raíz del repositorio:

    python -m unittest applications.p2p_contracts.tests.test_service

Las pruebas deben ejecutarse en el entorno real de desarrollo antes de afirmar que pasan. La publicación IPFS, la propagación entre nodos y los instaladores quedan para fases posteriores.
