from pyspark.sql import SparkSession
from src.collectors.billing_collector import collect_billing_azure, collect_billing_aws, collect_billing_gcp
from src.utils.cloud_detector import detect_cloud_from_url
import os

spark = SparkSession.builder.appName("FinOps_Collect_Billing").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
workspace_url = os.getenv("WORKSPACE_URL")
cloud = detect_cloud_from_url(workspace_url)

if not workspace_url:
    raise ValueError("WORKSPACE_URL é obrigatório")

days_back = int(os.getenv("BILLING_DAYS_BACK", "30"))

if cloud == "azure":
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        raise ValueError("AZURE_SUBSCRIPTION_ID é obrigatório para Azure")
    collect_billing_azure(
        spark=spark,
        workspace_name=workspace_name,
        workspace_url=workspace_url,
        subscription_id=subscription_id,
        days_back=days_back
    )
elif cloud == "aws":
    region = os.getenv("AWS_REGION", "us-east-1")
    collect_billing_aws(
        spark=spark,
        workspace_name=workspace_name,
        workspace_url=workspace_url,
        region=region,
        days_back=days_back
    )
elif cloud == "gcp":
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID é obrigatório para GCP")
    collect_billing_gcp(
        spark=spark,
        workspace_name=workspace_name,
        workspace_url=workspace_url,
        project_id=project_id,
        days_back=days_back
    )

print(f"Coleta de métricas de billing concluída para {workspace_name} ({cloud})")
