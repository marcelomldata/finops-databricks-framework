CREATE DATABASE IF NOT EXISTS finops_bronze;

CREATE TABLE IF NOT EXISTS finops_bronze.compute_clusters (
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
    spark_conf STRING,
    aws_attributes STRING,
    azure_attributes STRING,
    gcp_attributes STRING,
    start_time BIGINT,
    terminated_time BIGINT,
    last_state_loss_time BIGINT,
    last_activity_time BIGINT,
    cluster_memory_mb DOUBLE,
    cluster_cores DOUBLE,
    default_tags STRING,
    creator_user_name STRING,
    custom_tags STRING,
    cluster_log_conf STRING,
    spark_env_vars STRING,
    autoscale STRING,
    is_pinned BOOLEAN,
    is_high_availability BOOLEAN,
    init_scripts STRING,
    enable_local_disk_encryption BOOLEAN,
    data_security_mode STRING,
    runtime_engine STRING,
    photon BOOLEAN,
    single_user_name STRING,
    collect_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/bronze/compute/clusters'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_bronze.compute_jobs (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    job_id INT,
    job_name STRING,
    job_type STRING,
    timeout_seconds INT,
    max_concurrent_runs INT,
    schedule STRING,
    notebook_task STRING,
    spark_python_task STRING,
    spark_jar_task STRING,
    spark_submit_task STRING,
    new_cluster STRING,
    existing_cluster_id STRING,
    libraries STRING,
    email_notifications STRING,
    webhook_notifications STRING,
    tags STRING,
    format STRING,
    collect_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/bronze/compute/jobs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_bronze.compute_job_runs (
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
    setup_duration BIGINT,
    execution_duration BIGINT,
    cleanup_duration BIGINT,
    trigger STRING,
    cluster_instance STRING,
    cluster_spec STRING,
    overriding_parameters STRING,
    tasks STRING,
    error STRING,
    collect_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/bronze/compute/job_runs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_bronze.storage_tables (
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
    partition_columns STRING,
    last_modified TIMESTAMP,
    last_access TIMESTAMP,
    collect_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/bronze/storage/tables'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_bronze.billing_costs (
    workspace_name STRING,
    workspace_url STRING,
    cloud STRING,
    date STRING,
    resource_id STRING,
    resource_type STRING,
    resource_group STRING,
    service STRING,
    cost DOUBLE,
    currency STRING,
    collect_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud, date)
LOCATION 'dbfs:/finops/bronze/billing/costs'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
