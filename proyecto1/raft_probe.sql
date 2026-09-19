-- E4 — Tabla de control para observar mayoría Raft (RF=3).
-- Usa la BD ti4601 (ya configurada con 3 regiones).
-- No usa REGIONAL BY ROW para que los rangos sean globales
-- y la prueba no dependa de la región hogar de la fila.

CREATE TABLE IF NOT EXISTS ti4601.public.stock_probe (
    id          INT8        PRIMARY KEY,
    region_src  STRING      NOT NULL,   -- región del nodo que hizo la escritura
    version     INT8        NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO ti4601.public.stock_probe (id, region_src, version)
VALUES (1, 'tienda-a', 0)
ON CONFLICT (id) DO NOTHING;