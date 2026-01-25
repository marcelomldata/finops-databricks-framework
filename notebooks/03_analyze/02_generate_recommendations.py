from pyspark.sql import SparkSession
from src.analyzers.finops_analyzer import generate_recommendations
import os

spark = SparkSession.builder.appName("FinOps_Generate_Recommendations").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")

recommendations = generate_recommendations(spark, workspace_name)

if recommendations:
    df_recommendations = spark.createDataFrame(recommendations)
    
    df_recommendations.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/recommendations")
    
    print(f"Geradas {len(recommendations)} recomendações para {workspace_name}")
    
    high_priority = [r for r in recommendations if r["priority"] == "high"]
    medium_priority = [r for r in recommendations if r["priority"] == "medium"]
    low_priority = [r for r in recommendations if r["priority"] == "low"]
    
    print(f"  Alta prioridade: {len(high_priority)}")
    print(f"  Média prioridade: {len(medium_priority)}")
    print(f"  Baixa prioridade: {len(low_priority)}")
else:
    print(f"Nenhuma recomendação gerada para {workspace_name}")
