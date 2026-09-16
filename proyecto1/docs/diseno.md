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

## 3. Esquema lógico

A partir de las entidades definidas anteriormente, se propone el siguiente esquema lógico para el sistema de comercio e inventario multi-tienda.

### 3.1 producto

La entidad `producto` representa el catálogo general de productos disponibles en la empresa.

| Atributo      | Descripción                                                         |
| ------------- | ------------------------------------------------------------------- |
| `producto_id` | Identificador único del producto. Clave primaria.                   |
| `sku`         | Código único utilizado para identificar comercialmente el producto. |
| `nombre`      | Nombre del producto.                                                |
| `descripcion` | Descripción general del producto.                                   |
| `precio`      | Precio actual del producto.                                         |

**Clave primaria:**

`producto_id`

El catálogo de productos será compartido entre todas las regiones, por lo que cada tienda tendrá acceso a la misma información general de los productos.

---

### 3.2 stock

La entidad `stock` representa la cantidad disponible de un producto en una región determinada.

| Atributo         | Descripción                                             |
| ---------------- | ------------------------------------------------------- |
| `region`         | Región a la que pertenece el inventario.                |
| `producto_id`    | Producto al que pertenece el registro de inventario.    |
| `cantidad`       | Cantidad disponible del producto en la región.          |
| `actualizado_en` | Fecha y hora de la última actualización del inventario. |

**Clave primaria compuesta:**

`(region, producto_id)`

**Clave foránea:**

`producto_id → producto(producto_id)`

La clave primaria incluye la región debido a que un mismo producto puede existir simultáneamente en el inventario de varias tiendas. De esta forma, cada combinación de región y producto representa un registro de inventario independiente.

---

### 3.3 pedido

La entidad `pedido` representa una compra realizada en una región determinada.

| Atributo    | Descripción                            |
| ----------- | -------------------------------------- |
| `region`    | Región en la que se realizó el pedido. |
| `pedido_id` | Identificador del pedido.              |
| `estado`    | Estado actual del pedido.              |
| `total`     | Monto total del pedido.                |
| `creado_en` | Fecha y hora en que se creó el pedido. |

**Clave primaria compuesta:**

`(region, pedido_id)`

La región forma parte de la clave primaria para identificar la región hogar del pedido y permitir que los pedidos puedan distribuirse según la tienda donde fueron realizados.

---

### 3.4 detalle_pedido

La entidad `detalle_pedido` representa los productos que forman parte de un pedido.

| Atributo          | Descripción                                                     |
| ----------------- | --------------------------------------------------------------- |
| `region`          | Región a la que pertenece el pedido.                            |
| `pedido_id`       | Pedido al que pertenece el detalle.                             |
| `producto_id`     | Producto incluido en el pedido.                                 |
| `cantidad`        | Cantidad comprada del producto.                                 |
| `precio_unitario` | Precio del producto utilizado al momento de realizar el pedido. |

**Clave primaria compuesta:**

`(region, pedido_id, producto_id)`

**Claves foráneas:**

`(region, pedido_id) → pedido(region, pedido_id)`

`producto_id → producto(producto_id)`

Se almacena `precio_unitario` en el detalle para conservar el precio utilizado en el momento de realizar el pedido, aunque posteriormente cambie el precio actual almacenado en `producto`.

---

## 4. Relaciones entre entidades

Las relaciones principales del modelo son las siguientes:

* Un `producto` puede tener registros de `stock` en varias regiones.
* Cada registro de `stock` pertenece a un único `producto` y a una única región.
* Cada `pedido` pertenece a una región.
* Un `pedido` puede contener uno o varios registros de `detalle_pedido`.
* Cada `detalle_pedido` pertenece a un único pedido.
* Cada `detalle_pedido` hace referencia a un producto del catálogo general.

De forma simplificada, las relaciones pueden representarse como:

```text
producto
   │
   ├──────────────< stock
   │
   └──────────────< detalle_pedido >──────── pedido
```

La información global de los productos se mantiene separada de los datos regionales de inventario y pedidos. Esto permitirá posteriormente definir distintas estrategias de localidad y fragmentación para cada tipo de información.

## 5. Fragmentación horizontal

Para distribuir la información entre las tres regiones del sistema se utilizará fragmentación horizontal basada en el atributo `region`.

Las regiones definidas para el proyecto son:

* `tienda-a`
* `tienda-b`
* `cd-central`

Las tablas `stock` y `pedido` contienen información propia de cada región, por lo que se fragmentarán horizontalmente utilizando el valor de `region`.

### 5.1 Fragmentación de stock

