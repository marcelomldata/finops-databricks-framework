CREATE DATABASE IF NOT EXISTS finops_gold;

CREATE TABLE IF NOT EXISTS finops_gold.revalidation_executive_reports (
    workspace_name STRING,
    report_date STRING,
    baseline_date STRING,
    executive_summary STRUCT<
        current_maturity_score: DOUBLE,
        current_maturity_level: STRING,
        total_issues: INT,
        high_priority_issues: INT,
        medium_priority_issues: INT,
        recommendations_implemented: INT,
        recommendations_not_implemented: INT,
        regressions_detected: INT,
        estimated_monthly_savings: DOUBLE,
        estimated_annual_savings: DOUBLE,
        reduction_percentage: DOUBLE
    >,
    new_resources STRUCT<
        new_clusters: INT,
        new_tables: INT,
        new_jobs: INT
    >,
    recommendations_status ARRAY<STRUCT<
        workspace_name: STRING,
        recommendation_title: STRING,
        category: STRING,
        priority: STRING,
        status: STRING,
        baseline_date: STRING,
        validation_timestamp: TIMESTAMP
    >>,
    critical_issues ARRAY<STRUCT<
        workspace_name: STRING,
        issue_type: STRING,
        table_name: STRING,
        resource_id: STRING,
        resource_name: STRING,
        severity: STRING,
        description: STRING,
        recommended_action: STRING,
        estimated_impact: STRING,
        validation_timestamp: TIMESTAMP
    >>,
    roi_analysis STRUCT<
        workspace_name: STRING,
        current_monthly_cost: DOUBLE,
        estimated_monthly_cost: DOUBLE,
        estimated_monthly_savings: DOUBLE,
        estimated_annual_savings: DOUBLE,
        reduction_percentage: DOUBLE,
        confidence: STRING,
        margin_of_error: STRING,
        calculation_timestamp: TIMESTAMP
    >,
    maturity_breakdown STRUCT<
        compute_score: DOUBLE,
        storage_score: DOUBLE,
        governance_score: DOUBLE,
        pipelines_score: DOUBLE,
        observability_score: DOUBLE,
        costs_score: DOUBLE
    >
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/revalidation/executive_reports'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.revalidation_technical_checklist (
    workspace_name STRING,
    category STRING,
    issue_type STRING,
    resource_name STRING,
    severity STRING,
    description STRING,
    recommended_action STRING,
    estimated_impact STRING,
    status STRING,
    validation_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (workspace_name, category)
LOCATION 'dbfs:/finops/gold/revalidation/technical_checklist'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.revalidation_prioritized_backlog (
    workspace_name STRING,
    priority INT,
    category STRING,
    issue STRING,
    action STRING,
    estimated_savings_usd_month DOUBLE,
    estimated_savings_usd_year DOUBLE,
    complexity STRING,
    effort_hours DOUBLE
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/revalidation/prioritized_backlog'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

CREATE TABLE IF NOT EXISTS finops_gold.revalidation_quick_wins (
    workspace_name STRING,
    alert_type STRING,
    category STRING,
    title STRING,
    description STRING,
    action STRING,
    estimated_savings_usd_month DOUBLE,
    estimated_savings_usd_year DOUBLE,
    effort_hours DOUBLE,
    complexity STRING,
    urgency STRING
)
USING DELTA
PARTITIONED BY (workspace_name)
LOCATION 'dbfs:/finops/gold/revalidation/quick_wins'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
