from pyspark.sql import SparkSession
from src.utils.benchmark_calculator import benchmark_workspace
import os

spark = SparkSession.builder.appName("FinOps_Calculate_Benchmarks").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")

print(f"Calculando benchmarks para {workspace_name}...")

benchmark_result = benchmark_workspace(spark, workspace_name)

df_benchmark = spark.createDataFrame([{
    "workspace_name": workspace_name,
    "benchmark_date": benchmark_result["benchmark_date"],
    "cost_per_tb": benchmark_result["metrics"]["cost_per_tb"]["value"],
    "cost_per_tb_level": benchmark_result["metrics"]["cost_per_tb"]["level"],
    "cluster_utilization": benchmark_result["metrics"]["cluster_utilization"]["value"],
    "utilization_level": benchmark_result["metrics"]["cluster_utilization"]["level"],
    "job_success_rate": benchmark_result["metrics"]["job_success_rate"]["value"],
    "success_rate_level": benchmark_result["metrics"]["job_success_rate"]["level"],
    "cold_data_percentage": benchmark_result["metrics"]["cold_data_percentage"]["value"],
    "cold_data_level": benchmark_result["metrics"]["cold_data_percentage"]["level"],
    "overall_score": benchmark_result["overall_benchmark"]["score"],
    "overall_level": benchmark_result["overall_benchmark"]["level"],
    "process_timestamp": benchmark_result["benchmark_date"]
}])

df_benchmark.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .save("dbfs:/finops/gold/benchmarks")

print(f"\n=== BENCHMARK RESULTADO ===")
print(f"Nível Geral: {benchmark_result['overall_benchmark']['level']}")
print(f"Score: {benchmark_result['overall_benchmark']['score']:.2f}")
print(f"\nMétricas:")
print(f"  Custo por TB: ${benchmark_result['metrics']['cost_per_tb']['value']:.2f} ({benchmark_result['metrics']['cost_per_tb']['level']})")
print(f"  Utilização: {benchmark_result['metrics']['cluster_utilization']['value']:.2%} ({benchmark_result['metrics']['cluster_utilization']['level']})")
print(f"  Taxa de Sucesso: {benchmark_result['metrics']['job_success_rate']['value']:.2%} ({benchmark_result['metrics']['job_success_rate']['level']})")
print(f"  Dados Frios: {benchmark_result['metrics']['cold_data_percentage']['value']:.1f}% ({benchmark_result['metrics']['cold_data_percentage']['level']})")