La tabla `stock` contiene las existencias de cada producto en las diferentes regiones.

Se definen los siguientes fragmentos:

```text
STOCK_A = σ region = 'tienda-a' (stock)

STOCK_B = σ region = 'tienda-b' (stock)

STOCK_CD = σ region = 'cd-central' (stock)
```

Los predicados equivalentes en SQL son:

```sql
region = 'tienda-a'

region = 'tienda-b'

region = 'cd-central'
```

Cada registro de `stock` pertenece a la región donde se encuentra físicamente el inventario correspondiente.

Por ejemplo, si un producto tiene existencias tanto en `tienda-a` como en `tienda-b`, existirán dos registros diferentes:

```text
(region='tienda-a', producto_id=X)

(region='tienda-b', producto_id=X)
```

Esto permite que cada tienda gestione de manera independiente su inventario.

---

### 5.2 Fragmentación de pedido

Los pedidos también se distribuyen según la región donde fueron realizados.

Se definen los siguientes fragmentos:

```text
PEDIDO_A = σ region = 'tienda-a' (pedido)

PEDIDO_B = σ region = 'tienda-b' (pedido)

PEDIDO_CD = σ region = 'cd-central' (pedido)
```

Los predicados equivalentes en SQL son:

```sql
region = 'tienda-a'

region = 'tienda-b'

region = 'cd-central'
```

Cada pedido pertenece únicamente a la región en la que se originó.

De esta forma, los pedidos realizados en `tienda-a` tendrán como región hogar `tienda-a`, mientras que los pedidos generados en `tienda-b` tendrán como región hogar `tienda-b`.

El centro de distribución `cd-central` también puede almacenar pedidos u operaciones generadas desde su propia región.

---

## 6. Propiedades de la fragmentación

Para que la fragmentación horizontal sea válida se analizan las propiedades de completitud, reconstrucción y disyunción.

### 6.1 Completitud

La fragmentación cumple la propiedad de completitud porque todos los registros de las tablas fragmentadas pertenecen a una de las tres regiones definidas.

Para `stock`:

```text
stock = STOCK_A ∪ STOCK_B ∪ STOCK_CD
```

Para `pedido`:

```text
pedido = PEDIDO_A ∪ PEDIDO_B ∪ PEDIDO_CD
```

Por lo tanto, ningún registro válido queda fuera de los fragmentos definidos.

**Se cumple:** Sí.

---

### 6.2 Reconstrucción

La información original puede reconstruirse mediante la unión de todos los fragmentos.

Para `stock`:

```sql
SELECT * FROM STOCK_A
UNION ALL
SELECT * FROM STOCK_B
UNION ALL
SELECT * FROM STOCK_CD;
```

Conceptualmente:

```text
stock = STOCK_A ∪ STOCK_B ∪ STOCK_CD
```

De igual manera:

```text
pedido = PEDIDO_A ∪ PEDIDO_B ∪ PEDIDO_CD
```

Debido a que cada fragmento conserva todos los atributos de la relación original, la unión de los fragmentos permite recuperar la relación completa.

**Se cumple:** Sí.

---

### 6.3 Disyunción

Los fragmentos son disyuntos porque un mismo registro solo puede poseer un valor para el atributo `region`.

Por ejemplo, un registro de `stock` no puede cumplir simultáneamente:

```sql
region = 'tienda-a'
```

y

```sql
region = 'tienda-b'
```

Por lo tanto:

```text
STOCK_A ∩ STOCK_B = ∅
STOCK_A ∩ STOCK_CD = ∅
STOCK_B ∩ STOCK_CD = ∅
```

El mismo principio se aplica a los fragmentos de `pedido`.

**Se cumple:** Sí.

---

## 7. Tabla de verificación de fragmentación

| Propiedad      | ¿Se cumple? | Justificación                                                                                                              |
| -------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------- |
| Completitud    | Sí          | Todo registro de `stock` y `pedido` pertenece a una de las tres regiones definidas: `tienda-a`, `tienda-b` o `cd-central`. |
| Reconstrucción | Sí          | La relación original puede obtenerse mediante la unión de los tres fragmentos regionales.                                  |
| Disyunción     | Sí          | Cada registro posee un único valor de `region`, por lo que no puede pertenecer simultáneamente a dos fragmentos.           |

## 8. Estrategia de replicación

No todas las relaciones del sistema requieren el mismo tipo de distribución. Se utilizarán distintas estrategias según la forma en que los datos son consultados y modificados.

### 8.1 Catálogo de productos

