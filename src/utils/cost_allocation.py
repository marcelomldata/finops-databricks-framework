from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, coalesce, struct, current_timestamp
)
from typing import Dict, Optional

def extract_cost_allocation_tags(
    spark: SparkSession,
    workspace_name: str
) -> None:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/silver/compute/clusters") \
        .filter(col("workspace_name") == workspace_name)
    
    df_jobs = spark.read.format("delta").load("dbfs:/finops/silver/compute/jobs") \
        .filter(col("workspace_name") == workspace_name)
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    def parse_tags(tags_str: str) -> Dict:
        import json
        try:
            if tags_str and tags_str != "null" and tags_str != "":
                tags = json.loads(tags_str.replace("'", '"'))
                return {
                    "cost_center": tags.get("cost_center") or tags.get("CostCenter") or "",
                    "business_unit": tags.get("business_unit") or tags.get("BusinessUnit") or "",
                    "data_domain": tags.get("data_domain") or tags.get("DataDomain") or "",
                    "project": tags.get("project") or tags.get("Project") or "",
                    "owner": tags.get("owner") or tags.get("Owner") or ""
                }
        except:
            pass
        return {
            "cost_center": "",
            "business_unit": "",
            "data_domain": "",
            "project": "",
            "owner": ""
        }
    
    cluster_allocation = []
    for row in df_clusters.collect():
        tags = parse_tags(row.custom_tags if hasattr(row, 'custom_tags') else "")
        cluster_cost = df_costs.filter(col("cluster_id") == row.cluster_id).collect()
        monthly_cost = cluster_cost[0].estimated_monthly_cost if cluster_cost else 0.0
        dbu_cost = cluster_cost[0].estimated_dbu_cost if cluster_cost else 0.0
        
        cost_center = tags["cost_center"] or "unallocated"
        
        cluster_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "cluster",
            "resource_id": row.cluster_id,
            "resource_name": row.cluster_name if hasattr(row, 'cluster_name') else "",
            "cost_center": cost_center,
            "business_unit": tags["business_unit"] or "unallocated",
            "data_domain": tags["data_domain"] or "unallocated",
            "estimated_monthly_cost": monthly_cost,
            "estimated_dbu_cost": dbu_cost,
            "allocation_method": "tags" if tags["cost_center"] else "default",
            "tags": tags,
            "process_timestamp": current_timestamp()
        })
    
    job_allocation = []
    for row in df_jobs.collect():
        tags = parse_tags(row.tags if hasattr(row, 'tags') else "")
        
        cost_center = tags["cost_center"] or "unallocated"
        
        job_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "job",
            "resource_id": str(row.job_id),
            "resource_name": row.job_name if hasattr(row, 'job_name') else "",
            "cost_center": cost_center,
            "business_unit": tags["business_unit"] or "unallocated",
            "data_domain": tags["data_domain"] or "unallocated",
            "estimated_monthly_cost": 0.0,
            "estimated_dbu_cost": 0.0,
            "allocation_method": "tags" if tags["cost_center"] else "default",
            "tags": tags,
            "process_timestamp": current_timestamp()
        })
    
    if cluster_allocation:
        df_cluster_alloc = spark.createDataFrame(cluster_allocation)
        df_cluster_alloc.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation")
    
    if job_allocation:
        df_job_alloc = spark.createDataFrame(job_allocation)
        df_job_alloc.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation")

def get_cost_by_domain(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    df_allocation = spark.read.format("delta").load("dbfs:/finops/gold/cost_allocation") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_allocation.count() == 0:
        return {}
    
    domain_costs = df_allocation \
        .groupBy("cost_center", "business_unit", "data_domain") \
        .agg({
            "estimated_monthly_cost": "sum",
            "estimated_dbu_cost": "sum"
        }) \
        .collect()
    
    return {
        "by_cost_center": {row.cost_center: row["sum(estimated_monthly_cost)"] for row in domain_costs},
        "by_business_unit": {row.business_unit: row["sum(estimated_monthly_cost)"] for row in domain_costs},
        "by_data_domain": {row.data_domain: row["sum(estimated_monthly_cost)"] for row in domain_costs}
    }
