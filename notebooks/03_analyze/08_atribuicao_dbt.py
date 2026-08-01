"""
08 — Atribuição de custo por modelo dbt + tendência interna (Fase 1a / Tier 1).

O diferencial: custo por MODELO dbt (não só por warehouse), cruzando
`system.query.history` (task-time por query + o node_id do comentário dbt) com o
custo do warehouse por hora do billing. E a tendência período-vs-período.

⚠ `system.query.history` é Public Preview e só cobre query de SQL warehouse/
serverless (all-purpose clássico não aparece). Custo por query é ATRIBUIÇÃO
(estimativa), não medição — o idle do warehouse entra rateado. Precisa de SELECT
em `system.query.history` (grant do account admin).

Grava:
- gold/attribution/custo_por_modelo_dbt : custo atribuído por modelo (+ não-atribuído)
- gold/attribution/tendencia            : custo/DBU período atual vs anterior, por SKU
"""
from pyspark.sql import SparkSession
from src.analyzers.attribution import materializar_atribuicao
import os

spark = SparkSession.builder.appName("FinOps_Atribuicao").getOrCreate()

dias = int(os.getenv("FINOPS_DIAS", "30"))
moeda = os.getenv("FINOPS_MOEDA", "USD")

r = materializar_atribuicao(spark, dias=dias, moeda=moeda)

print(f"Atribuição/tendência (janela: {dias} dias, moeda: {moeda}):")
for tabela, linhas in r["gravado"].items():
    print(f"  - {tabela}: {linhas} linhas")
for tabela, err in r["erros"].items():
    print(f"  ⚠ {tabela}: FALHOU — {err}")

if "gold/attribution/custo_por_modelo_dbt" in r["erros"]:
    print("\n  (custo por modelo dbt precisa de system.query.history liberado + queries em "
          "SQL warehouse/serverless com o comentário do dbt. A tendência não depende disso.)")

print("\nLIMITAÇÃO: custo por modelo é ATRIBUÍDO (estimativa) — distribui o custo do warehouse "
      "por task-time; o overhead/idle entra rateado; query sem node_id vai para '(não-atribuído)'. "
      "É comparável entre modelos, não é 'esta query custou exatamente X'.")
