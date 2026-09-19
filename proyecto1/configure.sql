-- Configuracion de regiones de la base de datos
-- Region principal del sistema.
ALTER DATABASE ti4601
SET PRIMARY REGION "tienda-a";

-- Regiones adicionales.
ALTER DATABASE ti4601
ADD REGION IF NOT EXISTS "tienda-b";

ALTER DATABASE ti4601
ADD REGION IF NOT EXISTS "cd-central";

-- Verificacion de las regiones configuradas.
SHOW REGIONS FROM DATABASE ti4601;