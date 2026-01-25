from pyspark.sql import SparkSession
from src.auditors.report_generator import (
    generate_executive_report,
    generate_technical_checklist,
    generate_prioritized_backlog,
    generate_quick_wins_alerts
)
import os
from datetime import datetime, timedelta

spark = SparkSession.builder.appName("FinOps_Revalidation").getOrCreate()

workspace_name = os.getenv("WORKSPACE_NAME", "default_workspace")
baseline_days = int(os.getenv("BASELINE_DAYS", "30"))
baseline_date = (datetime.utcnow() - timedelta(days=baseline_days)).isoformat()

print(f"Iniciando revalidação para {workspace_name}")
print(f"Baseline date: {baseline_date}")

executive_report = generate_executive_report(spark, workspace_name, baseline_date)

df_report = spark.createDataFrame([executive_report])
df_report.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .save("dbfs:/finops/gold/revalidation/executive_reports")

print("\n=== RELATÓRIO EXECUTIVO ===")
print(f"Maturity Score: {executive_report['executive_summary']['current_maturity_score']:.2f}")
print(f"Nível: {executive_report['executive_summary']['current_maturity_level']}")
print(f"Issues Críticas: {executive_report['executive_summary']['high_priority_issues']}")
print(f"Economia Mensal Estimada: ${executive_report['executive_summary']['estimated_monthly_savings']:.2f}")
print(f"Economia Anual Estimada: ${executive_report['executive_summary']['estimated_annual_savings']:.2f}")
print(f"Redução Percentual: {executive_report['executive_summary']['reduction_percentage']:.2f}%")

technical_checklist = generate_technical_checklist(spark, workspace_name)

if technical_checklist:
    df_checklist = spark.createDataFrame(technical_checklist)
    df_checklist.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/revalidation/technical_checklist")
    
    print(f"\n=== CHECKLIST TÉCNICO ===")
    print(f"Total de itens: {len(technical_checklist)}")
    high_priority = len([c for c in technical_checklist if c.get("severity") == "high"])
    print(f"Alta prioridade: {high_priority}")

prioritized_backlog = generate_prioritized_backlog(spark, workspace_name)

if prioritized_backlog:
    df_backlog = spark.createDataFrame(prioritized_backlog)
    df_backlog.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/revalidation/prioritized_backlog")
    
    print(f"\n=== BACKLOG PRIORIZADO ===")
    print(f"Total de itens: {len(prioritized_backlog)}")
    total_savings = sum([b.get("estimated_savings_usd_year", 0.0) for b in prioritized_backlog])
    print(f"Economia anual total estimada: ${total_savings:.2f}")

quick_wins = generate_quick_wins_alerts(spark, workspace_name)

if quick_wins:
    df_quick_wins = spark.createDataFrame(quick_wins)
    df_quick_wins.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .save("dbfs:/finops/gold/revalidation/quick_wins")
    
    print(f"\n=== QUICK WINS ===")
    print(f"Total de quick wins: {len(quick_wins)}")
    for qw in quick_wins[:5]:
        print(f"  - {qw['title']}: ${qw['estimated_savings_usd_month']:.2f}/mês")

print("\nRevalidação concluída")
