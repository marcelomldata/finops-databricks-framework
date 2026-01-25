from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, count, struct, current_timestamp
)
from typing import Dict, List
from datetime import datetime

def allocate_cost_by_pipeline(
    spark: SparkSession,
    workspace_name: str
) -> None:
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(col("workspace_name") == workspace_name) \
        .filter(col("start_time") >= int((datetime.utcnow().timestamp() - 30 * 24 * 3600) * 1000))
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    df_job_costs = df_runs \
        .join(df_costs, df_runs.cluster_instance.contains(df_costs.cluster_id), "left") \
        .groupBy("job_id") \
        .agg(
            spark_sum("estimated_dbu_cost").alias("total_dbu_cost"),
            avg("estimated_dbu_cost").alias("avg_dbu_cost_per_run"),
            count("*").alias("total_runs"),
            avg("duration_hours").alias("avg_duration_hours")
        )
    
    pipeline_allocation = []
    
    for row in df_jobs.join(df_job_costs, "job_id", "left").collect():
        job_id = row.job_id
        job_name = row.job_name
        
        total_cost = row.total_dbu_cost or 0.0
        avg_cost_per_run = row.avg_dbu_cost_per_run or 0.0
        total_runs = row.total_runs or 0
        avg_duration = row.avg_duration_hours or 0.0
        
        pipeline_name = job_name.split("_")[0] if "_" in job_name else job_name
        product_name = job_name.split("-")[0] if "-" in job_name else "default"
        
        sla_tier = "standard"
        if avg_duration < 0.5:
            sla_tier = "fast"
        elif avg_duration > 4:
            sla_tier = "slow"
        
        pipeline_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "pipeline",
            "resource_id": str(job_id),
            "resource_name": job_name,
            "pipeline_name": pipeline_name,
            "product_name": product_name,
            "sla_tier": sla_tier,
            "estimated_monthly_cost": total_cost * 30,
            "estimated_dbu_cost": total_cost,
            "cost_per_run": avg_cost_per_run,
            "total_runs_monthly": total_runs,
            "avg_duration_hours": avg_duration,
            "allocation_method": "job_runs",
            "process_timestamp": current_timestamp()
        })
    
    if pipeline_allocation:
        df_allocation = spark.createDataFrame(pipeline_allocation)
        df_allocation.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation_pipelines")

def get_cost_by_product(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    try:
        df_allocation = spark.read.format("delta").load("dbfs:/finops/gold/cost_allocation_pipelines") \
            .filter(col("workspace_name") == workspace_name)
        
        if df_allocation.count() == 0:
            return {}
        
        product_costs = df_allocation \
            .groupBy("product_name") \
            .agg({
                "estimated_monthly_cost": "sum",
                "resource_id": "count"
            }) \
            .collect()
        
        return {
            "by_product": {row.product_name: row["sum(estimated_monthly_cost)"] for row in product_costs},
            "by_pipeline": df_allocation.groupBy("pipeline_name").agg({"estimated_monthly_cost": "sum"}).collect(),
            "by_sla": df_allocation.groupBy("sla_tier").agg({"estimated_monthly_cost": "sum"}).collect()
        }
    except:
        return {}
