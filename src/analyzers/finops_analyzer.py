from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, max as spark_max,
    count, struct, current_timestamp, round, concat_ws, desc
)
from typing import Dict, List
from datetime import datetime

def calculate_compute_score(spark: SparkSession, workspace_name: str) -> float:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_clusters.count() == 0:
        return 0.0
    
    cluster_metrics = df_clusters.agg(
        avg("utilization_score").alias("avg_utilization"),
        spark_sum(when(col("is_idle"), 1).otherwise(0)).alias("idle_count"),
        count("*").alias("total_clusters"),
        spark_sum(when(col("has_autoscaling"), 1).otherwise(0)).alias("autoscaling_count")
    ).collect()[0]
    
    job_metrics = df_jobs.agg(
        avg("success_rate").alias("avg_success_rate"),
        avg("efficiency_score").alias("avg_efficiency")
    ).collect()[0] if df_jobs.count() > 0 else None
    
    total_clusters = cluster_metrics.total_clusters or 1
    idle_ratio = (cluster_metrics.idle_count or 0) / total_clusters
    autoscaling_ratio = (cluster_metrics.autoscaling_count or 0) / total_clusters
    utilization = cluster_metrics.avg_utilization or 0.0
    
    utilization_score = utilization * (1 - idle_ratio * 0.5)
    autoscaling_score = autoscaling_ratio * 0.3
    
    job_score = 0.0
    if job_metrics:
        job_score = (job_metrics.avg_success_rate or 0.0) * 0.4 + (job_metrics.avg_efficiency or 0.0) * 0.3
    
    compute_score = (utilization_score * 0.5) + (autoscaling_score * 0.2) + (job_score * 0.3)
    
    return min(max(compute_score, 0.0), 1.0)

def calculate_storage_score(spark: SparkSession, workspace_name: str) -> float:
    df_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_summary = spark.read.format("delta").load("dbfs:/finops/gold/storage/workspace_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_tables.count() == 0:
        return 0.0
    
    table_metrics = df_tables.agg(
        spark_sum(when(col("is_partitioned"), 1).otherwise(0)).alias("partitioned_count"),
        spark_sum(when(col("has_small_files"), 1).otherwise(0)).alias("small_files_count"),
        spark_sum(when(col("is_abandoned"), 1).otherwise(0)).alias("abandoned_count"),
        count("*").alias("total_tables")
    ).collect()[0]
    
    summary_metrics = df_summary.collect()[0] if df_summary.count() > 0 else None
    
    total_tables = table_metrics.total_tables or 1
    partitioned_ratio = (table_metrics.partitioned_count or 0) / total_tables
    small_files_ratio = (table_metrics.small_files_count or 0) / total_tables
    abandoned_ratio = (table_metrics.abandoned_count or 0) / total_tables
    
    partitioning_score = partitioned_ratio * 0.4
    optimization_score = (1 - small_files_ratio) * 0.3
    cleanup_score = (1 - abandoned_ratio) * 0.3
    
    storage_score = partitioning_score + optimization_score + cleanup_score
    
    return min(max(storage_score, 0.0), 1.0)

def calculate_governance_score(spark: SparkSession, workspace_name: str) -> float:
    df_tables = spark.read.format("delta").load("dbfs:/finops/silver/storage/tables") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_tables.count() == 0:
        return 0.0
    
    metastore_type = df_tables.select("metastore_type").first()
    unity_score = 0.5 if metastore_type and metastore_type.metastore_type == "unity_catalog" else 0.0
    
    return min(max(unity_score, 0.0), 1.0)

def calculate_pipelines_score(spark: SparkSession, workspace_name: str) -> float:
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_jobs.count() == 0:
        return 0.5
    
    job_metrics = df_jobs.agg(
        avg("success_rate").alias("avg_success_rate"),
        avg("efficiency_score").alias("avg_efficiency"),
        spark_sum(when(col("has_schedule"), 1).otherwise(0)).alias("scheduled_count"),
        count("*").alias("total_jobs")
    ).collect()[0]
    
    total_jobs = job_metrics.total_jobs or 1
    scheduled_ratio = (job_metrics.scheduled_count or 0) / total_jobs
    success_score = job_metrics.avg_success_rate or 0.0
    efficiency_score = job_metrics.avg_efficiency or 0.0
    
    pipelines_score = (scheduled_ratio * 0.3) + (success_score * 0.4) + (efficiency_score * 0.3)
    
    return min(max(pipelines_score, 0.0), 1.0)

def calculate_observability_score(spark: SparkSession, workspace_name: str) -> float:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/silver/compute/clusters") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/silver/compute/jobs") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_clusters.count() == 0:
        return 0.0
    
    cluster_has_tags = df_clusters.filter(col("custom_tags") != "null").count()
    job_has_tags = df_jobs.filter(col("tags") != "null").count()
    
    total_clusters = df_clusters.count()
    total_jobs = df_jobs.count() if df_jobs.count() > 0 else 1
    
    tagging_score = ((cluster_has_tags / total_clusters) * 0.5 + (job_has_tags / total_jobs) * 0.5) if total_jobs > 0 else (cluster_has_tags / total_clusters)
    
    return min(max(tagging_score, 0.0), 1.0)

