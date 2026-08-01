"""
Motor de custo REAL via system tables (Fase 1 do PLANO_DE_ACAO).

Substitui a estimativa por uptime × taxa fixa (`cost_estimator.py`) pelo custo
MEDIDO do Databricks: `system.billing.usage` (DBU metrificado por SKU e recurso)
× `system.billing.list_prices` (preço vigente por SKU).

⚠ LIMITAÇÕES QUE O RELATÓRIO PRECISA DECLARAR (o número NÃO fecha com a fatura
Azure se você ignorar isto):
- Isto mede o **DBU do Databricks a preço de lista** (`effective_list`). NÃO inclui
  a VM/compute subjacente, storage e rede — o Azure fatura essas à parte e elas
  NÃO estão em `system.billing.usage`. O gasto total costuma ser ~2× o DBU.
- Não reflete descontos de commit/negociados, nem câmbio (`list_prices` em USD).
- Custo por job só cobre job/serverless compute; job em all-purpose não popula
  `job_id` no billing (custo compartilhado, não atribuível por job).

Fontes verificadas contra a doc oficial Azure Databricks (2026):
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/billing
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/pricing
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/compute
- https://learn.microsoft.com/en-us/azure/databricks/admin/system-tables/jobs
"""
import re
from pyspark.sql import SparkSession, DataFrame
from typing import Optional
from datetime import date, timedelta


# ── Validação de identificadores interpolados na query (defense-in-depth) ──────
# `moeda` e `tag` vêm de env vars (operador do assessment). Mesmo sendo operador
# privilegiado, validar contra allowlist evita quebra acidental de query (ex.:
# barra invertida no fim da tag fechava mal o literal) e fecha a interpolação.
def _validar_moeda(moeda: str) -> str:
    if not re.fullmatch(r"[A-Z]{3}", moeda or ""):
        raise ValueError(f"Moeda inválida: {moeda!r}. Use código ISO de 3 letras (ex.: USD).")
    return moeda


