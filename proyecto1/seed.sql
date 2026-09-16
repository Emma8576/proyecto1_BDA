--- Datos para el proyecto 1

-- 1. Catalogo Global /Productos disponibles
UPSERT INTO producto (producto_id, sku, nombre, descripcion, precio) VALUES
    ('00000000-0000-0000-0000-000000000001', 'SKU-LAPTOP', 'Laptop Pro 15', 'Laptop de alto rendimiento', 1200.00),
    ('00000000-0000-0000-0000-000000000002', 'SKU-MONITOR', 'Monitor 27 4K', 'Monitor IPS ultra HD', 350.00),
    ('00000000-0000-0000-0000-000000000003', 'SKU-TECLADO', 'Teclado Mecanico', 'Teclado RGB switches blue', 85.00),
    ('00000000-0000-0000-0000-000000000004', 'SKU-MOUSE', 'Mouse Inalambrico', 'Mouse ergonomico 16000 DPI', 45.00);

-- 2. Stock Inicial por Region
INSERT INTO stock (region, producto_id, cantidad) VALUES
    -- tienda-a
    ('tienda-a', '00000000-0000-0000-0000-000000000001', 50),
    ('tienda-a', '00000000-0000-0000-0000-000000000002', 30),
    ('tienda-a', '00000000-0000-0000-0000-000000000003', 100),
    -- tienda-b
    ('tienda-b', '00000000-0000-0000-0000-000000000001', 20),
    ('tienda-b', '00000000-0000-0000-0000-000000000002', 15),
    ('tienda-b', '00000000-0000-0000-0000-000000000004', 80),
    -- cd-central
    ('cd-central', '00000000-0000-0000-0000-000000000001', 500),
    ('cd-central', '00000000-0000-0000-0000-000000000002', 300),
    ('cd-central', '00000000-0000-0000-0000-000000000003', 1000),
    ('cd-central', '00000000-0000-0000-0000-000000000004', 1000)
ON CONFLICT (region, producto_id) DO NOTHING;

-- 3. Pedidos Prueba
INSERT INTO pedido (region, pedido_id, estado, total) VALUES
    ('tienda-a', '10000000-0000-0000-0000-000000000001', 'COMPLETADO', 1200.00),
    ('tienda-b', '10000000-0000-0000-0000-000000000002', 'CREADO', 350.00),
    ('cd-central', '10000000-0000-0000-0000-000000000003', 'PAGADO', 130.00)
ON CONFLICT (region, pedido_id) DO NOTHING;

-- 4. Detalle de Pedidos
INSERT INTO detalle_pedido (region, pedido_id, producto_id, cantidad, precio_unitario) VALUES
    ('tienda-a', '10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 1, 1200.00),
    ('tienda-b', '10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 1, 350.00),
    ('cd-central', '10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003', 1, 85.00),
    ('cd-central', '10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004', 1, 45.00)
ON CONFLICT (region, pedido_id, producto_id) DO NOTHING;
