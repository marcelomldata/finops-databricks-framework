from pyspark.sql import SparkSession
from src.utils.billing_reconciler import reconcile_dbu_vs_actual
import os

spark = SparkSession.builder.appName("FinOps_Reconcile_Billing").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
actual_cost = os.getenv("ACTUAL_COST")
actual_cost_date = os.getenv("ACTUAL_COST_DATE")

print(f"Reconciliando billing para {workspace_name}...")

reconciliation = reconcile_dbu_vs_actual(
    spark,
    workspace_name,
    float(actual_cost) if actual_cost else None,
    actual_cost_date
)

df_reconciliation = spark.createDataFrame([reconciliation])
df_reconciliation.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .save("dbfs:/finops/gold/billing_reconciliation")

print(f"\n=== RECONCILIAÇÃO DE BILLING ===")
print(f"Status: {reconciliation['reconciliation_status']}")
print(f"Confiança: {reconciliation['confidence']}")
if reconciliation.get('actual_cost'):
    print(f"Custo Estimado: ${reconciliation['estimated_monthly_cost']:.2f}")
    print(f"Custo Real: ${reconciliation['actual_cost']:.2f}")
    print(f"Variação: {reconciliation['variance_percentage']:.2f}%")
print(f"Recomendação: {reconciliation.get('recommendation', 'N/A')}")
