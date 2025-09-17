# Proyecto 1: Introducción a la ciencia de datos.


- Michael Rodriguez Arana
- Yeifer Ronaldo Muñoz Valencia
- Juan Carlos Rojas Quintero


## 1. Diseño del Modelo de la Bodega de Datos

    Modelo elegido: Esquema Estrella 

    Se escogió este modelo porque las consultas analíticas requeridas (ventas por categoría, clientes con más compras) son directas y se benefician de la menor cantidad de uniones, lo que resulta en un mejor rendimiento.

    Diagrama de la bodega de datos:

[![](/images/BancoDeDatos.png)](/images/BancoDeDatos.png)

### Scripts de creación de las tablas

```sql
-- Dimensión Cliente
CREATE TABLE dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50),
    gender VARCHAR(10),
    age INT
);

-- Dimensión Producto
CREATE TABLE dim_product (
    product_key SERIAL PRIMARY KEY,
    category VARCHAR(100)
);

-- Dimensión Tiempo
CREATE TABLE dim_date (
    date_key SERIAL PRIMARY KEY,
    invoice_date DATE
);

-- Dimensión Ubicación
CREATE TABLE dim_location (
    location_key SERIAL PRIMARY KEY,
    shopping_mall VARCHAR(100)
);

-- Dimensión Método de Pago
CREATE TABLE dim_payment (
    payment_key SERIAL PRIMARY KEY,
    payment_method VARCHAR(50)
);

-- Tabla de hechos
CREATE TABLE fact_sales (
    fact_id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(50),
    customer_key INT REFERENCES dim_customer(customer_key),
    product_key INT REFERENCES dim_product(product_key),
    date_key INT REFERENCES dim_date(date_key),
    location_key INT REFERENCES dim_location(location_key),
    payment_key INT REFERENCES dim_payment(payment_key),
    quantity INT,
    price NUMERIC(10,2)
);
```


## 2. Extracción, Transformación y Carga de Datos.

### Documentación del Proceso ETL.

#### Creación de Tablas de Dimensiones
En esta fase, aislamos los atributos descriptivos del conjunto de datos principales para crear tablas de dimensiones. Cada tabla representará una entidad de negocio única (Cliente, Producto, Fecha, Ubicación y Método de Pago).


El método .drop_duplicates() es fundamental aquí, ya que garantiza que cada tabla de dimensión contenga solo valores únicos, eliminando la redundancia.

```python

# Crear dataframes únicos para cada dimensión
dim_customer = df[['customer_id', 'gender', 'age']].drop_duplicates().reset_index(drop=True)
dim_product = df[['category']].drop_duplicates().reset_index(drop=True)
dim_date = df[['invoice_date']].drop_duplicates().reset_index(drop=True)
dim_location = df[['shopping_mall']].drop_duplicates().reset_index(drop=True)
dim_payment = df[['payment_method']].drop_duplicates().reset_index(drop=True)


```
#### Generación de Claves Sustitutas

Una vez creadas las dimensiones, se asigna una clave sustituta a cada una.

El propósito de usar claves sustitutas en lugar de las claves de negocio originales es:

    Eficiencia: Las uniones (joins) entre tablas son mucho más rápidas con índices enteros que con cadenas de texto.

    Independencia: Desvinculan la bodega de datos de los posibles cambios en los sistemas de origen. Si un customer_id cambia, la clave sustituta interna permanece igual.

    Gestión de Historial: Facilitan la implementación de dimensiones lentamente cambiantes (SCD) si se necesitara en el futuro.


```python

# Agregar surrogate keys
dim_customer['customer_key'] = dim_customer.index + 1
dim_product['product_key'] = dim_product.index + 1
dim_date['date_key'] = dim_date.index + 1
dim_location['location_key'] = dim_location.index + 1
dim_payment['payment_key'] = dim_payment.index + 1


```

#### Construcción de la Tabla de Hechos

Construcción de la Tabla de Hechos

Esta es la fase final donde se ensambla la tabla de hechos. Utilizando una serie de operaciones .merge(), el script vuelve a unir las dimensiones con el DataFrame original.

El objetivo de estos merge es reemplazar las columnas de texto descriptivas (ej. category, shopping_mall) por las claves sustitutas numéricas que se generaron en el paso anterior.

Finalmente, se seleccionan únicamente las columnas necesarias para la tabla de hechos:

- Las claves sustitutas de cada dimensión.

- Las métricas cuantitativas (quantity, price).

- Cualquier dimensión degenerada (invoice_no).

El resultado es una tabla de hechos compacta y optimizada.