def calculate_costs_score(spark: SparkSession, workspace_name: str) -> float:
    try:
        from src.analyzers.cost_estimator import update_costs_score_with_dbu
        return update_costs_score_with_dbu(spark, workspace_name)
    except Exception:
        try:
            df_costs = spark.read.format("delta").load("dbfs:/finops/gold/billing_costs_summary") \
                .filter(col("workspace_name") == workspace_name)
            
            if df_costs.count() == 0:
                return 0.5
            
            cost_trend = df_costs.orderBy("date_parsed").select("daily_cost_usd").collect()
            
            if len(cost_trend) < 2:
                return 0.5
            
            recent_avg = sum([row.daily_cost_usd for row in cost_trend[-7:]]) / min(len(cost_trend), 7)
            older_avg = sum([row.daily_cost_usd for row in cost_trend[:-7]]) / max(len(cost_trend) - 7, 1) if len(cost_trend) > 7 else recent_avg
            
            if older_avg == 0:
                return 0.5
            
            cost_change_ratio = (recent_avg - older_avg) / older_avg
            
            if cost_change_ratio < -0.1:
                return 1.0
            elif cost_change_ratio < 0:
                return 0.7
            elif cost_change_ratio < 0.1:
                return 0.5
            else:
                return 0.3
        except Exception:
            return 0.5

def calculate_maturity_score(spark: SparkSession, workspace_name: str, weights: Dict[str, float] = None) -> Dict:
    if weights is None:
        weights = {
            "compute": 0.25,
            "storage": 0.25,
            "governance": 0.20,
            "pipelines": 0.15,
            "observability": 0.10,
            "costs": 0.05
        }
    
    compute_score = calculate_compute_score(spark, workspace_name)
    storage_score = calculate_storage_score(spark, workspace_name)
    governance_score = calculate_governance_score(spark, workspace_name)
    pipelines_score = calculate_pipelines_score(spark, workspace_name)
    observability_score = calculate_observability_score(spark, workspace_name)
    costs_score = calculate_costs_score(spark, workspace_name)
    
    maturity_score = (
        compute_score * weights["compute"] +
        storage_score * weights["storage"] +
        governance_score * weights["governance"] +
        pipelines_score * weights["pipelines"] +
        observability_score * weights["observability"] +
        costs_score * weights["costs"]
    )
    
    if maturity_score >= 0.8:
        level = "Otimizado"
    elif maturity_score >= 0.6:
        level = "Avançado"
    elif maturity_score >= 0.4:
        level = "Intermediário"
    else:
        level = "Básico"
    
    return {
        "workspace_name": workspace_name,
        "maturity_score": round(maturity_score, 4),
        "maturity_level": level,
        "compute_score": round(compute_score, 4),
        "storage_score": round(storage_score, 4),
        "governance_score": round(governance_score, 4),
        "pipelines_score": round(pipelines_score, 4),
        "observability_score": round(observability_score, 4),
        "costs_score": round(costs_score, 4),
        "process_timestamp": current_timestamp()
    }

def generate_recommendations(spark: SparkSession, workspace_name: str) -> List[Dict]:
    recommendations = []
    process_ts = datetime.utcnow()
    
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    idle_clusters = df_clusters.filter(col("is_idle")).collect()
    for cluster in idle_clusters[:10]:
        recommendations.append({
            "workspace_name": workspace_name,
            "category": "compute",
            "priority": "high",
            "title": f"Cluster {cluster.cluster_name} está ocioso",
            "description": f"Cluster {cluster.cluster_id} está ocioso há {cluster.idle_hours:.1f} horas",
            "impact": "Alto",
            "complexity": "Baixa",
            "action": "Considerar desligar ou reduzir tamanho do cluster",
            "estimated_savings": "Variável",
            "process_timestamp": process_ts
        })
    
    abandoned_tables = df_tables.filter(col("is_abandoned")).orderBy(desc("size_gb")).collect()
    for table in abandoned_tables[:10]:
        recommendations.append({
            "workspace_name": workspace_name,
            "category": "storage",
            "priority": "high",
            "title": f"Tabela {table.table_name} abandonada",
            "description": f"Tabela {table.full_table_name} não é acessada há {table.days_since_accessed} dias",
            "impact": "Alto",
            "complexity": "Média",
            "action": "Arquivar ou excluir tabela",
            "estimated_savings": f"{table.size_gb:.2f} GB",
            "process_timestamp": process_ts
        })
    
    small_files_tables = df_tables.filter(col("has_small_files") & (col("size_gb") > 100)).collect()
    for table in small_files_tables[:10]:
        recommendations.append({
            "workspace_name": workspace_name,
            "category": "storage",
            "priority": "medium",
            "title": f"Tabela {table.table_name} com muitos arquivos pequenos",
            "description": f"Tabela {table.full_table_name} tem {table.num_files} arquivos com média de {table.avg_file_size_mb:.2f} MB",
            "impact": "Médio",
            "complexity": "Baixa",
            "action": "Executar OPTIMIZE e Z-ORDER",
            "estimated_savings": "Melhoria de performance",
            "process_timestamp": process_ts
        })
    
    failed_jobs = df_jobs.filter(col("failure_rate") > 0.2).collect()
    for job in failed_jobs[:10]:
        recommendations.append({
            "workspace_name": workspace_name,
            "category": "pipelines",
            "priority": "high",
            "title": f"Job {job.job_name} com alta taxa de falha",
            "description": f"Job {job.job_id} tem {job.failure_rate * 100:.1f}% de falhas",
            "impact": "Alto",
            "complexity": "Alta",
            "action": "Investigar e corrigir causas de falha",
            "estimated_savings": "Redução de retrabalho",
            "process_timestamp": process_ts
        })
    
    return recommendations
