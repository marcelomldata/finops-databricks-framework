from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, max as spark_max, min as spark_min,
    count, countDistinct, datediff, current_timestamp, desc, asc
)
from typing import Dict, List, Optional
from datetime import datetime, timedelta

def get_baseline_state(spark: SparkSession, workspace_name: str, baseline_date: str) -> Dict:
    baseline_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("process_timestamp") <= baseline_date)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    baseline_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("process_timestamp") <= baseline_date)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    baseline_recommendations = spark.read.format("delta").load("dbfs:/finops/gold/recommendations") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("process_timestamp") <= baseline_date)) \
        .orderBy(desc("process_timestamp"))
    
    baseline_maturity = spark.read.format("delta").load("dbfs:/finops/gold/maturity_scores") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("process_timestamp") <= baseline_date)) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    return {
        "clusters": baseline_clusters.collect() if baseline_clusters.count() > 0 else [],
        "tables": baseline_tables.collect() if baseline_tables.count() > 0 else [],
        "recommendations": baseline_recommendations.collect(),
        "maturity": baseline_maturity.collect()[0] if baseline_maturity.count() > 0 else None
    }

def get_current_state(spark: SparkSession, workspace_name: str) -> Dict:
    current_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    current_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    current_recommendations = spark.read.format("delta").load("dbfs:/finops/gold/recommendations") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp"))
    
    current_maturity = spark.read.format("delta").load("dbfs:/finops/gold/maturity_scores") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(1)
    
    return {
        "clusters": current_clusters.collect() if current_clusters.count() > 0 else [],
        "tables": current_tables.collect() if current_tables.count() > 0 else [],
        "recommendations": current_recommendations.collect(),
        "maturity": current_maturity.collect()[0] if current_maturity.count() > 0 else None
    }

def compare_recommendations_status(
    spark: SparkSession,
    workspace_name: str,
    baseline_date: str
) -> List[Dict]:
    baseline_recs = spark.read.format("delta").load("dbfs:/finops/gold/recommendations") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("process_timestamp") <= baseline_date)) \
        .select("title", "category", "priority", "action").distinct()
    
    current_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(1000)
    
    current_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(10000)
    
    current_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name) \
        .orderBy(desc("process_timestamp")) \
        .limit(1000)
    
    status_list = []
    
    baseline_recs_list = baseline_recs.collect()
    
    for rec in baseline_recs_list:
        title = rec.title
        category = rec.category
        action = rec.action
        
        status = "não_implementada"
        
        if category == "compute":
            if "ocioso" in title.lower() or "idle" in title.lower():
                cluster_name = title.split("Cluster ")[1].split(" está")[0] if "Cluster " in title else ""
                if cluster_name:
                    matching = current_clusters.filter(
                        (col("cluster_name") == cluster_name) & 
                        (col("is_idle") == True)
                    ).count()
                    if matching == 0:
                        status = "implementada"
                    else:
                        status = "regressão"
            elif "autoscaling" in title.lower():
                cluster_name = title.split("Cluster ")[1].split(" sem")[0] if "Cluster " in title else ""
                if cluster_name:
                    matching = current_clusters.filter(
                        (col("cluster_name") == cluster_name) & 
                        (col("has_autoscaling") == False)
                    ).count()
                    if matching == 0:
                        status = "implementada"
        
        elif category == "storage":
            if "abandonada" in title.lower() or "abandoned" in title.lower():
                table_name = title.split("Tabela ")[1].split(" abandonada")[0] if "Tabela " in title else ""
                if table_name:
                    matching = current_tables.filter(
                        (col("table_name") == table_name) & 
                        (col("is_abandoned") == True)
                    ).count()
                    if matching == 0:
                        status = "implementada"
                    else:
                        status = "regressão"
            elif "small files" in title.lower() or "arquivos pequenos" in title.lower():
                table_name = title.split("Tabela ")[1].split(" com")[0] if "Tabela " in title else ""
                if table_name:
                    matching = current_tables.filter(
                        (col("table_name") == table_name) & 
                        (col("has_small_files") == True) &
                        (col("size_gb") > 100)
                    ).count()
                    if matching == 0:
                        status = "implementada"
        
        elif category == "pipelines":
            if "alta taxa de falha" in title.lower() or "high failure" in title.lower():
                job_name = title.split("Job ")[1].split(" com")[0] if "Job " in title else ""
                if job_name:
                    matching = current_jobs.filter(
                        (col("job_name") == job_name) & 
                        (col("failure_rate") > 0.2)
                    ).count()
                    if matching == 0:
                        status = "implementada"
        
        status_list.append({
            "workspace_name": workspace_name,
            "recommendation_title": title,
            "category": category,
            "priority": rec.priority,
            "status": status,
            "baseline_date": baseline_date,
            "validation_timestamp": datetime.utcnow()
        })
    
    return status_list

