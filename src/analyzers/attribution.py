"""
Camada de ATRIBUIÇÃO + benchmark interno (Fase 1a / Tier 1 do roadmap).

O diferencial que o painel cravou: "todo mundo tem dashboard de custo por warehouse;
quase ninguém atribui custo por PIPELINE/MODELO com precisão de query-tag". A Fase 1
já dá custo por JOB (usage_metadata.job_id) e por TAG. Aqui vem o granular:

1. **Custo por modelo dbt** — cruza `system.query.history` (task time por query + o
   `node_id` que o dbt injeta no comentário) com o custo do warehouse por hora
   (`system.billing.usage` × preço), alocando por FRAÇÃO DE TASK-TIME dentro da hora.
2. **Tendência interna** — período vs período anterior (não peer-benchmark, que a
   mldata não tem; é comparação interna honesta).

⚠ RESSALVAS (declarar no relatório — schema verificado contra a doc oficial 2026):
- `system.query.history` é **Public Preview**; só popula queries de **SQL warehouse /
  serverless** (query em cluster all-purpose clássico NÃO aparece).
- Custo por query é **ATRIBUIÇÃO/ESTIMATIVA, não medição**: distribui TODO o custo do
  warehouse na hora por task-time — o overhead/idle entra rateado (a soma fecha com a
  fatura do warehouse, mas nenhuma query "gastou" o idle sozinha).
- `statement_text` pode vir truncado/vazio (customer-managed keys) → o `node_id` some e
  a query cai no bucket "não-atribuído". Reportamos o % não-atribuído (honestidade).

Fontes: https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/query-history
        https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing
"""
from pyspark.sql import SparkSession, DataFrame
from src.analyzers.real_cost import _janela, _validar_moeda

# Regex do comentário que o dbt PREPENDA por padrão: /* {json} */. Extrai o 1º
# objeto flat e pega `node_id` (ex.: "model.projeto.meu_modelo").
_RX_DBT = r"/\\*\\s*(\\{.*?\\})\\s*\\*/"


def custo_por_modelo_dbt(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo atribuído por modelo dbt (e um bucket 'não-atribuído' para query não-dbt
    / sem node_id). Alocação: custo do warehouse na hora × (task_time da query na hora
    / task_time total na hora). Buckets horários; query é atribuída à hora de início."""
    inicio, fim = _janela(dias)
    moeda = _validar_moeda(moeda)
    return spark.sql(f"""
      WITH custo_wh_hora AS (
        SELECT
          u.usage_metadata.warehouse_id                       AS warehouse_id,
          date_trunc('HOUR', u.usage_start_time)              AS hora,
          SUM(u.usage_quantity * CAST(lp.pricing.effective_list.`default` AS DOUBLE)) AS custo
        FROM system.billing.usage u
        JOIN system.billing.list_prices lp
          ON u.sku_name = lp.sku_name AND u.cloud = lp.cloud
         AND u.usage_end_time >= lp.price_start_time
         AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
         AND lp.currency_code = '{moeda}'
        WHERE u.usage_metadata.warehouse_id IS NOT NULL
          AND u.usage_date BETWEEN '{inicio}' AND '{fim}'
        GROUP BY 1, 2
      ),
      queries AS (
        SELECT
          q.compute.warehouse_id                              AS warehouse_id,
          date_trunc('HOUR', q.start_time)                    AS hora,
          get_json_object(regexp_extract(q.statement_text, '{_RX_DBT}', 1), '$.node_id') AS node_id,
          q.total_task_duration_ms                            AS task_ms
        FROM system.query.history q
        WHERE q.compute.warehouse_id IS NOT NULL
          AND q.total_task_duration_ms > 0
          AND q.start_time >= TIMESTAMP('{inicio}')
      ),
      tot_hora AS (
        SELECT warehouse_id, hora, SUM(task_ms) AS task_ms_total
        FROM queries GROUP BY 1, 2
      )
      SELECT
        COALESCE(q.node_id, '(não-atribuído / não-dbt)')       AS modelo,
        element_at(split(q.node_id, '[.]'), -1)                AS nome_modelo,
        SUM(c.custo * (q.task_ms / t.task_ms_total))           AS custo_atribuido,
        ROUND(SUM(q.task_ms) / 1000.0, 1)                      AS task_segundos,
        COUNT(*)                                               AS execucoes
      FROM queries q
      JOIN tot_hora t      ON q.warehouse_id = t.warehouse_id AND q.hora = t.hora
      JOIN custo_wh_hora c ON q.warehouse_id = c.warehouse_id AND q.hora = c.hora
      WHERE t.task_ms_total > 0
      GROUP BY 1, 2
    """)


def tendencia_periodo(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Tendência INTERNA: custo/DBU do período atual vs o período anterior de mesmo
    tamanho, por SKU. Não é peer-benchmark (a mldata não tem base de pares) — é
    comparação honesta período-vs-período. `SUM` sempre (RETRACTION/RESTATEMENT se
    cancelam)."""
    ini_atual, fim_atual = _janela(dias)
    ini_ant, fim_ant = _janela(2 * dias)  # janela anterior termina onde a atual começa
    moeda = _validar_moeda(moeda)
    return spark.sql(f"""
      WITH prec AS (
        SELECT u.sku_name, u.usage_date,
               u.usage_quantity AS dbus,
               u.usage_quantity * CAST(lp.pricing.effective_list.`default` AS DOUBLE) AS custo
        FROM system.billing.usage u
        JOIN system.billing.list_prices lp
          ON u.sku_name = lp.sku_name AND u.cloud = lp.cloud
         AND u.usage_end_time >= lp.price_start_time
         AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
         AND lp.currency_code = '{moeda}'
        WHERE u.usage_date BETWEEN '{ini_ant}' AND '{fim_atual}'
      )
      SELECT
        sku_name,
        SUM(CASE WHEN usage_date BETWEEN '{ini_atual}' AND '{fim_atual}' THEN custo ELSE 0 END) AS custo_atual,
        SUM(CASE WHEN usage_date BETWEEN '{ini_ant}' AND '{fim_ant}'    THEN custo ELSE 0 END) AS custo_anterior,
        SUM(CASE WHEN usage_date BETWEEN '{ini_atual}' AND '{fim_atual}' THEN dbus ELSE 0 END) AS dbus_atual,
        SUM(CASE WHEN usage_date BETWEEN '{ini_ant}' AND '{fim_ant}'    THEN dbus ELSE 0 END) AS dbus_anterior
      FROM prec
      GROUP BY sku_name
      HAVING custo_atual > 0 OR custo_anterior > 0
    """)


def materializar_atribuicao(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> dict:
    """Grava as gold de atribuição/tendência, isolando cada uma (query.history pode
    não estar liberada; a tendência não depende dela). Retorna resumo."""
    saidas = [
        ("gold/attribution/custo_por_modelo_dbt", lambda: custo_por_modelo_dbt(spark, dias, moeda)),
        ("gold/attribution/tendencia",            lambda: tendencia_periodo(spark, dias, moeda)),
    ]
    gravado, erros = {}, {}
    for caminho, fn in saidas:
        try:
            df = fn().cache()
            df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
                .save(f"dbfs:/finops/{caminho}")
            gravado[caminho] = df.count()
            df.unpersist()
        except Exception as e:
            erros[caminho] = str(e).splitlines()[0][:200]
    return {"gravado": gravado, "erros": erros}