def _validar_tag(tag: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", tag or ""):
        raise ValueError(f"Chave de tag inválida: {tag!r}. Use apenas letras, números, _ . -")
    return tag


def _janela(dias: int) -> tuple:
    """Intervalo [inicio, fim] como ISO. `fim` = ONTEM: hoje ainda acumula e o
    billing tem latência de ingestão, então incluir hoje faria o último dia ler
    baixo e parecer 'queda de custo'. Janela = exatamente `dias` dias fechados."""
    fim = date.today() - timedelta(days=1)
    inicio = fim - timedelta(days=dias - 1)
    return (inicio.isoformat(), fim.isoformat())


# ── Preflight ─────────────────────────────────────────────────────────────────
_PROBES = {
    "system.billing.usage":
        "SELECT 1 FROM system.billing.usage WHERE usage_date >= current_date() - INTERVAL 1 DAYS LIMIT 1",
    "system.billing.list_prices":
        "SELECT 1 FROM system.billing.list_prices LIMIT 1",
    "system.compute.node_timeline":
        "SELECT 1 FROM system.compute.node_timeline WHERE start_time >= current_date() - INTERVAL 1 DAYS LIMIT 1",
    "system.lakeflow.jobs":
        "SELECT 1 FROM system.lakeflow.jobs LIMIT 1",
}


def system_tables_disponiveis(spark: SparkSession) -> tuple:
    """As QUATRO system tables que o pipeline lê estão acessíveis?

    Testa cada uma — não só `billing.usage`. Em conta Azure nova, `billing` vem
    habilitada mas `compute` e `lakeflow` costumam exigir habilitação EXPLÍCITA
    do account admin. Testar só billing dava um falso-verde: passava aqui e
    abortava no meio, com gold pela metade. Retorna (True, msg) ou (False, msg
    acionável dizendo QUAIS faltam e como liberar).
    """
    faltando = []
    for tabela, q in _PROBES.items():
        try:
            spark.sql(q).collect()
        except Exception as e:
            faltando.append((tabela, str(e).splitlines()[0][:160]))
    if not faltando:
        return (True, "todas as system tables necessárias estão acessíveis")
    detalhe = "\n".join(f"  - {t}: {err}" for t, err in faltando)
    msg = (
        "Faltam system tables acessíveis:\n" + detalhe + "\n\n"
        "Corrija antes de rodar: (1) o workspace precisa de Unity Catalog; "
        "(2) o account/metastore admin habilita os system schemas — `billing` vem "
        "ligada, mas COMPUTE e LAKEFLOW normalmente precisam de habilitação "
        "explícita — e concede ao usuário/SP que roda o assessment: USE CATALOG no "
        "catálogo `system`, USE SCHEMA e SELECT em billing/compute/lakeflow."
    )
    return (False, msg)


# ── CTE de uso precificado (o coração; usado por 3 das 4 queries) ──────────────
def _cte_uso_precificado(inicio: str, fim: str, moeda: str, filtro_extra: str = "") -> str:
    """CTE `uso_precificado`: cada linha de `usage` com seu preço.

    - **LEFT JOIN** (não inner): uso sem preço casado (SKU novo, free-tier, moeda
      sem linha) NÃO some — fica com `preco=NULL`/`tem_preco=false`, e o total de
      DBU continua correto. A subcontagem silenciosa do inner join era o furo que
      mais feria a promessa de "medido, não estimado".
    - **QUALIFY por `record_id`**: garante UM preço por linha de uso mesmo se
      `list_prices` tiver janelas sobrepostas (dado malformado) — sem isso a linha
      casaria 2× e dobraria DBU e custo. Pega a janela de maior `price_start_time`.
    - **CAST DOUBLE**: `effective_list.default` é string; multiplicar sem cast é
      frágil sob ANSI estrito.
    - `default` é palavra reservada → crase.
    """
    return f"""
    WITH uso_precificado AS (
      SELECT
        u.usage_date, u.workspace_id, u.billing_origin_product, u.sku_name,
        u.product_features.is_serverless AS is_serverless,
        u.product_features.is_photon     AS is_photon,
        u.usage_metadata                  AS usage_metadata,
        u.custom_tags                     AS custom_tags,
        u.usage_quantity                  AS usage_quantity,
        CAST(lp.pricing.effective_list.`default` AS DOUBLE) AS preco,
        (lp.sku_name IS NOT NULL)         AS tem_preco
      FROM system.billing.usage u
      LEFT JOIN system.billing.list_prices lp
        ON u.sku_name = lp.sku_name
       AND u.cloud    = lp.cloud
       AND u.usage_end_time >= lp.price_start_time
       AND (lp.price_end_time IS NULL OR u.usage_end_time < lp.price_end_time)
       AND lp.currency_code = '{moeda}'
      WHERE u.usage_date BETWEEN '{inicio}' AND '{fim}'
        {filtro_extra}
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY u.record_id ORDER BY lp.price_start_time DESC NULLS LAST) = 1
    )"""


def custo_real_por_recurso(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo real e DBU por recurso e dia. `dbus_sem_preco` expõe a cobertura
    (quanto do DBU não casou preço) — honestidade, não silêncio."""
    inicio, fim = _janela(dias)
    moeda = _validar_moeda(moeda)
    return spark.sql(_cte_uso_precificado(inicio, fim, moeda) + """
      SELECT
        usage_date, workspace_id, billing_origin_product, sku_name,
        is_serverless, is_photon,
        COALESCE(usage_metadata.cluster_id, usage_metadata.warehouse_id,
                 usage_metadata.job_id, usage_metadata.dlt_pipeline_id,
                 usage_metadata.endpoint_name)              AS resource_id,
        SUM(usage_quantity)                                  AS dbus,
        SUM(usage_quantity * COALESCE(preco, 0))             AS cost,
        SUM(CASE WHEN NOT tem_preco THEN usage_quantity ELSE 0 END) AS dbus_sem_preco
      FROM uso_precificado
      GROUP BY 1,2,3,4,5,6,7
    """)


def custo_por_job(spark: SparkSession, dias: int = 30, moeda: str = "USD") -> DataFrame:
    """Custo real por job. ⚠ Só job/serverless compute — job em all-purpose não
    popula `job_id` no billing e NÃO aparece aqui (limitação da plataforma)."""
    inicio, fim = _janela(dias)
    moeda = _validar_moeda(moeda)
    cte = _cte_uso_precificado(
        inicio, fim, moeda,
        "AND u.billing_origin_product = 'JOBS' AND u.usage_metadata.job_id IS NOT NULL")
    return spark.sql(cte + """
      , jobs_atuais AS (
        SELECT workspace_id, job_id, name
        FROM system.lakeflow.jobs
        QUALIFY ROW_NUMBER() OVER (
          PARTITION BY workspace_id, job_id ORDER BY change_time DESC) = 1
      )
      SELECT
        up.workspace_id,
        up.usage_metadata.job_id                       AS job_id,
        FIRST(j.name, TRUE)                            AS job_name,
        COUNT(DISTINCT up.usage_metadata.job_run_id)    AS runs,
        SUM(up.usage_quantity)                          AS dbus,
        SUM(up.usage_quantity * COALESCE(up.preco, 0))  AS cost
      FROM uso_precificado up
      LEFT JOIN jobs_atuais j
        ON up.workspace_id = j.workspace_id
       AND up.usage_metadata.job_id = j.job_id
      GROUP BY up.workspace_id, up.usage_metadata.job_id
    """)


def utilizacao_por_cluster(spark: SparkSession, dias: int = 7) -> DataFrame:
    """Utilização média/idle por cluster (right-sizing) via node_timeline.
    ⚠ Retenção de 90 dias; `dias` acima disso volta vazio. Idle = minutos com
    CPU (`user+system`) < 10%. Separa driver (ocioso é normal) de worker."""
    inicio, _ = _janela(min(dias, 90))
    return spark.sql(f"""
      SELECT
        workspace_id, cluster_id, driver,
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
    """Custo serverless por uma tag de `custom_tags`. Linha sem a tag entra como
    NULL = o % NÃO-ATRIBUÍDO (cobertura). ⚠ A gold resultante pode conter
    identificador se o cliente usa pessoa como tag — trate com acesso restrito."""
    inicio, fim = _janela(dias)
    moeda = _validar_moeda(moeda)
    tag = _validar_tag(tag)
    cte = _cte_uso_precificado(inicio, fim, moeda, "AND u.product_features.is_serverless")
    return spark.sql(cte + f"""
      SELECT
        custom_tags['{tag}']                      AS tag_value,
        billing_origin_product,
        SUM(usage_quantity)                       AS dbus,
        SUM(usage_quantity * COALESCE(preco, 0))  AS cost
      FROM uso_precificado
      GROUP BY 1,2
    """)


def materializar_gold(spark: SparkSession, dias: int = 30, moeda: str = "USD",
                      tag_negocio: Optional[str] = None) -> dict:
    """Roda os coletores e grava as tabelas gold de custo REAL.

    ISOLA cada coletor: se `lakeflow`/`compute` não estiver liberada, o coletor
    daquela tabela falha SOZINHO (registrado em `erros`) e os demais continuam —
    em vez de abortar tudo e deixar gold pela metade com um erro cru.

    A contagem de linhas vem do DataFrame em CACHE (não re-escaneia as system
    tables — o `.count()` cru dobraria o scan, numa ferramenta que existe para
    cortar custo). Overwrite = idempotente (a fonte são as system tables).
    """
    ok, msg = system_tables_disponiveis(spark)
    if not ok:
        raise RuntimeError(f"[real_cost] {msg}")

    coletores = [
        ("gold/costs/real_usage",    lambda: custo_real_por_recurso(spark, dias, moeda)),
        ("gold/costs/by_job",        lambda: custo_por_job(spark, dias, moeda)),
        ("gold/compute/utilization", lambda: utilizacao_por_cluster(spark, min(dias, 90))),
    ]
    if tag_negocio:
        coletores.append(("gold/costs/serverless_by_tag",
                          lambda: custo_serverless_por_tag(spark, tag_negocio, dias, moeda)))

    gravado, erros = {}, {}
    for caminho, fn in coletores:
        try:
            df = fn().cache()
            df.write.format("delta").mode("overwrite").option("overwriteSchema", "true") \
                .save(f"dbfs:/finops/{caminho}")
            gravado[caminho] = df.count()  # usa o cache — não re-escaneia
            df.unpersist()
        except Exception as e:
            erros[caminho] = str(e).splitlines()[0][:200]
    return {"gravado": gravado, "erros": erros}
