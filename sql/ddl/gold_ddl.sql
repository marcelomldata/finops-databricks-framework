CREATE DATABASE IF NOT EXISTS finops_gold;

CREATE TABLE IF NOT EXISTS finops_gold.compute_clusters_summary (
    workspace_name STRING,
    cluster_id STRING,
    cluster_name STRING,
    state STRING,
    num_workers INT,
    memory_gb DOUBLE,
    uptime_hours DOUBLE,
    idle_hours DOUBLE,
    is_idle BOOLEAN,
    is_overprovisioned BOOLEAN,
    utilization_score DOUBLE,
    has_autoscaling BOOLEAN,
    rank_by_uptime INT,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/compute/clusters_summary'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.compute_jobs_summary (
    workspace_name STRING,
    job_id INT,
    job_name STRING,
    job_type STRING,
    uses_existing_cluster BOOLEAN,
    has_schedule BOOLEAN,
    total_runs BIGINT,
    successful_runs BIGINT,
    failed_runs BIGINT,
    avg_duration_hours DOUBLE,
    max_duration_hours DOUBLE,
    min_duration_hours DOUBLE,
    total_duration_hours DOUBLE,
    success_rate DOUBLE,
    failure_rate DOUBLE,
    efficiency_score DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/compute/jobs_summary'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.storage_tables_summary (
    workspace_name STRING,
    catalog STRING,
    schema STRING,
    table_name STRING,
    full_table_name STRING,
    table_type STRING,
    size_gb DOUBLE,
    size_tb DOUBLE,
    num_files INT,
    avg_file_size_mb DOUBLE,
    days_since_modified INT,
    days_since_accessed INT,
    is_partitioned BOOLEAN,
    is_delta BOOLEAN,
    has_small_files BOOLEAN,
    is_cold_data BOOLEAN,
    is_abandoned BOOLEAN,
    storage_tier STRING,
    optimization_priority STRING,
    estimated_savings_gb DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/storage/tables_summary'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.storage_workspace_summary (
    workspace_name STRING,
    total_tables BIGINT,
    total_size_tb DOUBLE,
    cold_size_tb DOUBLE,
    abandoned_size_tb DOUBLE,
    small_files_size_tb DOUBLE,
    total_schemas BIGINT,
    avg_file_size_mb DOUBLE,
    cold_data_percentage DOUBLE,
    abandoned_data_percentage DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/storage/workspace_summary'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.billing_costs_summary (
    workspace_name STRING,
    date_parsed DATE,
    year INT,
    month INT,
    daily_cost_usd DOUBLE,
    monthly_cost_usd DOUBLE,
    avg_daily_cost_usd DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, year, month)
LOCATION 'dbfs:/finops/billing/costs_summary'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.maturity_scores (
    workspace_name STRING,
    maturity_score DOUBLE,
    maturity_level STRING,
    compute_score DOUBLE,
    storage_score DOUBLE,
    governance_score DOUBLE,
    pipelines_score DOUBLE,
    observability_score DOUBLE,
    costs_score DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/maturity_scores'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.recommendations (
    workspace_name STRING,
    category STRING,
    priority STRING,
    title STRING,
    description STRING,
    impact STRING,
    complexity STRING,
    action STRING,
    estimated_savings STRING,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, category)
LOCATION 'dbfs:/finops/gold/recommendations'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
