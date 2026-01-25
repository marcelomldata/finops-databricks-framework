from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, max as spark_max, min as spark_min,
    count, datediff, desc, round
)
from typing import Dict, List, Optional
from datetime import datetime, timedelta

def estimate_cluster_savings(
    spark: SparkSession,
    workspace_name: str,
    cluster_id: str,
    action: str
) -> Dict:
    df_cluster = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("cluster_id") == cluster_id)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    if df_cluster.count() == 0:
        return {"error": "Cluster não encontrado"}
    
    cluster = df_cluster.collect()[0]
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/billing_costs_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("date_parsed")) \
        .limit(30)
    
    avg_daily_cost = df_costs.agg(avg("daily_cost_usd").alias("avg_cost")).collect()[0].avg_cost or 0.0
    
    hourly_cost_per_worker = 0.5
    
    savings = {}
    
    if action == "terminate_idle":
        idle_hours = cluster.idle_hours or 0
        num_workers = cluster.num_workers or 0
        monthly_savings = idle_hours * num_workers * hourly_cost_per_worker * 30
        savings = {
            "action": "terminate_idle",
            "current_monthly_cost": idle_hours * num_workers * hourly_cost_per_worker * 30,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 100.0,
            "confidence": "high",
            "payback_months": 0.0
        }
    
    elif action == "enable_autoscaling":
        num_workers = cluster.num_workers or 0
        current_monthly = num_workers * hourly_cost_per_worker * 24 * 30
        estimated_monthly = num_workers * 0.6 * hourly_cost_per_worker * 24 * 30
        monthly_savings = current_monthly - estimated_monthly
        savings = {
            "action": "enable_autoscaling",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": estimated_monthly,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 40.0,
            "confidence": "medium",
            "payback_months": 0.0
        }
    
    elif action == "resize_cluster":
        current_workers = cluster.num_workers or 0
        recommended_workers = max(1, int(current_workers * 0.7))
        current_monthly = current_workers * hourly_cost_per_worker * 24 * 30
        estimated_monthly = recommended_workers * hourly_cost_per_worker * 24 * 30
        monthly_savings = current_monthly - estimated_monthly
        savings = {
            "action": "resize_cluster",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": estimated_monthly,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 30.0,
            "confidence": "medium",
            "payback_months": 0.0
        }
    
    return savings

def estimate_storage_savings(
    spark: SparkSession,
    workspace_name: str,
    table_name: str,
    action: str
) -> Dict:
    df_table = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("full_table_name") == table_name)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    if df_table.count() == 0:
        return {"error": "Tabela não encontrada"}
    
    table = df_table.collect()[0]
    
    storage_cost_per_gb_month = 0.023
    
    savings = {}
    
    if action == "archive_abandoned":
        size_gb = table.size_gb or 0.0
        current_monthly = size_gb * storage_cost_per_gb_month
        archived_monthly = size_gb * storage_cost_per_gb_month * 0.3
        monthly_savings = current_monthly - archived_monthly
        savings = {
            "action": "archive_abandoned",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": archived_monthly,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 70.0,
            "confidence": "high",
            "payback_months": 0.0
        }
    
    elif action == "delete_abandoned":
        size_gb = table.size_gb or 0.0
        current_monthly = size_gb * storage_cost_per_gb_month
        savings = {
            "action": "delete_abandoned",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": 0.0,
            "estimated_monthly_savings": current_monthly,
            "estimated_annual_savings": current_monthly * 12,
            "reduction_percentage": 100.0,
            "confidence": "high",
            "payback_months": 0.0
        }
    
    elif action == "optimize_small_files":
        size_gb = table.size_gb or 0.0
        num_files = table.num_files or 0
        current_monthly = size_gb * storage_cost_per_gb_month
        estimated_reduction = num_files * 0.3
        estimated_size_gb = size_gb * 0.9
        estimated_monthly = estimated_size_gb * storage_cost_per_gb_month
        monthly_savings = current_monthly - estimated_monthly
        savings = {
            "action": "optimize_small_files",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": estimated_monthly,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 10.0,
            "confidence": "medium",
            "payback_months": 0.0,
            "performance_improvement": "30-50% em queries"
        }
    
    return savings

