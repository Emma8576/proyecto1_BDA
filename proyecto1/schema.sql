-- Esquema de base de datos distribuida

-- Producto

CREATE TABLE IF NOT EXISTS producto (
    producto_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku STRING NOT NULL UNIQUE,
    nombre STRING NOT NULL,
    descripcion STRING,
    precio DECIMAL(12, 2) NOT NULL CHECK (precio >= 0)
) LOCALITY GLOBAL;


-- Stock

CREATE TABLE IF NOT EXISTS stock (
    region crdb_internal_region NOT NULL,
    producto_id UUID NOT NULL,
    cantidad INT8 NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (region, producto_id),

    CONSTRAINT fk_stock_producto
        FOREIGN KEY (producto_id)
        REFERENCES producto (producto_id)
) LOCALITY REGIONAL BY ROW AS region;


-- Pedido

CREATE TABLE IF NOT EXISTS pedido (
    region crdb_internal_region NOT NULL,
    pedido_id UUID NOT NULL DEFAULT gen_random_uuid(),
    estado STRING NOT NULL DEFAULT 'CREADO',
    total DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (region, pedido_id),

    CONSTRAINT chk_estado_pedido
        CHECK (estado IN (
            'CREADO',
            'PAGADO',
            'PREPARANDO',
            'COMPLETADO',
            'CANCELADO'
        ))
) LOCALITY REGIONAL BY ROW AS region;


-- Detalle del pedido

CREATE TABLE IF NOT EXISTS detalle_pedido (
    region crdb_internal_region NOT NULL,
    pedido_id UUID NOT NULL,
    producto_id UUID NOT NULL,
    cantidad INT8 NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(12, 2) NOT NULL
        CHECK (precio_unitario >= 0),

    PRIMARY KEY (region, pedido_id, producto_id),

    CONSTRAINT fk_detalle_pedido
        FOREIGN KEY (region, pedido_id)
        REFERENCES pedido (region, pedido_id),

    CONSTRAINT fk_detalle_producto
        FOREIGN KEY (producto_id)
        REFERENCES producto (producto_id)
) LOCALITY REGIONAL BY ROW AS region;