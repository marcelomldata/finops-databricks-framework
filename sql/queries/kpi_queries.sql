-- KPI: Top 10 Clusters Mais Caros
SELECT 
    workspace_name,
    cluster_name,
    cluster_id,
    num_workers,
    memory_gb,
    uptime_hours,
    idle_hours,
    utilization_score,
    is_idle,
    is_overprovisioned
FROM finops_gold.compute_clusters_summary
WHERE workspace_name = '${workspace_name}'
ORDER BY uptime_hours DESC, memory_gb DESC
LIMIT 10;

-- KPI: Jobs Menos Eficientes
SELECT 
    workspace_name,
    job_name,
    job_id,
    total_runs,
    successful_runs,
    failed_runs,
    success_rate,
    failure_rate,
    avg_duration_hours,
    efficiency_score
FROM finops_gold.compute_jobs_summary
WHERE workspace_name = '${workspace_name}'
    AND total_runs > 10
ORDER BY failure_rate DESC, avg_duration_hours DESC
LIMIT 20;

-- KPI: Tabelas Candidatas a Arquivamento
SELECT 
    workspace_name,
    full_table_name,
    size_gb,
    size_tb,
    days_since_accessed,
    days_since_modified,
    is_cold_data,
    is_abandoned,
    storage_tier,
    optimization_priority,
    estimated_savings_gb
FROM finops_gold.storage_tables_summary
WHERE workspace_name = '${workspace_name}'
    AND (is_abandoned = true OR is_cold_data = true)
ORDER BY size_gb DESC
LIMIT 50;

-- KPI: Resumo de Storage por Workspace
SELECT 
    workspace_name,
    total_tables,
    total_size_tb,
    cold_size_tb,
    abandoned_size_tb,
    small_files_size_tb,
    cold_data_percentage,
    abandoned_data_percentage,
    avg_file_size_mb
FROM finops_gold.storage_workspace_summary
WHERE workspace_name = '${workspace_name}';

-- KPI: Custos Diários
SELECT 
    workspace_name,
    date_parsed,
    daily_cost_usd,
    monthly_cost_usd,
    avg_daily_cost_usd
FROM finops_gold.billing_costs_summary
WHERE workspace_name = '${workspace_name}'
    AND date_parsed >= CURRENT_DATE - INTERVAL 30 DAYS
ORDER BY date_parsed DESC;

-- KPI: Maturity Score
SELECT 
    workspace_name,
    maturity_score,
    maturity_level,
    compute_score,
    storage_score,
    governance_score,
    pipelines_score,
    observability_score,
    costs_score,
    process_timestamp
FROM finops_gold.maturity_scores
WHERE workspace_name = '${workspace_name}'
ORDER BY process_timestamp DESC
LIMIT 1;

-- KPI: Recomendações por Prioridade
SELECT 
    workspace_name,
    category,
    priority,
    title,
    description,
    impact,
    complexity,
    action,
    estimated_savings
FROM finops_gold.recommendations
WHERE workspace_name = '${workspace_name}'
ORDER BY 
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    category;
