from pyspark.sql import SparkSession
from src.processors.silver_to_gold import (
    process_compute_gold,
    process_storage_gold,
    process_billing_gold
)

spark = SparkSession.builder.appName("FinOps_Process_Silver_To_Gold").getOrCreate()

print("Processando camada Silver para Gold...")

process_compute_gold(spark)
print("Compute processado")

process_storage_gold(spark)
print("Storage processado")

process_billing_gold(spark)
print("Billing processado")

print("Processamento Silver -> Gold concluído")
