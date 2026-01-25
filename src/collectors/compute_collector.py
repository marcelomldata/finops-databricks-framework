from datetime import datetime, timedelta
from typing import Dict, List
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, current_timestamp
from src.utils.databricks_client import DatabricksAPIClient, DatabricksConfig
from src.utils.cloud_detector import detect_cloud_from_url

def collect_clusters_metrics(
    spark: SparkSession,
    databricks_config: DatabricksConfig,
    workspace_name: str,
    workspace_url: str
) -> None:
    client = DatabricksAPIClient(databricks_config)
    cloud = detect_cloud_from_url(workspace_url)
    
    clusters = client.get_clusters()
    
    if not clusters:
        return
    
    cluster_data = []
    current_ts = datetime.utcnow()
    
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id")
        cluster_info = client.get_cluster_details(cluster_id)
        
        cluster_data.append({
            "workspace_name": workspace_name,
            "workspace_url": workspace_url,
            "cloud": cloud,
            "cluster_id": cluster_id,
            "cluster_name": cluster.get("cluster_name", ""),
            "state": cluster.get("state", ""),
            "spark_version": cluster_info.get("spark_version", ""),
            "node_type_id": cluster_info.get("node_type_id", ""),
            "driver_node_type_id": cluster_info.get("driver_node_type_id", ""),
            "num_workers": cluster_info.get("num_workers", 0),
            "autotermination_minutes": cluster_info.get("autotermination_minutes", 0),
            "enable_elastic_disk": cluster_info.get("enable_elastic_disk", False),
            "cluster_source": cluster_info.get("cluster_source", ""),
            "spark_conf": str(cluster_info.get("spark_conf", {})),
            "aws_attributes": str(cluster_info.get("aws_attributes", {})),
            "azure_attributes": str(cluster_info.get("azure_attributes", {})),
            "gcp_attributes": str(cluster_info.get("gcp_attributes", {})),
            "start_time": cluster_info.get("start_time", 0),
            "terminated_time": cluster_info.get("terminated_time", 0),
            "last_state_loss_time": cluster_info.get("last_state_loss_time", 0),
            "last_activity_time": cluster_info.get("last_activity_time", 0),
            "cluster_memory_mb": cluster_info.get("cluster_memory_mb", 0),
            "cluster_cores": cluster_info.get("cluster_cores", 0),
            "default_tags": str(cluster_info.get("default_tags", {})),
            "creator_user_name": cluster_info.get("creator_user_name", ""),
            "custom_tags": str(cluster_info.get("custom_tags", {})),
            "cluster_log_conf": str(cluster_info.get("cluster_log_conf", {})),
            "spark_env_vars": str(cluster_info.get("spark_env_vars", {})),
            "autoscale": str(cluster_info.get("autoscale", {})),
            "is_pinned": cluster_info.get("is_pinned", False),
            "is_high_availability": cluster_info.get("is_high_availability", False),
            "init_scripts": str(cluster_info.get("init_scripts", [])),
            "enable_local_disk_encryption": cluster_info.get("enable_local_disk_encryption", False),
            "data_security_mode": cluster_info.get("data_security_mode", ""),
            "runtime_engine": cluster_info.get("runtime_engine", ""),
            "photon": cluster_info.get("photon", False),
            "single_user_name": cluster_info.get("single_user_name", ""),
            "collect_timestamp": current_ts
        })
    
    df = spark.createDataFrame(cluster_data)
    
    df.write \
        .format("delta") \
        .mode("append") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/bronze/compute/clusters")

def collect_jobs_metrics(
    spark: SparkSession,
    databricks_config: DatabricksConfig,
    workspace_name: str,
    workspace_url: str,
    days_back: int = 30
) -> None:
    client = DatabricksAPIClient(databricks_config)
    cloud = detect_cloud_from_url(workspace_url)
    
    jobs = client.get_jobs()
    
    if not jobs:
        return
    
    job_data = []
    run_data = []
    current_ts = datetime.utcnow()
    cutoff_time = int((current_ts - timedelta(days=days_back)).timestamp() * 1000)
    
    for job in jobs:
        job_id = job.get("job_id")
        job_info = client.get_job_details(job_id)
        
        job_data.append({
            "workspace_name": workspace_name,
            "workspace_url": workspace_url,
            "cloud": cloud,
            "job_id": job_id,
            "job_name": job.get("settings", {}).get("name", ""),
            "job_type": job.get("job_type", {}).get("id", ""),
            "timeout_seconds": job_info.get("settings", {}).get("timeout_seconds", 0),
            "max_concurrent_runs": job_info.get("settings", {}).get("max_concurrent_runs", 1),
            "schedule": str(job_info.get("settings", {}).get("schedule", {})),
            "notebook_task": str(job_info.get("settings", {}).get("notebook_task", {})),
            "spark_python_task": str(job_info.get("settings", {}).get("spark_python_task", {})),
            "spark_jar_task": str(job_info.get("settings", {}).get("spark_jar_task", {})),
            "spark_submit_task": str(job_info.get("settings", {}).get("spark_submit_task", {})),
            "new_cluster": str(job_info.get("settings", {}).get("new_cluster", {})),
            "existing_cluster_id": job_info.get("settings", {}).get("existing_cluster_id", ""),
            "libraries": str(job_info.get("settings", {}).get("libraries", [])),
            "email_notifications": str(job_info.get("settings", {}).get("email_notifications", {})),
            "webhook_notifications": str(job_info.get("settings", {}).get("webhook_notifications", {})),
            "tags": str(job_info.get("settings", {}).get("tags", {})),
            "format": job_info.get("format", ""),
            "collect_timestamp": current_ts
        })
        
        runs = client.get_job_runs(job_id=job_id, limit=1000)
        
        for run in runs:
            if run.get("start_time", 0) < cutoff_time:
                continue
            
            run_data.append({
                "workspace_name": workspace_name,
                "workspace_url": workspace_url,
                "cloud": cloud,
                "job_id": job_id,
                "run_id": run.get("run_id", 0),
                "run_name": run.get("run_name", ""),
                "state": run.get("state", {}).get("life_cycle_state", ""),
                "result_state": run.get("state", {}).get("result_state", ""),
                "start_time": run.get("start_time", 0),
                "end_time": run.get("end_time", 0),
                "setup_duration": run.get("setup_duration", 0),
                "execution_duration": run.get("execution_duration", 0),
                "cleanup_duration": run.get("cleanup_duration", 0),
                "trigger": run.get("trigger", ""),
                "cluster_instance": str(run.get("cluster_instance", {})),
                "cluster_spec": str(run.get("cluster_spec", {})),
                "overriding_parameters": str(run.get("overriding_parameters", {})),
                "tasks": str(run.get("tasks", [])),
                "error": str(run.get("error", {})),
                "collect_timestamp": current_ts
            })
    
    if job_data:
        df_jobs = spark.createDataFrame(job_data)
        df_jobs.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/compute/jobs")
    
    if run_data:
        df_runs = spark.createDataFrame(run_data)
        df_runs.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/bronze/compute/job_runs")
