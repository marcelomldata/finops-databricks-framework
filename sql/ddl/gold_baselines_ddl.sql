CREATE DATABASE IF NOT EXISTS finops_gold;

CREATE TABLE IF NOT EXISTS finops_gold.assessment_baselines (
    baseline_id STRING,
    workspace_name STRING,
    baseline_date DATE,
    cloud STRING,
    framework_version STRING,
    maturity_score DOUBLE,
    maturity_level STRING,
    compute_score DOUBLE,
    storage_score DOUBLE,
    governance_score DOUBLE,
    pipelines_score DOUBLE,
    observability_score DOUBLE,
    costs_score DOUBLE,
    estimated_monthly_cost DOUBLE,
    estimated_annual_cost DOUBLE,
    total_clusters INT,
    total_jobs INT,
    total_tables BIGINT,
    total_storage_tb DOUBLE,
    context STRUCT<
        num_workspaces: INT,
        primary_use_case: STRING,
        team_size: INT,
        notes: STRING
    >,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, baseline_date)
LOCATION 'dbfs:/finops/gold/assessment_baselines'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);


CREATE TABLE IF NOT EXISTS finops_gold.cost_allocation (
    workspace_name STRING,
    resource_type STRING,
    resource_id STRING,
    resource_name STRING,
    cost_center STRING,
    business_unit STRING,
    data_domain STRING,
    estimated_monthly_cost DOUBLE,
    estimated_dbu_cost DOUBLE,
    allocation_method STRING,
    tags STRUCT<
        cost_center: STRING,
        business_unit: STRING,
        data_domain: STRING,
        project: STRING,
        owner: STRING
    >,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cost_center)
LOCATION 'dbfs:/finops/gold/cost_allocation'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);


CREATE TABLE IF NOT EXISTS finops_gold.costs_dbu_estimates (
    workspace_name STRING,
    cloud STRING,
    cluster_id STRING,
    cluster_name STRING,
    cluster_type STRING,
    num_workers INT,
    uptime_hours DOUBLE,
    dbu_rate DOUBLE,
    dbu_per_hour DOUBLE,
    estimated_dbu_cost DOUBLE,
    estimated_monthly_cost DOUBLE,
    process_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, cloud)
LOCATION 'dbfs:/finops/gold/costs/dbu_estimates'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
