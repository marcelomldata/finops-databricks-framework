from pyspark.sql import SparkSession
from pyspark.sql.functions import col, desc
from typing import Dict, List
from datetime import datetime

def generate_executive_report(
    spark: SparkSession,
    workspace_name: str,
    baseline_date: str
) -> Dict:
    from src.auditors.revalidation_auditor import (
        compare_recommendations_status,
        detect_new_resources,
        validate_storage_maintenance,
        validate_compute_usage,
        validate_workflows_pipelines
    )
    from src.auditors.roi_estimator import calculate_total_roi
    from src.analyzers.finops_analyzer import calculate_maturity_score
    
    current_maturity = calculate_maturity_score(spark, workspace_name)
    
    recommendations_status = compare_recommendations_status(spark, workspace_name, baseline_date)
    
    new_resources = detect_new_resources(spark, workspace_name, baseline_date)
    
    storage_issues = validate_storage_maintenance(spark, workspace_name)
    compute_issues = validate_compute_usage(spark, workspace_name)
    workflow_issues = validate_workflows_pipelines(spark, workspace_name)
    
    all_issues = storage_issues + compute_issues + workflow_issues
    
    high_priority_issues = [i for i in all_issues if i.get("severity") == "high"]
    medium_priority_issues = [i for i in all_issues if i.get("severity") == "medium"]
    
    implemented = len([r for r in recommendations_status if r.get("status") == "implementada"])
    not_implemented = len([r for r in recommendations_status if r.get("status") == "não_implementada"])
    regression = len([r for r in recommendations_status if r.get("status") == "regressão"])
    
    roi = calculate_total_roi(spark, workspace_name, high_priority_issues)
    
    report = {
        "workspace_name": workspace_name,
        "report_date": datetime.utcnow().isoformat(),
        "baseline_date": baseline_date,
        "executive_summary": {
            "current_maturity_score": current_maturity.get("maturity_score", 0.0),
            "current_maturity_level": current_maturity.get("maturity_level", "Básico"),
            "total_issues": len(all_issues),
            "high_priority_issues": len(high_priority_issues),
            "medium_priority_issues": len(medium_priority_issues),
            "recommendations_implemented": implemented,
            "recommendations_not_implemented": not_implemented,
            "regressions_detected": regression,
            "estimated_monthly_savings": roi.get("estimated_monthly_savings", 0.0),
            "estimated_annual_savings": roi.get("estimated_annual_savings", 0.0),
            "reduction_percentage": roi.get("reduction_percentage", 0.0)
        },
        "new_resources": {
            "new_clusters": new_resources.get("new_clusters", 0),
            "new_tables": new_resources.get("new_tables", 0),
            "new_jobs": new_resources.get("new_jobs", 0)
        },
        "recommendations_status": recommendations_status,
        "critical_issues": high_priority_issues[:10],
        "roi_analysis": roi,
        "maturity_breakdown": {
            "compute_score": current_maturity.get("compute_score", 0.0),
            "storage_score": current_maturity.get("storage_score", 0.0),
            "governance_score": current_maturity.get("governance_score", 0.0),
            "pipelines_score": current_maturity.get("pipelines_score", 0.0),
            "observability_score": current_maturity.get("observability_score", 0.0),
            "costs_score": current_maturity.get("costs_score", 0.0)
        }
    }
    
    return report

def generate_technical_checklist(
    spark: SparkSession,
    workspace_name: str
) -> List[Dict]:
    from src.auditors.revalidation_auditor import (
        validate_storage_maintenance,
        validate_compute_usage,
        validate_workflows_pipelines
    )
    
    storage_issues = validate_storage_maintenance(spark, workspace_name)
    compute_issues = validate_compute_usage(spark, workspace_name)
    workflow_issues = validate_workflows_pipelines(spark, workspace_name)
    
    checklist = []
    
    for issue in storage_issues + compute_issues + workflow_issues:
        checklist.append({
            "workspace_name": workspace_name,
            "category": issue.get("issue_type", "").split("_")[0],
            "issue_type": issue.get("issue_type", ""),
            "resource_name": issue.get("resource_name") or issue.get("table_name") or issue.get("resource_id", ""),
            "severity": issue.get("severity", ""),
            "description": issue.get("description", ""),
            "recommended_action": issue.get("recommended_action", ""),
            "estimated_impact": issue.get("estimated_impact", ""),
            "status": "pending",
            "validation_timestamp": issue.get("validation_timestamp", datetime.utcnow())
        })
    
    return checklist

