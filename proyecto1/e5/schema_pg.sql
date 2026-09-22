-- Schema simplificado para PostgreSQL (E5 — comparación de latencia)
-- Sin LOCALITY, sin crdb_internal_region; region es TEXT simple.

CREATE TABLE IF NOT EXISTS producto (
    producto_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku         TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    descripcion TEXT,
    precio      NUMERIC(12,2) NOT NULL CHECK (precio >= 0)
);

CREATE TABLE IF NOT EXISTS stock (
    region      TEXT NOT NULL,
    producto_id UUID NOT NULL REFERENCES producto(producto_id),
    cantidad    BIGINT NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (region, producto_id)
);

CREATE TABLE IF NOT EXISTS pedido (
    region    TEXT NOT NULL,
    pedido_id UUID NOT NULL DEFAULT gen_random_uuid(),
    estado    TEXT NOT NULL DEFAULT 'CREADO'
                   CHECK (estado IN ('CREADO','PAGADO','PREPARANDO','COMPLETADO','CANCELADO')),
    total     NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (region, pedido_id)
);

CREATE TABLE IF NOT EXISTS detalle_pedido (
    region          TEXT NOT NULL,
    pedido_id       UUID NOT NULL,
    producto_id     UUID NOT NULL REFERENCES producto(producto_id),
    cantidad        BIGINT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario >= 0),
    PRIMARY KEY (region, pedido_id, producto_id),
    FOREIGN KEY (region, pedido_id) REFERENCES pedido(region, pedido_id)
);