import os
import re
from typing import Dict, Optional

def detect_cloud_from_url(workspace_url: str) -> str:
    if "azuredatabricks.net" in workspace_url or "adb-" in workspace_url:
        return "azure"
    elif "gcp.databricks.com" in workspace_url:
        return "gcp"
    elif "cloud.databricks.com" in workspace_url:
        return "aws"
    else:
        raise ValueError(f"Cloud não identificada para URL: {workspace_url}")

def detect_metastore_type(spark) -> str:
    try:
        spark.sql("SHOW CATALOGS").collect()
        return "unity_catalog"
    except:
        try:
            spark.sql("SHOW DATABASES").collect()
            return "hive"
        except:
            return "unknown"

def get_workspace_id_from_url(workspace_url: str) -> str:
    pattern = r'https://([^.]+)\.(?:azuredatabricks\.net|cloud\.databricks\.com|gcp\.databricks\.com)'
    match = re.search(pattern, workspace_url)
    if match:
        return match.group(1)
    raise ValueError(f"Não foi possível extrair workspace_id de: {workspace_url}")

def get_cloud_config(cloud: str) -> Dict:
    configs = {
        "azure": {
            "billing_api": "azure_cost_management",
            "metrics_api": "azure_monitor",
            "storage_account_pattern": "dbfs"
        },
        "aws": {
            "billing_api": "aws_cost_explorer",
            "metrics_api": "cloudwatch",
            "storage_account_pattern": "s3"
        },
        "gcp": {
            "billing_api": "gcp_billing",
            "metrics_api": "gcp_monitoring",
            "storage_account_pattern": "gs"
        }
    }
    return configs.get(cloud, {})