def validate_storage_maintenance(spark: SparkSession, workspace_name: str) -> List[Dict]:
    df_tables = spark.read.format("delta").load("dbfs:/finops/gold/storage/tables_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_history = spark.read.format("delta").load("dbfs:/finops/bronze/storage/tables") \
        .filter(col("workspace_name") == workspace_name) \
        .groupBy("full_table_name") \
        .agg(count("*").alias("version_count"))
    
    issues = []
    
    no_optimize = df_tables.filter(
        (col("is_delta") == True) &
        (col("has_small_files") == True) &
        (col("size_gb") > 10)
    ).select("full_table_name", "size_gb", "num_files", "avg_file_size_mb").collect()
    
    for table in no_optimize:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "missing_optimize",
            "table_name": table.full_table_name,
            "severity": "high" if table.size_gb > 100 else "medium",
            "description": f"Tabela Delta sem OPTIMIZE: {table.num_files} arquivos, média {table.avg_file_size_mb:.2f} MB",
            "recommended_action": "Executar OPTIMIZE ZORDER BY (colunas de join)",
            "estimated_impact": f"Redução de {table.num_files * 0.3:.0f} arquivos, melhoria de 30-50% em queries",
            "validation_timestamp": datetime.utcnow()
        })
    
    abandoned = df_tables.filter(col("is_abandoned") == True).collect()
    for table in abandoned:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "abandoned_table",
            "table_name": table.full_table_name,
            "severity": "high",
            "description": f"Tabela abandonada: {table.days_since_accessed} dias sem acesso, {table.size_gb:.2f} GB",
            "recommended_action": "Arquivar ou excluir tabela",
            "estimated_impact": f"Economia de {table.size_gb:.2f} GB de storage",
            "validation_timestamp": datetime.utcnow()
        })
    
    return issues

def validate_compute_usage(spark: SparkSession, workspace_name: str) -> List[Dict]:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(col("workspace_name") == workspace_name) \
        .filter(col("start_time") >= int((datetime.utcnow() - timedelta(days=7)).timestamp() * 1000))
    
    issues = []
    
    idle_clusters = df_clusters.filter(
        (col("is_idle") == True) &
        (col("idle_hours") > 4)
    ).collect()
    
    for cluster in idle_clusters:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "idle_cluster",
            "resource_id": cluster.cluster_id,
            "resource_name": cluster.cluster_name,
            "severity": "high",
            "description": f"Cluster ocioso há {cluster.idle_hours:.1f} horas",
            "recommended_action": "Desligar cluster ou configurar autotermination",
            "estimated_impact": f"Economia estimada: {cluster.idle_hours * cluster.num_workers * 0.5:.2f} USD",
            "validation_timestamp": datetime.utcnow()
        })
    
    failed_jobs = df_jobs.filter(col("failure_rate") > 0.2).collect()
    for job in failed_jobs:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "high_failure_job",
            "resource_id": str(job.job_id),
            "resource_name": job.job_name,
            "severity": "high",
            "description": f"Job com {job.failure_rate * 100:.1f}% de falhas em {job.total_runs} execuções",
            "recommended_action": "Investigar logs, corrigir erros, implementar retry inteligente",
            "estimated_impact": f"Redução de {job.failed_runs * 0.5:.1f} horas de retrabalho/semana",
            "validation_timestamp": datetime.utcnow()
        })
    
    no_autoscaling = df_clusters.filter(
        (col("has_autoscaling") == False) &
        (col("num_workers") > 5)
    ).collect()
    
    for cluster in no_autoscaling:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "missing_autoscaling",
            "resource_id": cluster.cluster_id,
            "resource_name": cluster.cluster_name,
            "severity": "medium",
            "description": f"Cluster com {cluster.num_workers} workers fixos sem autoscaling",
            "recommended_action": "Configurar autoscaling baseado em carga",
            "estimated_impact": f"Economia estimada: 20-40% em custos de compute",
            "validation_timestamp": datetime.utcnow()
        })
    
    return issues

