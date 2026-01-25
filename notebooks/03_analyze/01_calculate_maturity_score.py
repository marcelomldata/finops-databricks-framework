from pyspark.sql import SparkSession
from src.analyzers.finops_analyzer import calculate_maturity_score
import os
import yaml

spark = SparkSession.builder.appName("FinOps_Calculate_Maturity_Score").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")

config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

weights = config.get("analysis", {}).get("maturity_score", {}).get("weights", {
    "compute": 0.25,
    "storage": 0.25,
    "governance": 0.20,
    "pipelines": 0.15,
    "observability": 0.10,
    "costs": 0.05
})

maturity_result = calculate_maturity_score(spark, workspace_name, weights)

df_result = spark.createDataFrame([maturity_result])

df_result.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .save("dbfs:/finops/gold/maturity_scores")

print(f"Maturity Score calculado para {workspace_name}:")
print(f"  Score: {maturity_result['maturity_score']}")
print(f"  Nível: {maturity_result['maturity_level']}")
print(f"  Compute: {maturity_result['compute_score']}")
print(f"  Storage: {maturity_result['storage_score']}")
print(f"  Governance: {maturity_result['governance_score']}")
print(f"  Pipelines: {maturity_result['pipelines_score']}")
print(f"  Observability: {maturity_result['observability_score']}")
print(f"  Costs: {maturity_result['costs_score']}")
