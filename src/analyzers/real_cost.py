"""
Motor de custo REAL via system tables (Fase 1 do PLANO_DE_ACAO).

Substitui a estimativa por uptime × taxa fixa (`cost_estimator.py`) pelo custo
MEDIDO do próprio Databricks: `system.billing.usage` (DBU metrificado por SKU e
recurso) × `system.billing.list_prices` (preço vigente por SKU). O custo passa a
ser o que o Databricks realmente faturou, por recurso, período e cloud corretos —
não mais um número igual entre AWS/Azure/GCP.

Fontes da verdade (schemas verificados contra a doc oficial, 2026):
- Custo real   : usage_quantity × pricing.effective_list.default
                 (NÃO pricing.default — a doc mistura os dois; effective_list é o
                 preço realmente faturado, já resolvendo lista vs. promocional)
- DBU          : coluna `usage_quantity` (sempre agregar com SUM — RETRACTION/
                 RESTATEMENT entram como linhas que se cancelam)
- Join preço   : sku_name + cloud + usage_end_time dentro de [price_start, price_end)
- Efêmeros     : node_timeline (por minuto, 90d) enxerga job clusters que a REST
                 API não via
- SCD2         : clusters/jobs guardam histórico; estado atual = maior change_time

Pré-requisitos no ambiente (ver docstring de `system_tables_disponiveis`):
Unity Catalog + SELECT nas system tables. Sem isso, a query nem roda.

Referências:
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/pricing
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/compute
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/jobs
"""
from pyspark.sql import SparkSession, DataFrame
from typing import Optional
from datetime import date, timedelta

# `default` é palavra reservada em SQL — sempre com crase ao acessar o struct.
_PRECO = "lp.pricing.effective_list.`default`"

# Janela de vigência do preço: prende o momento do uso dentro de [start, end).
# `price_end_time IS NULL` = preço vigente (sem fim). Iguala cloud também, senão
# um SKU multi-cloud casaria com o preço de outra nuvem.
_JOIN_PRECO = f"""
  JOIN system.billing.list_prices lp
    ON u.sku_name = lp.sku_name
   AND u.cloud    = lp.cloud
   AND u.usage_end_time >= lp.price_start_time
   AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
   AND lp.currency_code = '{{moeda}}'
"""


def system_tables_disponiveis(spark: SparkSession) -> tuple:
    """Preflight: as system tables são legíveis neste workspace?

    Retorna (True, msg) se sim; (False, motivo_acionável) se não. É a primeira
    coisa a chamar — sem Unity Catalog + os grants (`USE CATALOG`/`USE SCHEMA`/
    `SELECT` no catálogo `system`), a query nem executa, e o erro cru do Spark
    não diz ao dono o que fazer. Aqui traduzimos.
    """
    try:
        # Query barata e seletiva (o motor rejeita varredura ampla das system
        # tables): só confirma que dá para ler billing.usage.
        spark.sql(
            "SELECT 1 FROM system.billing.usage "
            "WHERE usage_date >= current_date() - INTERVAL 1 DAYS LIMIT 1"
        ).collect()
        return (True, "system tables acessíveis")
    except Exception as e:
        return (False,
                "Não consegui ler system.billing.usage. Verifique: (1) o workspace "
                "está habilitado para Unity Catalog; (2) o usuário/SP tem USE CATALOG "
                "no catálogo `system`, USE SCHEMA e SELECT nos schemas billing/compute/"
                f"lakeflow (concedido por um account/metastore admin). Erro original: {e}")


def _janela(dias: int) -> tuple:
    """Intervalo [inicio, fim] a partir de hoje, como strings ISO (sem Date.now
    fora do driver). `fim` é hoje; `inicio` é `dias` atrás."""
    fim = date.today()
    inicio = fim - timedelta(days=dias)
    return (inicio.isoformat(), fim.isoformat())