```python
# Merge para construir la tabla de hechos
fact_sales = df.merge(dim_customer, on=['customer_id', 'gender', 'age'])
fact_sales = fact_sales.merge(dim_product, on='category')
fact_sales = fact_sales.merge(dim_date, on='invoice_date')
fact_sales = fact_sales.merge(dim_location, on='shopping_mall')
fact_sales = fact_sales.merge(dim_payment, on='payment_method')

# Seleccionar las columnas finales para la tabla de hechos
fact_sales = fact_sales[['invoice_no',
                         'customer_key',
                         'product_key',
                         'date_key',
                         'location_key',
                         'payment_key',
                         'quantity',
                         'price']]

```

#### Comprobación de que los datos han sido correctamente insertados en la base de datos.

Para comprobar si los datos fueron correctamente insertados podemos realizar una consultar basica en la base de datos.

[![](consultaSQL.png)](ConsultaSQL.png)

## 3. Consultas Analíticas en SQL

### Total de Ventas por Categoría de Producto

[![consulta1](/images/1.consulta.jpeg)](/images/1.consulta.jpeg)

Esta consulta calcula los ingresos totales generados por cada categoría de producto, ordenándolos de mayor a menor para identificar las más importantes para el negocio.

```sql
 SELECT
    p.category,
    SUM(f.quantity * f.price) AS total_ventas
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY total_ventas DESC;

```

```sql
SELECT p.category, SUM(f.quantity * f.price) AS total_ventas: Selecciona el nombre de la categoría y calcula la venta total. La venta de cada fila se obtiene multiplicando quantity por price, y luego SUM() agrega estos valores para cada categoría.

FROM fact_sales f JOIN dim_product p ON f.product_key = p.product_key: Une la tabla de hechos fact_sales con la dimensión de producto dim_product usando la clave product_key. Esto permite asociar cada venta con su respectiva categoría.

GROUP BY p.category: Agrupa todas las filas por el nombre de la categoría para que SUM() calcule el total de cada una de ellas por separado.

ORDER BY total_ventas DESC: Ordena los resultados de forma descendente, mostrando las categorías con mayores ventas primero.
```


### Clientes con mayor volumen de compras

[![consulta2](/images/2.consulta.jpeg)](/images/2.consulta.jpeg)

```sql

 SELECT
    c.customer_id,
    c.gender,
    c.age,
    SUM(f.quantity * f.price) AS total_compras,
    COUNT(DISTINCT f.invoice_no) AS numero_facturas
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_id, c.gender, c.age
ORDER BY total_compras DESC
LIMIT 10;

```

```sql

Relaciona fact_sales con dim_customer para obtener información de los clientes.

SUM(f.quantity * f.price) da el gasto total de cada cliente.

COUNT(DISTINCT f.invoice_no) cuenta cuántas facturas (compras únicas) tiene cada cliente.

Se agrupa por cliente (GROUP BY c.customer_id, c.gender, c.age).

Se ordena de mayor a menor gasto (ORDER BY total_compras DESC).

Se limita a los 10 clientes más valiosos.
```


### Métodos de pago más utilizados.

[![consulta3](/images/3.consulta.jpeg)](/images/3.consulta.jpeg)


```sql
SELECT
    pm.payment_method,
    COUNT(*) AS cantidad_transacciones,
    SUM(f.quantity * f.price) AS total_vendido
FROM fact_sales f
JOIN dim_payment pm ON f.payment_key = pm.payment_key
GROUP BY pm.payment_method
ORDER BY cantidad_transacciones DESC;
```

```sql

Une fact_sales con dim_payment para obtener el método de pago de cada transacción.

COUNT(*) cuenta cuántas transacciones se hicieron con cada método.

SUM(f.quantity * f.price) calcula el total vendido por método de pago.

Se ordena por cantidad de transacciones (ORDER BY cantidad_transacciones DESC).

```
### Comparación de ventas por mes.
[![consulta4](/images/4.consulta.jpeg)](/images/4.consulta.jpeg)

```sql
 SELECT
    DATE_TRUNC('month', d.invoice_date)::date AS mes,
    SUM(f.quantity * f.price) AS total_ventas,
    COUNT(DISTINCT f.invoice_no) AS numero_facturas
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY mes
ORDER BY mes;
```
```sql

Usa dim_date para obtener la fecha de cada venta.

DATE_TRUNC('month', d.invoice_date) agrupa las fechas por mes.

SUM(f.quantity * f.price) calcula las ventas totales del mes.

COUNT(DISTINCT f.invoice_no) mide el número de facturas distintas por mes.

Se ordena cronológicamente (ORDER BY mes).

```

## 4. Análisis Descriptivo y Visualización de Datos.

### Analisis realizados.




## 5. Conclusiones y Presentación Final