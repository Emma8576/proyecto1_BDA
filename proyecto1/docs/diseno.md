# E1 — Diseño de fragmentación y asignación

## 1. Dominio

El sistema representa una empresa de comercio con múltiples tiendas que
comparten un catálogo de productos, pero mantienen de manera regional el
stock disponible y los pedidos realizados.

Se utilizarán tres regiones simuladas:

- tienda-a
- tienda-b
- cd-central

`tienda-a` y `tienda-b` representan dos puntos de venta independientes.

`cd-central` representa el centro de distribución encargado del inventario
central y de procesos de sincronización con las tiendas.

## 2. Entidades principales

El sistema utilizará las siguientes entidades:

### producto

Representa los productos disponibles en el catálogo general de la empresa.

### stock

Representa la cantidad disponible de cada producto en una región determinada.

### pedido

Representa una compra realizada en una tienda o región determinada.

### detalle_pedido

Representa los productos que forman parte de cada pedido.