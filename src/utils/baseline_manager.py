from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, max as spark_max
from typing import Dict, Optional
from datetime import datetime
import uuid

def create_baseline(
    spark: SparkSession,
    workspace_name: str,
    cloud: str,
    framework_version: str = "1.0.0",
    context: Optional[Dict] = None
) -> str:
    from src.analyzers.finops_analyzer import calculate_maturity_score
    from src.analyzers.cost_estimator import calculate_workspace_dbu_cost
    
    baseline_id = f"{workspace_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    baseline_date = datetime.utcnow().date()
    
    maturity = calculate_maturity_score(spark, workspace_name)
    costs = calculate_workspace_dbu_cost(spark, workspace_name)
    
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage_workspace_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    total_clusters = df_clusters.count()
    total_jobs = df_jobs.count()
    
    total_tables = 0
    total_storage_tb = 0.0
    if df_tables.count() > 0:
        table_summary = df_tables.collect()[0]
        total_tables = table_summary.total_tables or 0
        total_storage_tb = table_summary.total_size_tb or 0.0
    
    baseline_data = {
        "baseline_id": baseline_id,
        "workspace_name": workspace_name,
        "baseline_date": baseline_date,
        "cloud": cloud,
        "framework_version": framework_version,
        "maturity_score": maturity.get("maturity_score", 0.0),
        "maturity_level": maturity.get("maturity_level", "Básico"),
        "compute_score": maturity.get("compute_score", 0.0),
        "storage_score": maturity.get("storage_score", 0.0),
        "governance_score": maturity.get("governance_score", 0.0),
        "pipelines_score": maturity.get("pipelines_score", 0.0),
        "observability_score": maturity.get("observability_score", 0.0),
        "costs_score": maturity.get("costs_score", 0.0),
        "estimated_monthly_cost": costs.get("total_estimated_monthly_cost", 0.0),
        "estimated_annual_cost": costs.get("total_estimated_monthly_cost", 0.0) * 12,
        "total_clusters": total_clusters,
        "total_jobs": total_jobs,
        "total_tables": total_tables,
        "total_storage_tb": total_storage_tb,
        "context": {
            "num_workspaces": 1,
            "primary_use_case": context.get("primary_use_case", "") if context else "",
            "team_size": context.get("team_size", 0) if context else 0,
            "notes": context.get("notes", "") if context else ""
        },
        "process_timestamp": datetime.utcnow()
    }
    
    df_baseline = spark.createDataFrame([baseline_data])
    
    df_baseline.write \
        .format("delta") \
        .mode("append") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/assessment_baselines")
    
    return baseline_id

def get_latest_baseline(
    spark: SparkSession,
    workspace_name: str
) -> Optional[Dict]:
    df_baseline = spark.read.format("delta").load("dbfs:/finops/gold/assessment_baselines") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(col("baseline_date").desc()) \
        .limit(1)
    
    if df_baseline.count() == 0:
        return None
    
    baseline = df_baseline.collect()[0]
    
    return {
        "baseline_id": baseline.baseline_id,
        "baseline_date": baseline.baseline_date,
        "maturity_score": baseline.maturity_score,
        "estimated_monthly_cost": baseline.estimated_monthly_cost,
        "total_clusters": baseline.total_clusters,
        "total_jobs": baseline.total_jobs
    }

def compare_baselines(
    spark: SparkSession,
    workspace_name: str,
    baseline_id_1: str,
    baseline_id_2: str
) -> Dict:
    df_baselines = spark.read.format("delta").load("dbfs:/finops/gold/assessment_baselines") \
        .filter(
            (col("workspace_name") == workspace_name) &
            (col("baseline_id").isin([baseline_id_1, baseline_id_2]))
        )
    
    baselines = {row.baseline_id: row for row in df_baselines.collect()}
    
    if len(baselines) != 2:
        return {"error": "Baselines não encontrados"}
    
    b1 = baselines[baseline_id_1]
    b2 = baselines[baseline_id_2]
    
    return {
        "baseline_1": {
            "baseline_id": b1.baseline_id,
            "date": b1.baseline_date,
            "maturity_score": b1.maturity_score,
            "estimated_monthly_cost": b1.estimated_monthly_cost
        },
        "baseline_2": {
            "baseline_id": b2.baseline_id,
            "date": b2.baseline_date,
            "maturity_score": b2.maturity_score,
            "estimated_monthly_cost": b2.estimated_monthly_cost
        },
        "improvements": {
            "maturity_score_delta": b2.maturity_score - b1.maturity_score,
            "cost_reduction": b1.estimated_monthly_cost - b2.estimated_monthly_cost,
            "cost_reduction_percentage": ((b1.estimated_monthly_cost - b2.estimated_monthly_cost) / b1.estimated_monthly_cost * 100) if b1.estimated_monthly_cost > 0 else 0.0
        }
    }
