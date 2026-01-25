from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, current_timestamp, datediff, 
    sum as spark_sum, avg, max as spark_max, min as spark_min,
    count, countDistinct, regexp_extract, split, size, array
)
from datetime import datetime, timedelta

def process_compute_silver(spark: SparkSession) -> None:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/bronze/compute/clusters")
    df_jobs = spark.read.format("delta").load("dbfs:/finops/bronze/compute/jobs")
    df_runs = spark.read.format("delta").load("dbfs:/finops/bronze/compute/job_runs")
    
    df_clusters_silver = df_clusters \
        .withColumn("is_running", when(col("state") == "RUNNING", True).otherwise(False)) \
        .withColumn("is_terminated", when(col("state") == "TERMINATED", True).otherwise(False)) \
        .withColumn("has_autoscaling", when(col("autoscale") != "null", True).otherwise(False)) \
        .withColumn("is_serverless", when(col("cluster_source") == "UI", False).otherwise(True)) \
        .withColumn("uptime_hours", 
            when(col("start_time").isNotNull() & col("terminated_time").isNotNull(),
                (col("terminated_time") - col("start_time")) / 3600000)
            .otherwise(None)) \
        .withColumn("idle_hours",
            when(col("last_activity_time").isNotNull() & col("start_time").isNotNull(),
                (current_timestamp().cast("long") * 1000 - col("last_activity_time")) / 3600000)
            .otherwise(None)) \
        .withColumn("memory_gb", col("cluster_memory_mb") / 1024) \
        .withColumn("estimated_cost_per_hour", lit(0.0)) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_clusters_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/silver/compute/clusters")
    
    df_jobs_silver = df_jobs \
        .withColumn("uses_existing_cluster", when(col("existing_cluster_id") != "", True).otherwise(False)) \
        .withColumn("has_schedule", when(col("schedule") != "null", True).otherwise(False)) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_jobs_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/silver/compute/jobs")
    
    df_runs_silver = df_runs \
        .withColumn("duration_seconds", col("execution_duration") / 1000) \
        .withColumn("duration_hours", col("execution_duration") / 3600000) \
        .withColumn("is_success", when(col("result_state") == "SUCCESS", True).otherwise(False)) \
        .withColumn("is_failed", when(col("result_state") == "FAILED", True).otherwise(False)) \
        .withColumn("is_cancelled", when(col("result_state") == "CANCELLED", True).otherwise(False)) \
        .withColumn("has_error", when(col("error") != "null", True).otherwise(False)) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_runs_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/silver/compute/job_runs")

def process_storage_silver(spark: SparkSession) -> None:
    df_tables = spark.read.format("delta").load("dbfs:/finops/bronze/storage/tables")
    
    df_tables_silver = df_tables \
        .withColumn("size_gb", col("size_in_bytes") / (1024 * 1024 * 1024)) \
        .withColumn("size_tb", col("size_in_bytes") / (1024 * 1024 * 1024 * 1024)) \
        .withColumn("avg_file_size_mb", 
            when(col("num_files") > 0, 
                (col("size_in_bytes") / col("num_files")) / (1024 * 1024))
            .otherwise(0)) \
        .withColumn("days_since_modified", 
            when(col("last_modified").isNotNull(),
                datediff(current_timestamp(), col("last_modified")))
            .otherwise(None)) \
        .withColumn("days_since_accessed", 
            when(col("last_access").isNotNull(),
                datediff(current_timestamp(), col("last_access")))
            .otherwise(None)) \
        .withColumn("is_partitioned", when(size(split(col("partition_columns"), ",")) > 1, True).otherwise(False)) \
        .withColumn("is_delta", when(col("table_type") == "delta", True).otherwise(False)) \
        .withColumn("has_small_files", when(col("avg_file_size_mb") < 128, True).otherwise(False)) \
        .withColumn("is_cold_data", 
            when(col("days_since_accessed") > 90, True)
            .when(col("days_since_accessed").isNull() & (col("days_since_modified") > 90), True)
            .otherwise(False)) \
        .withColumn("is_abandoned", 
            when(col("days_since_accessed") > 180, True)
            .when(col("days_since_accessed").isNull() & (col("days_since_modified") > 180), True)
            .otherwise(False)) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_tables_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/silver/storage/tables")

def process_billing_silver(spark: SparkSession) -> None:
    df_costs = spark.read.format("delta").load("dbfs:/finops/bronze/billing/costs")
    
    df_costs_silver = df_costs \
        .withColumn("cost_usd", 
            when(col("currency") == "USD", col("cost"))
            .otherwise(col("cost") * 1.0)) \
        .withColumn("date_parsed", col("date").cast("date")) \
        .withColumn("year", col("date_parsed").year) \
        .withColumn("month", col("date_parsed").month) \
        .withColumn("day", col("date_parsed").day) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_costs_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/silver/billing/costs")
