-- Query: Relatório Executivo Mais Recente
SELECT 
    workspace_name,
    report_date,
    executive_summary.current_maturity_score,
    executive_summary.current_maturity_level,
    executive_summary.total_issues,
    executive_summary.high_priority_issues,
    executive_summary.estimated_monthly_savings,
    executive_summary.estimated_annual_savings,
    executive_summary.reduction_percentage
FROM finops_gold.revalidation_executive_reports
WHERE workspace_name = '${workspace_name}'
ORDER BY report_date DESC
LIMIT 1;

-- Query: Status de Recomendações
SELECT 
    recommendation_title,
    category,
    priority,
    status,
    validation_timestamp
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(recommendations_status) AS rec
WHERE workspace_name = '${workspace_name}'
ORDER BY 
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    validation_timestamp DESC;

-- Query: Quick Wins
SELECT 
    title,
    category,
    description,
    action,
    estimated_savings_usd_month,
    estimated_savings_usd_year,
    effort_hours,
    complexity
FROM finops_gold.revalidation_quick_wins
WHERE workspace_name = '${workspace_name}'
ORDER BY estimated_savings_usd_month DESC;

-- Query: Backlog Priorizado
SELECT 
    priority,
    category,
    issue,
    action,
    estimated_savings_usd_month,
    estimated_savings_usd_year,
    complexity,
    effort_hours
FROM finops_gold.revalidation_prioritized_backlog
WHERE workspace_name = '${workspace_name}'
ORDER BY priority ASC, estimated_savings_usd_month DESC;

-- Query: Checklist Técnico por Categoria
SELECT 
    category,
    severity,
    issue_type,
    resource_name,
    description,
    recommended_action,
    estimated_impact,
    status
FROM finops_gold.revalidation_technical_checklist
WHERE workspace_name = '${workspace_name}'
    AND category = '${category}'
ORDER BY 
    CASE severity
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END;

-- Query: ROI Analysis
SELECT 
    workspace_name,
    current_monthly_cost,
    estimated_monthly_cost,
    estimated_monthly_savings,
    estimated_annual_savings,
    reduction_percentage,
    confidence,
    margin_of_error
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(ARRAY(roi_analysis)) AS roi
WHERE workspace_name = '${workspace_name}'
ORDER BY report_date DESC
LIMIT 1;

-- Query: Novos Recursos Detectados
SELECT 
    new_resources.new_clusters AS new_clusters,
    new_resources.new_tables AS new_tables,
    new_resources.new_jobs AS new_jobs,
    report_date
FROM finops_gold.revalidation_executive_reports
WHERE workspace_name = '${workspace_name}'
ORDER BY report_date DESC
LIMIT 1;

-- Query: Issues Críticas
SELECT 
    issue.issue_type,
    issue.resource_name,
    issue.severity,
    issue.description,
    issue.recommended_action,
    issue.estimated_impact
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(critical_issues) AS issue
WHERE workspace_name = '${workspace_name}'
ORDER BY report_date DESC
LIMIT 20;
