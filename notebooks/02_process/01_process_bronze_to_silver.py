from pyspark.sql import SparkSession
from src.processors.bronze_to_silver import (
    process_compute_silver,
    process_storage_silver,
    process_billing_silver
)

spark = SparkSession.builder.appName("FinOps_Process_Bronze_To_Silver").getOrCreate()

print("Processando camada Bronze para Silver...")

process_compute_silver(spark)
print("Compute processado")

process_storage_silver(spark)
print("Storage processado")

process_billing_silver(spark)
print("Billing processado")

print("Processamento Bronze -> Silver concluído")
