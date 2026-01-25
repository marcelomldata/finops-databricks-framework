from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, abs as spark_abs, round, current_timestamp
from typing import Dict, Optional
from datetime import datetime

def reconcile_dbu_vs_actual(
    spark: SparkSession,
    workspace_name: str,
    actual_cost: Optional[float] = None,
    actual_cost_date: Optional[str] = None
) -> Dict:
    df_dbu_estimates = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    if df_dbu_estimates.count() == 0:
        return {
            "workspace_name": workspace_name,
            "reconciliation_status": "no_data",
            "confidence": "low"
        }
    
    estimated_monthly = df_dbu_estimates.agg({"estimated_monthly_cost": "sum"}).collect()[0][0] or 0.0
    
    if actual_cost is None:
        try:
            df_billing = spark.read.format("delta").load("dbfs:/finops/gold/billing_costs_summary") \
                .filter(col("workspace_name") == workspace_name) \
                .orderBy(col("date_parsed").desc()) \
                .limit(30)
            
            if df_billing.count() > 0:
                actual_cost = df_billing.agg({"daily_cost_usd": "sum"}).collect()[0][0] or 0.0
                actual_cost = actual_cost * 30 / df_billing.count()
        except:
            actual_cost = None
    
    if actual_cost is None or actual_cost == 0:
        return {
            "workspace_name": workspace_name,
            "estimated_monthly_cost": round(estimated_monthly, 2),
            "actual_cost": None,
            "reconciliation_status": "estimated_only",
            "variance_percentage": None,
            "confidence": "medium",
            "recommendation": "Integrar billing real para maior precisão"
        }
    
    variance = abs(estimated_monthly - actual_cost)
    variance_percentage = (variance / actual_cost * 100) if actual_cost > 0 else 0.0
    
    if variance_percentage < 5:
        confidence = "high"
        status = "reconciled"
    elif variance_percentage < 15:
        confidence = "medium"
        status = "close"
    else:
        confidence = "low"
        status = "needs_review"
    
    return {
        "workspace_name": workspace_name,
        "estimated_monthly_cost": round(estimated_monthly, 2),
        "actual_cost": round(actual_cost, 2),
        "variance": round(variance, 2),
        "variance_percentage": round(variance_percentage, 2),
        "reconciliation_status": status,
        "confidence": confidence,
        "reconciliation_date": actual_cost_date or datetime.utcnow().isoformat(),
        "recommendation": "Billing real integrado" if confidence == "high" else "Revisar estimativas ou integrar billing real"
    }

def calculate_roi_confidence(
    spark: SparkSession,
    workspace_name: str,
    estimated_savings: float
) -> Dict:
    reconciliation = reconcile_dbu_vs_actual(spark, workspace_name)
    
    base_confidence = {
        "high": 0.9,
        "medium": 0.7,
        "low": 0.5
    }.get(reconciliation.get("confidence", "low"), 0.5)
    
    if reconciliation.get("variance_percentage"):
        variance_penalty = min(reconciliation["variance_percentage"] / 100, 0.3)
        base_confidence = max(base_confidence - variance_penalty, 0.3)
    
    roi_confidence = base_confidence
    
    if estimated_savings > 10000:
        roi_confidence = min(roi_confidence + 0.1, 1.0)
    elif estimated_savings < 100:
        roi_confidence = max(roi_confidence - 0.1, 0.3)
    
    return {
        "workspace_name": workspace_name,
        "estimated_savings": estimated_savings,
        "roi_confidence": round(roi_confidence, 2),
        "confidence_level": "high" if roi_confidence >= 0.8 else "medium" if roi_confidence >= 0.6 else "low",
        "reconciliation_status": reconciliation.get("reconciliation_status"),
        "variance_percentage": reconciliation.get("variance_percentage"),
        "recommendation": "ROI confiável" if roi_confidence >= 0.8 else "Revisar estimativas antes de apresentar ROI"
    }