def estimate_job_optimization_savings(
    spark: SparkSession,
    workspace_name: str,
    job_id: int,
    action: str
) -> Dict:
    df_job = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("job_id") == job_id)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    if df_job.count() == 0:
        return {"error": "Job não encontrado"}
    
    job = df_job.collect()[0]
    
    hourly_cost_per_run = 2.0
    
    savings = {}
    
    if action == "fix_failures":
        failed_runs = job.failed_runs or 0
        avg_duration = job.avg_duration_hours or 0.0
        current_monthly_waste = failed_runs * avg_duration * hourly_cost_per_run
        estimated_reduction = failed_runs * 0.8
        estimated_monthly_waste = estimated_reduction * avg_duration * hourly_cost_per_run
        monthly_savings = current_monthly_waste - estimated_monthly_waste
        savings = {
            "action": "fix_failures",
            "current_monthly_waste": current_monthly_waste,
            "estimated_monthly_waste": estimated_monthly_waste,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 80.0,
            "confidence": "high",
            "payback_months": 0.0
        }
    
    elif action == "optimize_long_runs":
        avg_duration = job.avg_duration_hours or 0.0
        total_runs = job.total_runs or 0
        current_monthly = total_runs * avg_duration * hourly_cost_per_run
        estimated_duration = avg_duration * 0.7
        estimated_monthly = total_runs * estimated_duration * hourly_cost_per_run
        monthly_savings = current_monthly - estimated_monthly
        savings = {
            "action": "optimize_long_runs",
            "current_monthly_cost": current_monthly,
            "estimated_monthly_cost": estimated_monthly,
            "estimated_monthly_savings": monthly_savings,
            "estimated_annual_savings": monthly_savings * 12,
            "reduction_percentage": 30.0,
            "confidence": "medium",
            "payback_months": 0.0
        }
    
    return savings

def calculate_total_roi(
    spark: SparkSession,
    workspace_name: str,
    recommendations: List[Dict]
) -> Dict:
    total_current_monthly = 0.0
    total_estimated_monthly = 0.0
    total_monthly_savings = 0.0
    
    for rec in recommendations:
        category = rec.get("category")
        resource_id = rec.get("resource_id")
        action = rec.get("recommended_action", "")
        
        if category == "compute" and resource_id:
            savings = estimate_cluster_savings(spark, workspace_name, resource_id, "terminate_idle")
            if "estimated_monthly_savings" in savings:
                total_current_monthly += savings.get("current_monthly_cost", 0.0)
                total_estimated_monthly += savings.get("estimated_monthly_cost", savings.get("current_monthly_cost", 0.0))
                total_monthly_savings += savings.get("estimated_monthly_savings", 0.0)
        
        elif category == "storage" and resource_id:
            savings = estimate_storage_savings(spark, workspace_name, resource_id, "archive_abandoned")
            if "estimated_monthly_savings" in savings:
                total_current_monthly += savings.get("current_monthly_cost", 0.0)
                total_estimated_monthly += savings.get("estimated_monthly_cost", savings.get("current_monthly_cost", 0.0))
                total_monthly_savings += savings.get("estimated_monthly_savings", 0.0)
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/billing_costs_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("date_parsed")) \
        .limit(30)
    
    current_monthly_cost = df_costs.agg(avg("daily_cost_usd").alias("avg_cost")).collect()[0].avg_cost or 0.0
    current_monthly_cost = current_monthly_cost * 30
    
    total_annual_savings = total_monthly_savings * 12
    reduction_percentage = (total_monthly_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0.0
    
    return {
        "workspace_name": workspace_name,
        "current_monthly_cost": round(current_monthly_cost, 2),
        "estimated_monthly_cost": round(current_monthly_cost - total_monthly_savings, 2),
        "estimated_monthly_savings": round(total_monthly_savings, 2),
        "estimated_annual_savings": round(total_annual_savings, 2),
        "reduction_percentage": round(reduction_percentage, 2),
        "confidence": "medium",
        "margin_of_error": "±15%",
        "calculation_timestamp": datetime.utcnow()
    }
