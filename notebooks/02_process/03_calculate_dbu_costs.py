from pyspark.sql import SparkSession
from src.analyzers.cost_estimator import estimate_cluster_dbu_cost
from src.utils.cloud_detector import detect_cloud_from_url
import os

spark = SparkSession.builder.appName("FinOps_Calculate_DBU_Costs").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
workspace_url = os.getenv("WORKSPACE_URL")

if not workspace_url:
    raise ValueError("WORKSPACE_URL é obrigatório")

cloud = detect_cloud_from_url(workspace_url)

print(f"Calculando custos DBU para {workspace_name} ({cloud})...")

estimate_cluster_dbu_cost(spark, workspace_name, cloud)

print("Cálculo de custos DBU concluído")
