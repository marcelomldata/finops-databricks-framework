CREATE DATABASE IF NOT EXISTS finops_gold;

CREATE TABLE IF NOT EXISTS finops_gold.cost_allocation_pipelines (
    workspace_name STRING,
    resource_type STRING,
    resource_id STRING,
    resource_name STRING,
    pipeline_name STRING,
    product_name STRING,
    sla_tier STRING,
    estimated_monthly_cost DOUBLE,
    estimated_dbu_cost DOUBLE,
    cost_per_run DOUBLE,
    total_runs_monthly BIGINT,
    avg_duration_hours DOUBLE,
    allocation_method STRING,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, product_name)
LOCATION 'dbfs:/finops/gold/cost_allocation_pipelines'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.billing_reconciliation (
    workspace_name STRING,
    reconciliation_date STRING,
    estimated_monthly_cost DOUBLE,
    actual_cost DOUBLE,
    variance DOUBLE,
    variance_percentage DOUBLE,
    reconciliation_status STRING,
    confidence STRING,
    recommendation STRING,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/billing_reconciliation'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.automation_actions (
    workspace_name STRING,
    resource_type STRING,
    resource_id STRING,
    resource_name STRING,
    action_type STRING,
    automation_level STRING,
    condition STRING,
    estimated_savings DOUBLE,
    risk_level STRING,
    requires_approval BOOLEAN,
    can_execute BOOLEAN,
    action_command STRING,
    rollback_command STRING,
    executed BOOLEAN,
    executed_at TIMESTAMP,
    generated_at TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, automation_level)
LOCATION 'dbfs:/finops/gold/automation_actions'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.observability_enhanced (
    workspace_name STRING,
    analysis_type STRING,
    metric_name STRING,
    metric_value DOUBLE,
    benchmark_level STRING,
    recommendation STRING,
    analysis_date TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, analysis_type)
LOCATION 'dbfs:/finops/gold/observability_enhanced'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.benchmarks (
    workspace_name STRING,
    benchmark_date STRING,
    cost_per_tb DOUBLE,
    cost_per_tb_level STRING,
    cluster_utilization DOUBLE,
    utilization_level STRING,
    job_success_rate DOUBLE,
    success_rate_level STRING,
    cold_data_percentage DOUBLE,
    cold_data_level STRING,
    overall_score DOUBLE,
    overall_level STRING,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/benchmarks'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