def generate_prioritized_backlog(
    spark: SparkSession,
    workspace_name: str
) -> List[Dict]:
    from src.auditors.revalidation_auditor import (
        validate_storage_maintenance,
        validate_compute_usage,
        validate_workflows_pipelines
    )
    from src.auditors.roi_estimator import (
        estimate_cluster_savings,
        estimate_storage_savings,
        estimate_job_optimization_savings
    )
    
    storage_issues = validate_storage_maintenance(spark, workspace_name)
    compute_issues = validate_compute_usage(spark, workspace_name)
    workflow_issues = validate_workflows_pipelines(spark, workspace_name)
    
    backlog = []
    
    for issue in storage_issues:
        if issue.get("severity") == "high":
            savings = estimate_storage_savings(
                spark, 
                workspace_name, 
                issue.get("table_name", ""), 
                "archive_abandoned" if "abandoned" in issue.get("issue_type", "") else "optimize_small_files"
            )
            backlog.append({
                "workspace_name": workspace_name,
                "priority": 1 if issue.get("severity") == "high" else 2,
                "category": "storage",
                "issue": issue.get("description", ""),
                "action": issue.get("recommended_action", ""),
                "estimated_savings_usd_month": savings.get("estimated_monthly_savings", 0.0),
                "estimated_savings_usd_year": savings.get("estimated_annual_savings", 0.0),
                "complexity": "low" if "optimize" in issue.get("recommended_action", "").lower() else "medium",
                "effort_hours": 2 if "optimize" in issue.get("recommended_action", "").lower() else 8
            })
    
    for issue in compute_issues:
        if issue.get("severity") == "high":
            action_type = "terminate_idle" if "idle" in issue.get("issue_type", "") else "enable_autoscaling"
            savings = estimate_cluster_savings(
                spark,
                workspace_name,
                issue.get("resource_id", ""),
                action_type
            )
            backlog.append({
                "workspace_name": workspace_name,
                "priority": 1,
                "category": "compute",
                "issue": issue.get("description", ""),
                "action": issue.get("recommended_action", ""),
                "estimated_savings_usd_month": savings.get("estimated_monthly_savings", 0.0),
                "estimated_savings_usd_year": savings.get("estimated_annual_savings", 0.0),
                "complexity": "low",
                "effort_hours": 1
            })
    
    backlog_sorted = sorted(backlog, key=lambda x: (x["priority"], -x["estimated_savings_usd_month"]))
    
    return backlog_sorted

def generate_quick_wins_alerts(
    spark: SparkSession,
    workspace_name: str
) -> List[Dict]:
    from src.auditors.revalidation_auditor import (
        validate_storage_maintenance,
        validate_compute_usage
    )
    from src.auditors.roi_estimator import (
        estimate_cluster_savings,
        estimate_storage_savings
    )
    
    storage_issues = validate_storage_maintenance(spark, workspace_name)
    compute_issues = validate_compute_usage(spark, workspace_name)
    
    quick_wins = []
    
    for issue in compute_issues:
        if issue.get("severity") == "high" and "idle" in issue.get("issue_type", ""):
            savings = estimate_cluster_savings(
                spark,
                workspace_name,
                issue.get("resource_id", ""),
                "terminate_idle"
            )
            if savings.get("estimated_monthly_savings", 0.0) > 100:
                quick_wins.append({
                    "workspace_name": workspace_name,
                    "alert_type": "quick_win",
                    "category": "compute",
                    "title": f"Cluster {issue.get('resource_name', '')} ocioso",
                    "description": issue.get("description", ""),
                    "action": issue.get("recommended_action", ""),
                    "estimated_savings_usd_month": savings.get("estimated_monthly_savings", 0.0),
                    "estimated_savings_usd_year": savings.get("estimated_annual_savings", 0.0),
                    "effort_hours": 1,
                    "complexity": "low",
                    "urgency": "high"
                })
    
    for issue in storage_issues:
        if issue.get("severity") == "high" and "abandoned" in issue.get("issue_type", ""):
            savings = estimate_storage_savings(
                spark,
                workspace_name,
                issue.get("table_name", ""),
                "delete_abandoned"
            )
            if savings.get("estimated_monthly_savings", 0.0) > 50:
                quick_wins.append({
                    "workspace_name": workspace_name,
                    "alert_type": "quick_win",
                    "category": "storage",
                    "title": f"Tabela {issue.get('table_name', '')} abandonada",
                    "description": issue.get("description", ""),
                    "action": issue.get("recommended_action", ""),
                    "estimated_savings_usd_month": savings.get("estimated_monthly_savings", 0.0),
                    "estimated_savings_usd_year": savings.get("estimated_annual_savings", 0.0),
                    "effort_hours": 4,
                    "complexity": "medium",
                    "urgency": "high"
                })
    
    quick_wins_sorted = sorted(quick_wins, key=lambda x: -x["estimated_savings_usd_month"])
    
    return quick_wins_sorted[:10]
