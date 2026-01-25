CREATE DATABASE IF NOT EXISTS finops_silver;

CREATE TABLE IF NOT EXISTS finops_silver.compute_clusters (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    cluster_id STRING,
    cluster_name STRING,
    state STRING,
    spark_version STRING,
    node_type_id STRING,
    driver_node_type_id STRING,
    num_workers INT,
    autotermination_minutes INT,
    enable_elastic_disk BOOLEAN,
    cluster_source STRING,
    is_running BOOLEAN,
    is_terminated BOOLEAN,
    has_autoscaling BOOLEAN,
    is_serverless BOOLEAN,
    uptime_hours DOUBLE,
    idle_hours DOUBLE,
    memory_gb DOUBLE,
    estimated_cost_per_hour DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/silver/compute/clusters'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_silver.compute_jobs (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    job_id INT,
    job_name STRING,
    job_type STRING,
    timeout_seconds INT,
    max_concurrent_runs INT,
    schedule STRING,
    uses_existing_cluster BOOLEAN,
    has_schedule BOOLEAN,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/silver/compute/jobs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_silver.compute_job_runs (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    job_id INT,
    run_id BIGINT,
    run_name STRING,
    state STRING,
    result_state STRING,
    start_time BIGINT,
    end_time BIGINT,
    duration_seconds DOUBLE,
    duration_hours DOUBLE,
    is_success BOOLEAN,
    is_failed BOOLEAN,
    is_cancelled BOOLEAN,
    has_error BOOLEAN,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/silver/compute/job_runs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_silver.storage_tables (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    metastore_type STRING,
    catalog STRING,
    schema STRING,
    table_name STRING,
    full_table_name STRING,
    table_type STRING,
    location STRING,
    provider STRING,
    num_files INT,
    size_in_bytes BIGINT,
    size_gb DOUBLE,
    size_tb DOUBLE,
    avg_file_size_mb DOUBLE,
    days_since_modified INT,
    days_since_accessed INT,
    is_partitioned BOOLEAN,
    is_delta BOOLEAN,
    has_small_files BOOLEAN,
    is_cold_data BOOLEAN,
    is_abandoned BOOLEAN,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/silver/storage/tables'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_silver.billing_costs (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    date STRING,
    date_parsed DATE,
    year INT,
    month INT,
    day INT,
    resource_id STRING,
    resource_type STRING,
    resource_group STRING,
    service STRING,
    cost DOUBLE,
    cost_usd DOUBLE,
    currency STRING,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud, year, month)
LOCATION 'dbfs:/finops/silver/billing/costs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