def validate_workflows_pipelines(spark: SparkSession, workspace_name: str) -> List[Dict]:
    df_jobs = spark.read.format("delta").load("dbfs:/finops/silver/compute/jobs") \
        .filter(col("workspace_name") == workspace_name)
    
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(col("workspace_name") == workspace_name) \
        .filter(col("start_time") >= int((datetime.utcnow() - timedelta(days=30)).timestamp() * 1000))
    
    issues = []
    
    no_schedule = df_jobs.filter(col("has_schedule") == False).collect()
    for job in no_schedule:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "job_without_schedule",
            "resource_id": str(job.job_id),
            "resource_name": job.job_name,
            "severity": "medium",
            "description": "Job sem schedule definido, execução manual",
            "recommended_action": "Definir schedule apropriado ou considerar remoção",
            "estimated_impact": "Melhoria de governança e previsibilidade",
            "validation_timestamp": datetime.utcnow()
        })
    
    long_runs = df_runs.filter(col("duration_hours") > 4).collect()
    for run in long_runs[:20]:
        issues.append({
            "workspace_name": workspace_name,
            "issue_type": "long_running_job",
            "resource_id": str(run.run_id),
            "resource_name": run.run_name,
            "severity": "medium",
            "description": f"Job executando por {run.duration_hours:.1f} horas",
            "recommended_action": "Otimizar query, particionar dados, revisar lógica",
            "estimated_impact": "Redução de custo e melhoria de SLA",
            "validation_timestamp": datetime.utcnow()
        })
    
    return issues

def detect_new_resources(
    spark: SparkSession,
    workspace_name: str,
    baseline_date: str
) -> Dict:
    baseline_clusters = spark.read.format("delta").load("dbfs:/finops/bronze/compute/clusters") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("collect_timestamp") <= baseline_date)) \
        .select("cluster_id").distinct()
    
    current_clusters = spark.read.format("delta").load("dbfs:/finops/bronze/compute/clusters") \
        .filter(col("workspace_name") == workspace_name) \
        .select("cluster_id").distinct()
    
    baseline_tables = spark.read.format("delta").load("dbfs:/finops/bronze/storage/tables") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("collect_timestamp") <= baseline_date)) \
        .select("full_table_name").distinct()
    
    current_tables = spark.read.format("delta").load("dbfs:/finops/bronze/storage/tables") \
        .filter(col("workspace_name") == workspace_name) \
        .select("full_table_name").distinct()
    
    baseline_jobs = spark.read.format("delta").load("dbfs:/finops/bronze/compute/jobs") \
        .filter((col("workspace_name") == workspace_name) & 
                (col("collect_timestamp") <= baseline_date)) \
        .select("job_id").distinct()
    
    current_jobs = spark.read.format("delta").load("dbfs:/finops/bronze/compute/jobs") \
        .filter(col("workspace_name") == workspace_name) \
        .select("job_id").distinct()
    
    new_clusters = current_clusters.join(baseline_clusters, "cluster_id", "left_anti").count()
    new_tables = current_tables.join(baseline_tables, "full_table_name", "left_anti").count()
    new_jobs = current_jobs.join(baseline_jobs, "job_id", "left_anti").count()
    
    return {
        "workspace_name": workspace_name,
        "new_clusters": new_clusters,
        "new_tables": new_tables,
        "new_jobs": new_jobs,
        "baseline_date": baseline_date,
        "detection_timestamp": datetime.utcnow()
    }