La relación `producto` contiene información general utilizada por todas las tiendas, como el nombre, SKU, descripción y precio de los productos.

Esta información será configurada como una tabla global:

```text
producto → GLOBAL
```

El objetivo es que el catálogo pueda consultarse eficientemente desde cualquiera de las tres regiones sin depender constantemente de una región específica.

La tabla `producto` es un buen candidato para replicación debido a que:

* es consultada frecuentemente desde todas las regiones;
* su tamaño esperado es menor que el de las tablas transaccionales;
* presenta menos escrituras que las tablas de inventario y pedidos;
* evita accesos remotos frecuentes al consultar información de productos.

El costo adicional de mantener copias del catálogo se considera aceptable frente al beneficio de disponer de la información cerca de cada región.

En CockroachDB esta decisión será representada mediante:

```sql
LOCALITY GLOBAL
```

---

## 9. Asignación regional de los fragmentos

Las tablas `stock` y `pedido` contienen información regional y serán distribuidas según el atributo `region`.

La asignación propuesta es la siguiente:

| Nodo     | Región       | Fragmentos principales  |
| -------- | ------------ | ----------------------- |
| `crdb-1` | `tienda-a`   | `STOCK_A`, `PEDIDO_A`   |
| `crdb-2` | `tienda-b`   | `STOCK_B`, `PEDIDO_B`   |
| `crdb-3` | `cd-central` | `STOCK_CD`, `PEDIDO_CD` |

Cada fila tendrá una región hogar determinada por el valor almacenado en el atributo `region`.

Conceptualmente:

```text
                         producto
                          GLOBAL
                  ┌─────────┼─────────┐
                  │         │         │
                  ▼         ▼         ▼

               crdb-1    crdb-2    crdb-3
              tienda-a   tienda-b   cd-central
                  │         │         │
                  │         │         │
              STOCK_A   STOCK_B   STOCK_CD
              PEDIDO_A  PEDIDO_B  PEDIDO_CD
```

Las relaciones `stock` y `pedido` serán implementadas utilizando:

```sql
LOCALITY REGIONAL BY ROW AS region
```

De esta forma, el atributo `region` determina la región hogar de cada registro.

---

## 10. Asignación de detalle_pedido

La relación `detalle_pedido` está directamente asociada con `pedido`.

Por esta razón, los detalles de un pedido deben conservar la misma región que el pedido al que pertenecen.

La fragmentación conceptual es:

```text
DETALLE_A =
σ region = 'tienda-a' (detalle_pedido)

DETALLE_B =
σ region = 'tienda-b' (detalle_pedido)

DETALLE_CD =
σ region = 'cd-central' (detalle_pedido)
```

Su asignación será:

| Fragmento    | Región       |
| ------------ | ------------ |
| `DETALLE_A`  | `tienda-a`   |
| `DETALLE_B`  | `tienda-b`   |
| `DETALLE_CD` | `cd-central` |

Esto permite mantener los datos relacionados con un pedido en la misma región lógica.

---

## 11. Política de escritura del inventario

Cada región será responsable principalmente de las escrituras sobre su propio inventario.

Por ejemplo:

```text
tienda-a
    ↓
STOCK_A

tienda-b
    ↓
STOCK_B

cd-central
    ↓
STOCK_CD
```

Una operación originada en `tienda-a` no deberá modificar directamente el inventario perteneciente a `tienda-b`.

Como excepción, `cd-central` podrá participar en procesos de sincronización de inventario mediante operaciones batch documentadas.

Esta política permite representar el requisito del dominio donde el inventario de cada tienda se administra regionalmente, mientras el centro de distribución mantiene la posibilidad de ejecutar procesos de sincronización.

---

## 12. Resumen de estrategia de distribución

| Relación         | Estrategia        | Justificación                                                                                                |
| ---------------- | ----------------- | ------------------------------------------------------------------------------------------------------------ |
| `producto`       | `GLOBAL`          | Catálogo compartido y consultado frecuentemente desde todas las regiones.                                    |
| `stock`          | `REGIONAL BY ROW` | El inventario pertenece a una región específica y sus escrituras deben realizarse principalmente desde ella. |
| `pedido`         | `REGIONAL BY ROW` | Cada pedido pertenece a la región donde fue generado.                                                        |
| `detalle_pedido` | `REGIONAL BY ROW` | Los detalles deben conservar la misma región lógica que el pedido al que pertenecen.                         |

Con esta estrategia se busca reducir accesos remotos para las operaciones comunes de cada tienda y, al mismo tiempo, mantener disponible el catálogo general de productos en todas las regiones.
