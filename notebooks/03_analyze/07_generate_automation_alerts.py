from pyspark.sql import SparkSession
from src.utils.safe_automation import generate_automation_alerts
import os

spark = SparkSession.builder.appName("FinOps_Generate_Automation_Alerts").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")

print(f"Gerando alertas de automação para {workspace_name}...")

alerts = generate_automation_alerts(spark, workspace_name)

if alerts:
    df_alerts = spark.createDataFrame(alerts)
    df_alerts.write \
        .format("delta") \
        .mode("append") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/automation_actions")
    
    print(f"\n=== ALERTAS DE AUTOMAÇÃO ===")
    print(f"Total de alertas: {len(alerts)}")
    for alert in alerts[:5]:
        print(f"\n{alert['title']}")
        print(f"  Recurso: {alert['resource_name']}")
        print(f"  Economia estimada: ${alert['estimated_savings']:.2f}/mês")
        print(f"  Risco: {alert['risk_level']}")
        print(f"  Requer aprovação: {alert['requires_approval']}")
else:
    print("Nenhum alerta de automação gerado")
