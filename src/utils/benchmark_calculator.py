from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, avg, count, sum as spark_sum
from typing import Dict, Optional
from datetime import datetime

BENCHMARK_METRICS = {
    "cost_per_tb": {
        "excellent": 50.0,
        "good": 100.0,
        "average": 200.0,
        "poor": 400.0
    },
    "cluster_utilization": {
        "excellent": 0.8,
        "good": 0.6,
        "average": 0.4,
        "poor": 0.2
    },
    "job_success_rate": {
        "excellent": 0.98,
        "good": 0.95,
        "average": 0.90,
        "poor": 0.80
    },
    "storage_cold_data_percentage": {
        "excellent": 0.10,
        "good": 0.20,
        "average": 0.30,
        "poor": 0.50
    }
}

def calculate_cost_per_tb(
    spark: SparkSession,
    workspace_name: str
) -> float:
    df_storage = spark.read.format("delta").load("dbfs:/finops/gold/storage_workspace_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs_dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_storage.count() == 0 or df_costs.count() == 0:
        return 0.0
    
    storage_summary = df_storage.collect()[0]
    total_storage_tb = storage_summary.total_size_tb or 0.0
    
    total_monthly_cost = df_costs.agg({"estimated_monthly_cost": "sum"}).collect()[0][0] or 0.0
    
    if total_storage_tb == 0:
        return 0.0
    
    return total_monthly_cost / total_storage_tb

def benchmark_workspace(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    cost_per_tb = calculate_cost_per_tb(spark, workspace_name)
    
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_storage = spark.read.format("delta").load("dbfs:/finops/gold/storage_workspace_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    avg_utilization = 0.0
    if df_clusters.count() > 0:
        avg_utilization = df_clusters.agg({"utilization_score": "avg"}).collect()[0][0] or 0.0
    
    avg_success_rate = 0.0
    if df_jobs.count() > 0:
        avg_success_rate = df_jobs.agg({"success_rate": "avg"}).collect()[0][0] or 0.0
    
    cold_data_pct = 0.0
    if df_storage.count() > 0:
        storage_summary = df_storage.collect()[0]
        total_tb = storage_summary.total_size_tb or 1.0
        cold_tb = storage_summary.cold_size_tb or 0.0
        cold_data_pct = cold_tb / total_tb if total_tb > 0 else 0.0
    
    benchmarks = BENCHMARK_METRICS
    
    def get_benchmark_level(value: float, metric: str, reverse: bool = False) -> str:
        thresholds = benchmarks[metric]
        if reverse:
            if value <= thresholds["excellent"]:
                return "excellent"
            elif value <= thresholds["good"]:
                return "good"
            elif value <= thresholds["average"]:
                return "average"
            else:
                return "poor"
        else:
            if value >= thresholds["excellent"]:
                return "excellent"
            elif value >= thresholds["good"]:
                return "good"
            elif value >= thresholds["average"]:
                return "average"
            else:
                return "poor"
    
    cost_per_tb_level = get_benchmark_level(cost_per_tb, "cost_per_tb", reverse=True)
    utilization_level = get_benchmark_level(avg_utilization, "cluster_utilization")
    success_rate_level = get_benchmark_level(avg_success_rate, "job_success_rate")
    cold_data_level = get_benchmark_level(cold_data_pct, "storage_cold_data_percentage", reverse=True)
    
    overall_score = {
        "excellent": 4,
        "good": 3,
        "average": 2,
        "poor": 1
    }
    
    total_score = (
        overall_score.get(cost_per_tb_level, 2) +
        overall_score.get(utilization_level, 2) +
        overall_score.get(success_rate_level, 2) +
        overall_score.get(cold_data_level, 2)
    ) / 4
    
    if total_score >= 3.5:
        overall_level = "excellent"
    elif total_score >= 2.5:
        overall_level = "good"
    elif total_score >= 1.5:
        overall_level = "average"
    else:
        overall_level = "poor"
    
    return {
        "workspace_name": workspace_name,
        "benchmark_date": datetime.utcnow().isoformat(),
        "metrics": {
            "cost_per_tb": {
                "value": round(cost_per_tb, 2),
                "level": cost_per_tb_level,
                "benchmark": {
                    "excellent": benchmarks["cost_per_tb"]["excellent"],
                    "good": benchmarks["cost_per_tb"]["good"],
                    "average": benchmarks["cost_per_tb"]["average"]
                }
            },
            "cluster_utilization": {
                "value": round(avg_utilization, 2),
                "level": utilization_level,
                "benchmark": {
                    "excellent": benchmarks["cluster_utilization"]["excellent"],
                    "good": benchmarks["cluster_utilization"]["good"],
                    "average": benchmarks["cluster_utilization"]["average"]
                }
            },
            "job_success_rate": {
                "value": round(avg_success_rate, 2),
                "level": success_rate_level,
                "benchmark": {
                    "excellent": benchmarks["job_success_rate"]["excellent"],
                    "good": benchmarks["job_success_rate"]["good"],
                    "average": benchmarks["job_success_rate"]["average"]
                }
            },
            "cold_data_percentage": {
                "value": round(cold_data_pct * 100, 2),
                "level": cold_data_level,
                "benchmark": {
                    "excellent": benchmarks["storage_cold_data_percentage"]["excellent"] * 100,
                    "good": benchmarks["storage_cold_data_percentage"]["good"] * 100,
                    "average": benchmarks["storage_cold_data_percentage"]["average"] * 100
                }
            }
        },
        "overall_benchmark": {
            "score": round(total_score, 2),
            "level": overall_level,
            "interpretation": f"Workspace está {overall_level} comparado a benchmarks da indústria"
        }
    }
