from pyspark.sql import SparkSession
from src.utils.baseline_manager import create_baseline
from src.utils.cloud_detector import detect_cloud_from_url
import os

spark = SparkSession.builder.appName("FinOps_Create_Baseline").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
workspace_url = os.getenv("WORKSPACE_URL")
framework_version = os.getenv("FRAMEWORK_VERSION", "1.0.0")

if not workspace_url:
    raise ValueError("WORKSPACE_URL é obrigatório")

cloud = detect_cloud_from_url(workspace_url)

context = {
    "primary_use_case": os.getenv("PRIMARY_USE_CASE", ""),
    "team_size": int(os.getenv("TEAM_SIZE", "0")),
    "notes": os.getenv("BASELINE_NOTES", "")
}

print(f"Criando baseline para {workspace_name}...")

baseline_id = create_baseline(
    spark=spark,
    workspace_name=workspace_name,
    cloud=cloud,
    framework_version=framework_version,
    context=context
)

print(f"Baseline criado: {baseline_id}")
print(f"Consulte em: SELECT * FROM finops_gold.assessment_baselines WHERE baseline_id = '{baseline_id}'")
