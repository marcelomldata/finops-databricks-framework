from pyspark.sql import SparkSession
from src.collectors.storage_collector import collect_storage_metrics
import os

spark = SparkSession.builder.appName("FinOps_Collect_Storage").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
workspace_url = os.getenv("WORKSPACE_URL")

if not workspace_url:
    raise ValueError("WORKSPACE_URL é obrigatório")

collect_storage_metrics(
    spark=spark,
    workspace_name=workspace_name,
    workspace_url=workspace_url
)

print(f"Coleta de métricas de storage concluída para {workspace_name}")
