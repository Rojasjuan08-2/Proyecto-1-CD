import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates
import seaborn as sns
from sqlalchemy import create_engine

# Configuración de estilo
sns.set(style="whitegrid", palette="muted")

# Conexión a la bodega de datos
engine = create_engine("postgresql+psycopg2://mi_usuario:1122919783@localhost:5432/ProyectoCD")

# 1. Total de ventas por categoría
query1 = """
SELECT p.category, SUM(f.quantity * f.price) AS total_ventas
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY total_ventas DESC;
"""
ventas_categoria = pd.read_sql(query1, engine)

plt.figure(figsize=(12,7))
ax = sns.barplot(
    data=ventas_categoria, 
    x="total_ventas", 
    y="category", 
    palette="Blues_r"
)

plt.title("Total de ventas por categoría", fontsize=16)
plt.xlabel("Ventas", fontsize=12)
plt.ylabel("Categoría", fontsize=12)

ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x/1e6:.1f}M'))

# Agregar etiquetas con separador de miles
for i, v in enumerate(ventas_categoria["total_ventas"]):
    ax.text(
        v, i, f'{v:,.0f}',   # separa miles con comas -> 1,234,567
        va='center', ha='left',
        fontsize=10, color="black", weight="bold"
    )

plt.show()


# 2. Top 10 clientes con mayor volumen de compras
query2 = """
SELECT c.customer_id, SUM(f.quantity * f.price) AS total_compras
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_id
ORDER BY total_compras DESC;
"""
clientes_totales = pd.read_sql(query2, engine)

# Redondear totales para evitar problemas de decimales
clientes_totales['total_compras'] = clientes_totales['total_compras'].round(2)

# Contar la cantidad de clientes por cada total
resumen = clientes_totales.groupby('total_compras').size().reset_index(name='num_clientes')

# Calcular porcentaje
resumen['porcentaje'] = (resumen['num_clientes'] / resumen['num_clientes'].sum()) * 100

# Ordenar de mayor a menor
resumen = resumen.sort_values(by='num_clientes', ascending=False)

# Gráfico de barras más compacto
plt.figure(figsize=(14,5))
sns.barplot(data=resumen, x='total_compras', y='porcentaje', palette="viridis")

plt.title("Distribución de Clientes por Volumen de Compras", fontsize=16)
plt.xlabel("Total de Compras (TL)", fontsize=12)
plt.ylabel("Porcentaje de Clientes (%)", fontsize=12)
plt.xticks(rotation=45, ha="right")

# Mostrar valores encima de cada barra (con decimales más pequeños)
for index, row in resumen.iterrows():
    plt.text(index, row.porcentaje + 0.05, f"{row.porcentaje:.2f}%", ha='center', fontsize=6)

plt.ylim(0, resumen['porcentaje'].max() + 1)  # ajustar límite superior para mejor visualización
plt.tight_layout()
plt.show()


# 3. Métodos de pago más utilizados
query3 = """
SELECT pm.payment_method, COUNT(*) AS cantidad_transacciones
FROM fact_sales f
JOIN dim_payment pm ON f.payment_key = pm.payment_key
GROUP BY pm.payment_method;
"""
metodos_pago = pd.read_sql(query3, engine)

plt.figure(figsize=(7,7))
plt.pie(metodos_pago["cantidad_transacciones"], labels=metodos_pago["payment_method"],
        autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
plt.title("Distribución de métodos de pago")
plt.show()


# 4. Comparación de ventas por mes
query4 = """
SELECT DATE_TRUNC('month', d.invoice_date)::date AS mes,
       SUM(f.quantity * f.price) AS total_ventas
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY mes
ORDER BY mes;
"""
ventas_mes = pd.read_sql(query4, engine)

# Convertir columna 'mes' a datetime
ventas_mes['mes'] = pd.to_datetime(ventas_mes['mes'])

# Convertir ventas a millones
ventas_mes['total_ventas_millones'] = ventas_mes['total_ventas'] / 1e6

plt.figure(figsize=(14,6))
sns.lineplot(data=ventas_mes, x="mes", y="total_ventas_millones", marker="o", color="royalblue")

# Mostrar solo los meses existentes en el dataset
plt.xticks(ticks=ventas_mes['mes'], labels=ventas_mes['mes'].dt.strftime('%Y-%m'), rotation=45)

plt.title("Tendencia de Ventas por Mes", fontsize=16)
plt.xlabel("Mes", fontsize=12)
plt.ylabel("Ventas (millones TL)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# Dibujar línea entrecortada desde el eje X hasta cada punto
for _, row in ventas_mes.iterrows():
    plt.vlines(x=row['mes'], ymin=0, ymax=row['total_ventas_millones'],
               colors='gray', linestyles='dashed', linewidth=0.8)

plt.tight_layout()
plt.show()
