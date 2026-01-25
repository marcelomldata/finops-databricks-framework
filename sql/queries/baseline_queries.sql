-- Query: Listar Todos os Baselines
SELECT 
    baseline_id,
    baseline_date,
    maturity_score,
    maturity_level,
    estimated_monthly_cost,
    total_clusters,
    total_jobs,
    framework_version
FROM finops_gold.assessment_baselines
WHERE workspace_name = '${workspace_name}'
ORDER BY baseline_date DESC;

-- Query: Comparar Baselines
SELECT 
    b1.baseline_date AS baseline_1_date,
    b1.maturity_score AS baseline_1_score,
    b1.estimated_monthly_cost AS baseline_1_cost,
    b2.baseline_date AS baseline_2_date,
    b2.maturity_score AS baseline_2_score,
    b2.estimated_monthly_cost AS baseline_2_cost,
    (b2.maturity_score - b1.maturity_score) AS score_improvement,
    (b1.estimated_monthly_cost - b2.estimated_monthly_cost) AS cost_reduction,
    ((b1.estimated_monthly_cost - b2.estimated_monthly_cost) / b1.estimated_monthly_cost * 100) AS cost_reduction_percentage
FROM finops_gold.assessment_baselines b1
JOIN finops_gold.assessment_baselines b2
    ON b1.workspace_name = b2.workspace_name
    AND b1.baseline_date < b2.baseline_date
WHERE b1.workspace_name = '${workspace_name}'
    AND b1.baseline_id = '${baseline_id_1}'
    AND b2.baseline_id = '${baseline_id_2}';

-- Query: Custos DBU por Cluster
SELECT 
    cluster_name,
    cluster_type,
    num_workers,
    uptime_hours,
    dbu_rate,
    dbu_per_hour,
    estimated_dbu_cost,
    estimated_monthly_cost
FROM finops_gold.costs_dbu_estimates
WHERE workspace_name = '${workspace_name}'
ORDER BY estimated_monthly_cost DESC;

-- Query: Resumo de Custos DBU
SELECT 
    workspace_name,
    COUNT(*) AS total_clusters,
    SUM(estimated_monthly_cost) AS total_monthly_cost,
    SUM(estimated_dbu_cost) AS total_dbu_cost,
    AVG(dbu_per_hour) AS avg_dbu_per_hour
FROM finops_gold.costs_dbu_estimates
WHERE workspace_name = '${workspace_name}'
GROUP BY workspace_name;

-- Query: Cost Allocation por Domínio
SELECT 
    cost_center,
    business_unit,
    data_domain,
    COUNT(*) AS resource_count,
    SUM(estimated_monthly_cost) AS total_monthly_cost,
    SUM(estimated_dbu_cost) AS total_dbu_cost
FROM finops_gold.cost_allocation
WHERE workspace_name = '${workspace_name}'
GROUP BY cost_center, business_unit, data_domain
ORDER BY total_monthly_cost DESC;

-- Query: Recursos Não Alocados
SELECT 
    resource_type,
    resource_name,
    estimated_monthly_cost
FROM finops_gold.cost_allocation
WHERE workspace_name = '${workspace_name}'
    AND (cost_center = 'unallocated' OR cost_center = '')
ORDER BY estimated_monthly_cost DESC;
