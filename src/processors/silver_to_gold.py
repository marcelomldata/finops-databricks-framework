from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, max as spark_max, min as spark_min,
    count, countDistinct, collect_list, struct, current_timestamp,
    rank, window, desc, asc, round
)
from pyspark.sql.window import Window

def process_compute_gold(spark: SparkSession) -> None:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/silver/compute/clusters")
    df_jobs = spark.read.format("delta").load("dbfs:/finops/silver/compute/jobs")
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs")
    
    window_spec = Window.partitionBy("workspace_name").orderBy(desc("uptime_hours"))
    
    df_clusters_ranked = df_clusters \
        .withColumn("rank_by_uptime", rank().over(window_spec)) \
        .withColumn("is_idle", when(col("idle_hours") > 4, True).otherwise(False)) \
        .withColumn("is_overprovisioned", 
            when((col("num_workers") > 10) & (col("idle_hours") > 2), True)
            .otherwise(False)) \
        .withColumn("utilization_score", 
            when(col("idle_hours").isNull(), 0.5)
            .when(col("idle_hours") < 1, 1.0)
            .when(col("idle_hours") < 4, 0.7)
            .when(col("idle_hours") < 8, 0.4)
            .otherwise(0.1))
    
    df_clusters_gold = df_clusters_ranked \
        .select(
            "workspace_name",
            "cluster_id",
            "cluster_name",
            "state",
            "num_workers",
            "memory_gb",
            "uptime_hours",
            "idle_hours",
            "is_idle",
            "is_overprovisioned",
            "utilization_score",
            "has_autoscaling",
            "rank_by_uptime",
            current_timestamp().alias("process_timestamp")
        )
    
    df_clusters_gold.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/compute/clusters_summary")
    
    df_runs_agg = df_runs \
        .groupBy("workspace_name", "job_id") \
        .agg(
            count("*").alias("total_runs"),
            spark_sum(when(col("is_success"), 1).otherwise(0)).alias("successful_runs"),
            spark_sum(when(col("is_failed"), 1).otherwise(0)).alias("failed_runs"),
            avg("duration_hours").alias("avg_duration_hours"),
            max("duration_hours").alias("max_duration_hours"),
            min("duration_hours").alias("min_duration_hours"),
            spark_sum("duration_hours").alias("total_duration_hours")
        ) \
        .withColumn("success_rate", col("successful_runs") / col("total_runs")) \
        .withColumn("failure_rate", col("failed_runs") / col("total_runs")) \
        .withColumn("efficiency_score",
            when(col("success_rate") >= 0.95, 1.0)
            .when(col("success_rate") >= 0.80, 0.7)
            .when(col("success_rate") >= 0.60, 0.4)
            .otherwise(0.1))
    
    df_jobs_gold = df_jobs \
        .join(df_runs_agg, ["workspace_name", "job_id"], "left") \
        .withColumn("process_timestamp", current_timestamp())
    
    df_jobs_gold.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/compute/jobs_summary")

def process_storage_gold(spark: SparkSession) -> None:
    df_tables = spark.read.format("delta").load("dbfs:/finops/silver/storage/tables")
    
    df_tables_gold = df_tables \
        .withColumn("storage_tier",
            when(col("is_cold_data"), "cold")
            .when(col("days_since_accessed") > 30, "warm")
            .otherwise("hot")) \
        .withColumn("optimization_priority",
            when(col("is_abandoned"), "high")
            .when(col("has_small_files") & (col("size_gb") > 100), "high")
            .when(col("is_cold_data") & (col("size_gb") > 10), "medium")
            .when(~col("is_partitioned") & (col("size_gb") > 50), "medium")
            .otherwise("low")) \
        .withColumn("estimated_savings_gb",
            when(col("is_abandoned"), col("size_gb"))
            .when(col("is_cold_data"), col("size_gb") * 0.5)
            .otherwise(0.0))
    
    df_tables_gold.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/storage/tables_summary")
    
    df_storage_summary = df_tables \
        .groupBy("workspace_name") \
        .agg(
            count("*").alias("total_tables"),
            spark_sum("size_tb").alias("total_size_tb"),
            spark_sum(when(col("is_cold_data"), col("size_tb")).otherwise(0)).alias("cold_size_tb"),
            spark_sum(when(col("is_abandoned"), col("size_tb")).otherwise(0)).alias("abandoned_size_tb"),
            spark_sum(when(col("has_small_files"), col("size_tb")).otherwise(0)).alias("small_files_size_tb"),
            countDistinct("schema").alias("total_schemas"),
            avg("avg_file_size_mb").alias("avg_file_size_mb")
        ) \
        .withColumn("cold_data_percentage", 
            when(col("total_size_tb") > 0, (col("cold_size_tb") / col("total_size_tb")) * 100)
            .otherwise(0)) \
        .withColumn("abandoned_data_percentage",
            when(col("total_size_tb") > 0, (col("abandoned_size_tb") / col("total_size_tb")) * 100)
            .otherwise(0)) \
        .withColumn("process_timestamp", current_timestamp())
    
    df_storage_summary.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/storage/workspace_summary")

def process_billing_gold(spark: SparkSession) -> None:
    df_costs = spark.read.format("delta").load("dbfs:/finops/silver/billing/costs")
    
    df_costs_daily = df_costs \
        .groupBy("workspace_name", "date_parsed") \
        .agg(
            spark_sum("cost_usd").alias("daily_cost_usd")
        )
    
    df_costs_monthly = df_costs \
        .groupBy("workspace_name", "year", "month") \
        .agg(
            spark_sum("cost_usd").alias("monthly_cost_usd"),
            avg("cost_usd").alias("avg_daily_cost_usd")
        )
    
    df_costs_gold = df_costs_daily \
        .join(df_costs_monthly, ["workspace_name"], "left") \
        .withColumn("process_timestamp", current_timestamp())
    
    df_costs_gold.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/billing/costs_summary")
