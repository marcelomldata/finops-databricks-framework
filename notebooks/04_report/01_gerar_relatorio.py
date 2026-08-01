"""
04 — Gera o RELATÓRIO técnico + matriz de priorização (Fase 2).

Lê as tabelas gold (custo real da Fase 1 + maturity/recomendações), costura o
relatório e grava Markdown + HTML. O HTML abre no navegador e exporta PDF.

Pré-requisito: ter rodado antes o `00_collect_system_tables` (Fase 1) e, se
quiser scores/recomendações, os notebooks 03_analyze.
"""
from pyspark.sql import SparkSession
from src.reporting.relatorio import gerar_relatorio
import os

spark = SparkSession.builder.appName("FinOps_Relatorio").getOrCreate()

workspace = os.getenv("WORKSPACE_NAME", "workspace")
dias = int(os.getenv("FINOPS_DIAS", "30"))
moeda = os.getenv("FINOPS_MOEDA", "USD")
destino = os.getenv("FINOPS_RELATORIOS", "dbfs:/finops/relatorios")

r = gerar_relatorio(spark, workspace=workspace, dias=dias, moeda=moeda)

# Grava arquivo ÚNICO (não diretório de part-files) via dbutils — disponível no
# notebook. Se rodar fora do Databricks (sem dbutils), só imprime.
caminho_md = f"{destino}/relatorio_{workspace}.md"
caminho_html = f"{destino}/relatorio_{workspace}.html"
try:
    dbutils.fs.put(caminho_md, r["md"], overwrite=True)      # noqa: F821 (global do notebook)
    dbutils.fs.put(caminho_html, r["html"], overwrite=True)  # noqa: F821
    print(f"Relatório gravado:\n  - {caminho_md}\n  - {caminho_html}")
except NameError:
    print("(dbutils indisponível — imprimindo o relatório sem gravar)")

print("\n" + "=" * 70)
print(r["md"])
