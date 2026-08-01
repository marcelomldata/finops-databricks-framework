"""
00 — Coleta de CUSTO REAL via system tables (Fase 1).

A nova porta de entrada do assessment. Diferente dos notebooks 01/02/03 (que
chamam a REST API e precisam de WORKSPACE_URL + DATABRICKS_TOKEN), este só faz
query nas system tables do Unity Catalog — não precisa de token nem de host.

Grava as tabelas gold de custo MEDIDO:
- gold/costs/real_usage      : custo real (moeda) e DBU por recurso e dia
- gold/costs/by_job          : custo por job (job/serverless compute)
- gold/compute/utilization   : utilização/idle por cluster (right-sizing, 90d)
- gold/costs/serverless_by_tag : custo serverless por unidade de negócio (se TAG_NEGOCIO)

Pré-requisito: Unity Catalog + SELECT nas system tables (ver README / PLANO_DE_ACAO).
"""
from pyspark.sql import SparkSession
from src.analyzers.real_cost import system_tables_disponiveis, materializar_gold
import os

spark = SparkSession.builder.appName("FinOps_Collect_SystemTables").getOrCreate()

# Janela e moeda por env (com defaults sãos). TAG_NEGOCIO é opcional: a chave de
# custom_tags pela qual atribuir o gasto serverless (ex.: "cost_center").
dias = int(os.getenv("FINOPS_DIAS", "30"))
moeda = os.getenv("FINOPS_MOEDA", "USD")
tag_negocio = os.getenv("FINOPS_TAG_NEGOCIO") or None

# Preflight explícito: se as system tables não estão acessíveis, falha com uma
# mensagem que diz O QUE FAZER, em vez do erro cru do Spark.
ok, msg = system_tables_disponiveis(spark)
if not ok:
    raise RuntimeError(msg)
print(f"[system tables] {msg}")

resumo = materializar_gold(spark, dias=dias, moeda=moeda, tag_negocio=tag_negocio)

print(f"Custo REAL coletado (janela: {dias} dias, moeda: {moeda}):")
for tabela, linhas in resumo.items():
    print(f"  - {tabela}: {linhas} linhas")
if not tag_negocio:
    print("  (defina FINOPS_TAG_NEGOCIO=<chave> para atribuir custo serverless por tag)")
