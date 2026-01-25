from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, round, current_timestamp
)
from typing import Dict, Optional
from datetime import datetime

DBU_RATES = {
    "azure": {
        "standard": {
            "compute": 0.15,
            "all_purpose": 0.55,
            "jobs": 0.15,
            "sql_compute": 0.22,
            "sql_serverless": 0.70
        }
    },
    "aws": {
        "standard": {
            "compute": 0.15,
            "all_purpose": 0.55,
            "jobs": 0.15,
            "sql_compute": 0.22,
            "sql_serverless": 0.70
        }
    },
    "gcp": {
        "standard": {
            "compute": 0.15,
            "all_purpose": 0.55,
            "jobs": 0.15,
            "sql_compute": 0.22,
            "sql_serverless": 0.70
        }
    }
}

def estimate_cluster_dbu_cost(
    spark: SparkSession,
    workspace_name: str,
    cloud: str
) -> None:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/silver/compute/clusters") \
        .filter((col("workspace_name") == workspace_name) & (col("cloud") == cloud))
    
    rates = DBU_RATES.get(cloud, DBU_RATES["azure"])
    standard_rates = rates["standard"]
    
    df_costs = df_clusters \
        .withColumn("cluster_type",
            when(col("cluster_source") == "UI", "all_purpose")
            .when(col("cluster_source") == "JOB", "jobs")
            .otherwise("compute")) \
        .withColumn("dbu_rate",
            when(col("cluster_type") == "all_purpose", standard_rates["all_purpose"])
            .when(col("cluster_type") == "jobs", standard_rates["jobs"])
            .otherwise(standard_rates["compute"])) \
        .withColumn("dbu_per_hour",
            when(col("num_workers") > 0, 
                (col("num_workers") + 1) * col("dbu_rate"))
            .otherwise(col("dbu_rate"))) \
        .withColumn("estimated_dbu_cost",
            when(col("uptime_hours").isNotNull(),
                col("uptime_hours") * col("dbu_per_hour"))
            .when(col("is_running"),
                (current_timestamp().cast("long") - col("start_time") / 1000) / 3600 * col("dbu_per_hour"))
            .otherwise(lit(0.0))) \
        .withColumn("estimated_monthly_cost",
            col("estimated_dbu_cost") * 30 / 
            when(col("uptime_hours") > 0, col("uptime_hours")).otherwise(1)) \
        .select(
            "workspace_name",
            "cloud",
            "cluster_id",
            "cluster_name",
            "cluster_type",
            "num_workers",
            "uptime_hours",
            "dbu_rate",
            "dbu_per_hour",
            "estimated_dbu_cost",
            "estimated_monthly_cost",
            current_timestamp().alias("process_timestamp")
        )
    
    df_costs.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/costs/dbu_estimates")

def calculate_workspace_dbu_cost(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_costs.count() == 0:
        return {
            "workspace_name": workspace_name,
            "total_estimated_dbu_cost": 0.0,
            "total_estimated_monthly_cost": 0.0,
            "clusters_count": 0,
            "process_timestamp": datetime.utcnow()
        }
    
    summary = df_costs.agg(
        spark_sum("estimated_dbu_cost").alias("total_dbu_cost"),
        spark_sum("estimated_monthly_cost").alias("total_monthly_cost"),
        spark_sum(when(col("is_running"), 1).otherwise(0)).alias("running_clusters"),
        spark_sum("num_workers").alias("total_workers")
    ).collect()[0]
    
    return {
        "workspace_name": workspace_name,
        "total_estimated_dbu_cost": round(summary.total_dbu_cost or 0.0, 2),
        "total_estimated_monthly_cost": round(summary.total_monthly_cost or 0.0, 2),
        "running_clusters": summary.running_clusters or 0,
        "total_workers": summary.total_workers or 0,
        "process_timestamp": datetime.utcnow()
    }

def update_costs_score_with_dbu(
    spark: SparkSession,
    workspace_name: str,
    baseline_monthly_cost: Optional[float] = None
) -> float:
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_costs.count() == 0:
        return 0.5
    
    current_monthly = df_costs.agg(avg("estimated_monthly_cost").alias("avg_monthly")).collect()[0].avg_monthly or 0.0
    
    if baseline_monthly_cost is None:
        try:
            df_baseline = spark.read.format("delta").load("dbfs:/finops/gold/assessment_baselines") \
                .filter(col("workspace_name") == workspace_name) \
                .orderBy(col("baseline_date").desc()) \
                .limit(1)
            
            if df_baseline.count() > 0:
                baseline_monthly_cost = df_baseline.collect()[0].estimated_monthly_cost or current_monthly
            else:
                baseline_monthly_cost = current_monthly
        except Exception:
            baseline_monthly_cost = current_monthly
    
    if baseline_monthly_cost == 0:
        return 0.5
    
    cost_change_ratio = (current_monthly - baseline_monthly_cost) / baseline_monthly_cost
    
    if cost_change_ratio < -0.1:
        return 1.0
    elif cost_change_ratio < 0:
        return 0.7
    elif cost_change_ratio < 0.1:
        return 0.5
    else:
        return 0.3
