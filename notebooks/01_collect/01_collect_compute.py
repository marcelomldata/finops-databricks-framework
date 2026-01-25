from pyspark.sql import SparkSession
from src.utils.databricks_client import DatabricksConfig
from src.collectors.compute_collector import collect_clusters_metrics, collect_jobs_metrics
import os

spark = SparkSession.builder.appName("FinOps_Collect_Compute").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
workspace_url = os.getenv("WORKSPACE_URL")
databricks_token = os.getenv("DATABRICKS_TOKEN")

if not workspace_url or not databricks_token:
    raise ValueError("WORKSPACE_URL e DATABRICKS_TOKEN são obrigatórios")

databricks_config = DatabricksConfig(
    host=workspace_url,
    token=databricks_token
)

collect_clusters_metrics(
    spark=spark,
    databricks_config=databricks_config,
    workspace_name=workspace_name,
    workspace_url=workspace_url
)

collect_jobs_metrics(
    spark=spark,
    databricks_config=databricks_config,
    workspace_name=workspace_name,
    workspace_url=workspace_url,
    days_back=30
)

print(f"Coleta de métricas de compute concluída para {workspace_name}")
