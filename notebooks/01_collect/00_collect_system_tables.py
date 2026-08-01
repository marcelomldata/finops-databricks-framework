"""
00 — Coleta de CUSTO REAL via system tables (Fase 1).

A nova porta de entrada do assessment. Diferente dos notebooks 01/02/03 (que
chamam a REST API e precisam de WORKSPACE_URL + DATABRICKS_TOKEN), este só faz
query nas system tables do Unity Catalog — não precisa de token nem de host.

Grava as tabelas gold de custo MEDIDO:
- gold/costs/real_usage       : custo real (moeda) e DBU por recurso e dia
- gold/costs/by_job           : custo por job (job/serverless compute)
- gold/compute/utilization    : utilização/idle por cluster (right-sizing, 90d)
- gold/costs/serverless_by_tag: custo serverless por unidade de negócio (se TAG_NEGOCIO)

Pré-requisito: Unity Catalog + os system schemas billing/compute/lakeflow
habilitados e com SELECT concedido (ver RUNBOOK_FASE1.md).
"""
from pyspark.sql import SparkSession
from src.analyzers.real_cost import system_tables_disponiveis, materializar_gold
import os

spark = SparkSession.builder.appName("FinOps_Collect_SystemTables").getOrCreate()

dias = int(os.getenv("FINOPS_DIAS", "30"))
moeda = os.getenv("FINOPS_MOEDA", "USD")
tag_negocio = os.getenv("FINOPS_TAG_NEGOCIO") or None

# Preflight explícito das QUATRO system tables: se faltar acesso, falha com o que
# fazer, em vez do erro cru do Spark no meio do pipeline.
ok, msg = system_tables_disponiveis(spark)
if not ok:
    raise RuntimeError(msg)
print(f"[system tables] {msg}")

resultado = materializar_gold(spark, dias=dias, moeda=moeda, tag_negocio=tag_negocio)
gravado, erros = resultado["gravado"], resultado["erros"]

print(f"\nCusto REAL coletado (janela: {dias} dias fechados, moeda: {moeda}):")
for tabela, linhas in gravado.items():
    print(f"  - {tabela}: {linhas} linhas")
for tabela, err in erros.items():
    print(f"  ⚠ {tabela}: FALHOU — {err}")

if sum(gravado.values()) == 0:
    print(
        "\n⚠ Tudo zerado — provavelmente NÃO é bug. Causas comuns:\n"
        "  1. Workspace novo: system.billing.usage tem latência de ingestão (horas a ~1 dia).\n"
        "  2. Nenhuma carga rodada ainda no workspace.\n"
        "  3. node_timeline retém só 90 dias.\n"
        "  Rode num workspace com >=24-48h de uso REAL para ver números."
    )
if not tag_negocio:
    print("\n  (defina FINOPS_TAG_NEGOCIO=<chave> para atribuir custo serverless por tag)")

print(
    "\nLIMITAÇÕES DO NÚMERO (declare no relatório — ele NÃO fecha com a fatura Azure sem isto):\n"
    "  - Custo = DBU do Databricks a PREÇO DE LISTA (effective_list). NÃO inclui a VM/compute,\n"
    "    storage e rede da cloud — o Azure fatura à parte; o total costuma ser ~2x o DBU.\n"
    "  - Não reflete descontos de commit/negociados nem câmbio (list_prices em USD).\n"
    "  - Custo por job só cobre job/serverless compute; all-purpose não popula job_id.\n"
    "  - Coluna 'dbus_sem_preco' em real_usage = DBU sem preço casado (cobertura)."
)
