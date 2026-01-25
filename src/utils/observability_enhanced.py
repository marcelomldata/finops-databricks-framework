from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, count, countDistinct,
    collect_list, struct, current_timestamp, desc
)
from typing import Dict, List
from datetime import datetime, timedelta

def analyze_job_failures(
    spark: SparkSession,
    workspace_name: str,
    days_back: int = 30
) -> List[Dict]:
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(
            (col("workspace_name") == workspace_name) &
            (col("start_time") >= int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)) &
            (col("is_failed") == True)
        )
    
    failure_patterns = []
    
    failed_runs = df_runs.collect()
    
    error_messages = {}
    for run in failed_runs:
        if hasattr(run, 'error') and run.error and run.error != "null":
            error_key = str(run.error)[:100]
            error_messages[error_key] = error_messages.get(error_key, 0) + 1
    
    top_errors = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]
    
    for error_pattern, count in top_errors:
        failure_patterns.append({
            "workspace_name": workspace_name,
            "error_pattern": error_pattern,
            "occurrence_count": count,
            "severity": "high" if count > 10 else "medium" if count > 5 else "low",
            "recommendation": "Investigar causa raiz e implementar correção",
            "analysis_date": datetime.utcnow()
        })
    
    return failure_patterns

def analyze_performance_by_stage(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_runs.count() == 0:
        return {}
    
    performance_metrics = df_runs.agg(
        avg("setup_duration").alias("avg_setup_duration"),
        avg("execution_duration").alias("avg_execution_duration"),
        avg("cleanup_duration").alias("avg_cleanup_duration"),
        avg("duration_hours").alias("avg_total_duration")
    ).collect()[0]
    
    total_avg = performance_metrics.avg_total_duration or 0.0
    
    return {
        "workspace_name": workspace_name,
        "setup_percentage": (performance_metrics.avg_setup_duration or 0) / (total_avg * 3600000) * 100 if total_avg > 0 else 0,
        "execution_percentage": (performance_metrics.avg_execution_duration or 0) / (total_avg * 3600000) * 100 if total_avg > 0 else 0,
        "cleanup_percentage": (performance_metrics.avg_cleanup_duration or 0) / (total_avg * 3600000) * 100 if total_avg > 0 else 0,
        "bottleneck": "setup" if (performance_metrics.avg_setup_duration or 0) > (performance_metrics.avg_execution_duration or 0) else "execution",
        "analysis_date": datetime.utcnow()
    }

def link_cost_performance_failure(
    spark: SparkSession,
    workspace_name: str
) -> List[Dict]:
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    linkages = []
    
    for job in df_jobs.filter(col("failure_rate") > 0.1).collect():
        cost_per_run = 2.0
        total_failures = job.failed_runs or 0
        waste_cost = total_failures * cost_per_run
        
        linkages.append({
            "workspace_name": workspace_name,
            "job_id": job.job_id,
            "job_name": job.job_name,
            "failure_rate": job.failure_rate,
            "waste_cost_monthly": waste_cost,
            "performance_impact": "high" if job.failure_rate > 0.3 else "medium",
            "cost_impact": "high" if waste_cost > 100 else "medium" if waste_cost > 50 else "low",
            "recommendation": f"Corrigir falhas pode economizar ${waste_cost:.2f}/mês e melhorar SLA",
            "analysis_date": datetime.utcnow()
        })
    
    return linkages
