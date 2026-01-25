-- Query: Reconcilição de Billing
SELECT 
    workspace_name,
    reconciliation_date,
    estimated_monthly_cost,
    actual_cost,
    variance,
    variance_percentage,
    reconciliation_status,
    confidence,
    recommendation
FROM finops_gold.billing_reconciliation
WHERE workspace_name = '${workspace_name}'
ORDER BY reconciliation_date DESC
LIMIT 1;

-- Query: Cost Allocation por Produto
SELECT 
    product_name,
    COUNT(*) AS pipeline_count,
    SUM(estimated_monthly_cost) AS total_monthly_cost,
    AVG(cost_per_run) AS avg_cost_per_run,
    SUM(total_runs_monthly) AS total_runs
FROM finops_gold.cost_allocation_pipelines
WHERE workspace_name = '${workspace_name}'
GROUP BY product_name
ORDER BY total_monthly_cost DESC;

-- Query: Cost Allocation por SLA
SELECT 
    sla_tier,
    COUNT(*) AS pipeline_count,
    SUM(estimated_monthly_cost) AS total_monthly_cost,
    AVG(avg_duration_hours) AS avg_duration
FROM finops_gold.cost_allocation_pipelines
WHERE workspace_name = '${workspace_name}'
GROUP BY sla_tier
ORDER BY total_monthly_cost DESC;

-- Query: Alertas de Automação
SELECT 
    resource_name,
    action_type,
    estimated_savings,
    risk_level,
    requires_approval,
    action_command
FROM finops_gold.automation_actions
WHERE workspace_name = '${workspace_name}'
    AND executed = false
ORDER BY estimated_savings DESC;

-- Query: Benchmarks
SELECT 
    benchmark_date,
    cost_per_tb,
    cost_per_tb_level,
    cluster_utilization,
    utilization_level,
    job_success_rate,
    success_rate_level,
    cold_data_percentage,
    cold_data_level,
    overall_score,
    overall_level
FROM finops_gold.benchmarks
WHERE workspace_name = '${workspace_name}'
ORDER BY benchmark_date DESC
LIMIT 1;

-- Query: Comparar com Benchmark
SELECT 
    b.cost_per_tb AS meu_custo_por_tb,
    b.cost_per_tb_level,
    CASE 
        WHEN b.cost_per_tb_level = 'excellent' THEN 'Top 10% da indústria'
        WHEN b.cost_per_tb_level = 'good' THEN 'Top 25% da indústria'
        WHEN b.cost_per_tb_level = 'average' THEN 'Mediana da indústria'
        ELSE 'Abaixo da mediana'
    END AS interpretacao
FROM finops_gold.benchmarks b
WHERE b.workspace_name = '${workspace_name}'
ORDER BY b.benchmark_date DESC
LIMIT 1;

-- Query: ROI com Confiança
SELECT 
    r.workspace_name,
    r.estimated_monthly_cost,
    r.actual_cost,
    r.variance_percentage,
    r.confidence,
    CASE 
        WHEN r.confidence = 'high' THEN 'ROI confiável para apresentação executiva'
        WHEN r.confidence = 'medium' THEN 'ROI aceitável, revisar antes de apresentar'
        ELSE 'ROI requer validação adicional'
    END AS roi_recommendation
FROM finops_gold.billing_reconciliation r
WHERE r.workspace_name = '${workspace_name}'
ORDER BY r.reconciliation_date DESC
LIMIT 1;

-- Query: Top Pipelines por Custo
SELECT 
    pipeline_name,
    product_name,
    sla_tier,
    estimated_monthly_cost,
    cost_per_run,
    total_runs_monthly,
    avg_duration_hours
FROM finops_gold.cost_allocation_pipelines
WHERE workspace_name = '${workspace_name}'
ORDER BY estimated_monthly_cost DESC
LIMIT 20;
