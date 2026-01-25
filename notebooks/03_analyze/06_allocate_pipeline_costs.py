from pyspark.sql import SparkSession
from src.utils.pipeline_cost_allocation import allocate_cost_by_pipeline
import os

spark = SparkSession.builder.appName("FinOps_Allocate_Pipeline_Costs").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")

print(f"Alocando custos por pipeline para {workspace_name}...")

allocate_cost_by_pipeline(spark, workspace_name)

print("Alocação de custos por pipeline concluída")
print("Consulte em: SELECT * FROM finops_gold.cost_allocation_pipelines")
