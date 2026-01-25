from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, current_timestamp
from typing import Dict, List
from datetime import datetime
import os

def generate_safe_automation_actions(
    spark: SparkSession,
    workspace_name: str,
    automation_level: str = "alert"
) -> List[Dict]:
    actions = []
    
    df_clusters = spark.read.format("delta").load("dbfs:/finops/gold/compute/clusters_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    idle_clusters = df_clusters.filter(
        (col("is_idle") == True) &
        (col("idle_hours") > 4)
    ).collect()
    
    for cluster in idle_clusters:
        action = {
            "workspace_name": workspace_name,
            "resource_type": "cluster",
            "resource_id": cluster.cluster_id,
            "resource_name": cluster.cluster_name,
            "action_type": "terminate_idle",
            "automation_level": automation_level,
            "condition": f"idle_hours > {cluster.idle_hours:.1f}",
            "estimated_savings": cluster.idle_hours * 0.5,
            "risk_level": "low",
            "requires_approval": automation_level == "alert",
            "action_command": f"databricks clusters delete --cluster-id {cluster.cluster_id}",
            "rollback_command": f"databricks clusters start --cluster-id {cluster.cluster_id}",
            "generated_at": datetime.utcnow()
        }
        
        if automation_level == "auto" and cluster.idle_hours > 8:
            action["requires_approval"] = False
            action["can_execute"] = True
        else:
            action["can_execute"] = False
            action["alert_message"] = f"Cluster {cluster.cluster_name} está ocioso há {cluster.idle_hours:.1f} horas. Considere desligar."
        
        actions.append(action)
    
    return actions

def generate_automation_alerts(
    spark: SparkSession,
    workspace_name: str
) -> List[Dict]:
    actions = generate_safe_automation_actions(spark, workspace_name, "alert")
    
    alerts = []
    for action in actions:
        alerts.append({
            "workspace_name": workspace_name,
            "alert_type": "automation_opportunity",
            "severity": "medium",
            "title": f"Oportunidade de Automação: {action['action_type']}",
            "description": action.get("alert_message", ""),
            "resource_id": action["resource_id"],
            "resource_name": action["resource_name"],
            "action_available": True,
            "action_command": action["action_command"],
            "estimated_savings": action["estimated_savings"],
            "risk_level": action["risk_level"],
            "requires_approval": action["requires_approval"],
            "generated_at": action["generated_at"]
        })
    
    return alerts