def custo_real_por_recurso(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo REAL (moeda) e DBU por recurso e por dia — o coração da Fase 1.

    `resource_id` colapsa os diferentes identificadores de `usage_metadata` num
    só (cluster, warehouse, job, pipeline DLT, endpoint de serving), para uma
    linha por recurso independentemente do tipo de compute.
    """
    inicio, fim = _janela(dias)
    return spark.sql(f"""
      SELECT
        u.usage_date,
        u.workspace_id,
        u.billing_origin_product,
        u.sku_name,
        u.product_features.is_serverless AS is_serverless,
        u.product_features.is_photon     AS is_photon,
        COALESCE(u.usage_metadata.cluster_id,
                 u.usage_metadata.warehouse_id,
                 u.usage_metadata.job_id,
                 u.usage_metadata.dlt_pipeline_id,
                 u.usage_metadata.endpoint_name)      AS resource_id,
        SUM(u.usage_quantity)                          AS dbus,
        SUM(u.usage_quantity * {_PRECO})               AS cost
      FROM system.billing.usage u
      {_JOIN_PRECO.format(moeda=moeda)}
      WHERE u.usage_date BETWEEN '{inicio}' AND '{fim}'
      GROUP BY 1,2,3,4,5,6,7
    """)


def custo_por_job(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo real por job (e por run) via usage_metadata.job_id + lakeflow.

    ⚠ Só cobre jobs em JOB COMPUTE ou SERVERLESS — job rodando em all-purpose
    compute NÃO popula `job_id` no billing (recurso compartilhado), então seu
    custo não aparece aqui. Isso é limitação da plataforma, não do código; o
    relatório declara essa cobertura.
    """
    inicio, fim = _janela(dias)
    return spark.sql(f"""
      WITH jobs_usage AS (
        SELECT
          u.workspace_id,
          u.usage_metadata.job_id     AS job_id,
          u.usage_metadata.job_run_id AS run_id,
          u.identity_metadata.run_as  AS run_as,
          u.sku_name,
          u.usage_quantity                        AS dbus,
          u.usage_quantity * {_PRECO}             AS cost
        FROM system.billing.usage u
        {_JOIN_PRECO.format(moeda=moeda)}
        WHERE u.billing_origin_product = 'JOBS'
          AND u.usage_metadata.job_id IS NOT NULL
          AND u.usage_date BETWEEN '{inicio}' AND '{fim}'
      ),
      jobs_atuais AS (
        SELECT workspace_id, job_id, name
        FROM system.lakeflow.jobs
        QUALIFY ROW_NUMBER() OVER (
          PARTITION BY workspace_id, job_id ORDER BY change_time DESC) = 1
      )
      SELECT
        ju.workspace_id,
        ju.job_id,
        FIRST(j.name, TRUE)     AS job_name,
        COUNT(DISTINCT ju.run_id) AS runs,
        SUM(ju.dbus)            AS dbus,
        SUM(ju.cost)            AS cost
      FROM jobs_usage ju
      LEFT JOIN jobs_atuais j USING (workspace_id, job_id)
      GROUP BY ju.workspace_id, ju.job_id
    """)


def utilizacao_por_cluster(spark: SparkSession, dias: int = 7) -> DataFrame:
    """Utilização média/idle por cluster (right-sizing) via node_timeline.

    ⚠ Retenção de `node_timeline` é 90 dias; `dias` acima disso volta vazio.
    Idle = minutos com uso de CPU (`cpu_user_percent + cpu_system_percent`) < 10%.
    Separa driver de worker (`driver` boolean) — driver ocioso é normal, worker
    ocioso é desperdício.
    """
    inicio, _ = _janela(min(dias, 90))
    return spark.sql(f"""
      SELECT
        workspace_id,
        cluster_id,
        driver,
        COUNT(*)                                              AS minutos_observados,
        ROUND(AVG(cpu_user_percent + cpu_system_percent), 1)  AS cpu_medio_pct,
        ROUND(MAX(cpu_user_percent + cpu_system_percent), 1)  AS cpu_pico_pct,
        ROUND(AVG(mem_used_percent), 1)                       AS mem_medio_pct,
        ROUND(100.0 * SUM(CASE WHEN (cpu_user_percent + cpu_system_percent) < 10
                               THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_minutos_idle
      FROM system.compute.node_timeline
      WHERE start_time >= TIMESTAMP('{inicio}')
      GROUP BY workspace_id, cluster_id, driver
    """)


def custo_serverless_por_tag(spark: SparkSession, tag: str, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo serverless agregado por uma tag de `custom_tags`.

    `custom_tags` já traz as tags herdadas das serverless usage policies, então
    isto atribui o gasto serverless (o que mais cresce e o que uptime×rate nunca
    mediu) por unidade de negócio/produto. Linhas sem a tag entram como NULL —
    é o % NÃO-ATRIBUÍDO, que o relatório expõe (honestidade de cobertura).
    """
    inicio, fim = _janela(dias)
    # `tag` é uma chave de configuração (não input de usuário livre); ainda assim
    # escapa aspas simples para não quebrar a query.
    tag_safe = tag.replace("'", "")
    return spark.sql(f"""
      SELECT
        u.custom_tags['{tag_safe}']       AS tag_value,
        u.billing_origin_product,
        SUM(u.usage_quantity)             AS dbus,
        SUM(u.usage_quantity * {_PRECO})  AS cost
      FROM system.billing.usage u
      {_JOIN_PRECO.format(moeda=moeda)}
      WHERE u.product_features.is_serverless
        AND u.usage_date BETWEEN '{inicio}' AND '{fim}'
      GROUP BY 1,2
    """)


def materializar_gold(spark: SparkSession, dias: int = 30, moeda: str = "USD",
                      tag_negocio: Optional[str] = None) -> dict:
    """Roda os coletores e grava as tabelas gold de custo REAL.

    Idempotente por natureza: as system tables são a fonte, então re-rodar
    RECALCULA (overwrite) em vez de acumular — o problema de duplicação do
    caminho antigo (bronze append) não existe aqui.

    Retorna um resumo {tabela: linhas} para o notebook logar.
    """
    ok, msg = system_tables_disponiveis(spark)
    if not ok:
        raise RuntimeError(f"[real_cost] system tables indisponíveis — {msg}")

    resumo = {}
    saidas = [
        ("gold/costs/real_usage",        custo_real_por_recurso(spark, dias, moeda)),
        ("gold/costs/by_job",            custo_por_job(spark, dias, moeda)),
        ("gold/compute/utilization",     utilizacao_por_cluster(spark, min(dias, 90))),
    ]
    if tag_negocio:
        saidas.append(("gold/costs/serverless_by_tag",
                       custo_serverless_por_tag(spark, tag_negocio, dias, moeda)))

    for caminho, df in saidas:
        df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
            .save(f"dbfs:/finops/{caminho}")
        resumo[caminho] = df.count()
    return resumo
