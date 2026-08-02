import ast
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, coalesce, struct, current_timestamp
)
from typing import Dict, Iterable, Optional

_TAG_KEYS = {
    "cost_center": ("cost_center", "CostCenter"),
    "business_unit": ("business_unit", "BusinessUnit"),
    "data_domain": ("data_domain", "DataDomain"),
    "project": ("project", "Project"),
    "owner": ("owner", "Owner"),
}


def _empty_tags() -> Dict:
    return {k: "" for k in _TAG_KEYS}


def parse_tags(tags_str) -> Dict:
    """Parser ROBUSTO das tags de custo.

    Antes: `json.loads(tags_str.replace("'", '"'))` — quebrava em qualquer valor
    com apóstrofo (ex.: `O'Brien`), em `True/False/None` (repr de dict Python,
    que não é JSON) e viraria alocação vazia silenciosa. Agora:
      1. Tenta JSON puro (caso a origem já seja JSON).
      2. Se falhar, tenta `ast.literal_eval` — entende o repr de dict Python
         (aspas simples, True/None) SEM os riscos de `eval`.
      3. Só então desiste (linha vira alocação vazia — degradação por linha).
    Aceita dict já desserializado também.
    """
    if tags_str is None:
        return _empty_tags()

    parsed = None
    if isinstance(tags_str, dict):
        parsed = tags_str
    else:
        s = str(tags_str).strip()
        if not s or s.lower() == "null" or s == "{}":
            return _empty_tags()
        for loader in (json.loads, ast.literal_eval):
            try:
                candidate = loader(s)
                if isinstance(candidate, dict):
                    parsed = candidate
                    break
            except (ValueError, SyntaxError, TypeError):
                continue

    if not isinstance(parsed, dict):
        return _empty_tags()

    def _get(*names):
        for n in names:
            v = parsed.get(n)
            if v not in (None, ""):
                return str(v)
        return ""

    return {key: _get(*aliases) for key, aliases in _TAG_KEYS.items()}


def _build_cluster_cost_map(cost_rows: Iterable) -> Dict[str, Dict[str, float]]:
    """{cluster_id: {"monthly": ..., "dbu": ...}} a partir de dbu_estimates,
    coletado UMA vez (antes era uma query Spark por cluster — N+1)."""
    cost_map: Dict[str, Dict[str, float]] = {}
    for r in cost_rows:
        cid = getattr(r, "cluster_id", None)
        if cid is None:
            continue
        cost_map[str(cid)] = {
            "monthly": float(getattr(r, "estimated_monthly_cost", 0.0) or 0.0),
            "dbu": float(getattr(r, "estimated_dbu_cost", 0.0) or 0.0),
        }
    return cost_map


def _extract_cluster_id(instance) -> Optional[str]:
    """Extrai o cluster_id de `cluster_instance` para casar por IGUALDADE.

    Antes o match era `cluster_id in instance` (continência de string): um id
    curto casava DENTRO de outro (`c-1` dentro de `c-12`), sobre-contando. Aqui
    resolvemos o id exato. `cluster_instance` costuma ser um blob tipo
    `{'cluster_id': 'c-1'}` (repr de dict) ou o próprio id em texto puro."""
    if instance is None:
        return None
    s = str(instance).strip()
    if not s:
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            v = loader(s)
            if isinstance(v, dict):
                cid = v.get("cluster_id") or v.get("clusterId")
                return str(cid) if cid not in (None, "") else None
        except (ValueError, SyntaxError, TypeError):
            continue
    return s  # não é dict: a própria string é o id


def _map_job_costs(job_run_rows: Iterable,
                   cluster_cost_map: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Custo por job a partir dos runs (BUG histórico: antes era SEMPRE 0.0).

    Duas correções de rateio sobre a 1ª versão do fix (apontadas em revisão):
      - casa o cluster por IGUALDADE do id extraído (`_extract_cluster_id`), não
        por substring;
      - PRORRATEIA o custo mensal do cluster entre os jobs DISTINTOS que rodaram
        nele. Dar o custo cheio a cada job inflava: um cluster compartilhado por
        N jobs somava N× o próprio custo. Com o rateio, a soma das parcelas de
        job de um cluster é, no máximo, o custo do cluster.
    Deduplica por (job_id, cluster_id): várias runs do mesmo job no mesmo cluster
    contam uma vez. O rateio é aproximação por CONTAGEM de jobs (não há dado de
    uso por run) — declarado como tal no `allocation_method` da linha."""
    # 1) pares distintos (job, cluster) com id EXATO
    pairs = set()
    for run in job_run_rows:
        job_id = getattr(run, "job_id", None)
        if job_id is None:
            continue
        cid = _extract_cluster_id(getattr(run, "cluster_instance", None))
        if not cid or cid not in cluster_cost_map:
            continue
        pairs.add((str(job_id), cid))

    # 2) quantos jobs distintos por cluster (denominador do rateio)
    jobs_por_cluster: Dict[str, set] = {}
    for job_id, cid in pairs:
        jobs_por_cluster.setdefault(cid, set()).add(job_id)

    # 3) cada job recebe a FRAÇÃO do custo do cluster (custo/nº de jobs no cluster)
    job_costs: Dict[str, Dict[str, float]] = {}
    for job_id, cid in pairs:
        n = len(jobs_por_cluster[cid]) or 1
        costs = cluster_cost_map[cid]
        bucket = job_costs.setdefault(job_id, {"monthly": 0.0, "dbu": 0.0})
        bucket["monthly"] += costs["monthly"] / n
        bucket["dbu"] += costs["dbu"] / n
    return job_costs


def extract_cost_allocation_tags(
    spark: SparkSession,
    workspace_name: str
) -> None:
    df_clusters = spark.read.format("delta").load("dbfs:/finops/silver/compute/clusters") \
        .filter(col("workspace_name") == workspace_name)

    df_jobs = spark.read.format("delta").load("dbfs:/finops/silver/compute/jobs") \
        .filter(col("workspace_name") == workspace_name)

    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)

    # Coleta o custo por cluster UMA vez (dict) — evita a query por cluster e
    # serve tanto à alocação de cluster quanto à de job.
    cluster_cost_map = _build_cluster_cost_map(df_costs.collect())

    cluster_allocation = []
    for row in df_clusters.collect():
        tags = parse_tags(row.custom_tags if hasattr(row, 'custom_tags') else "")
        costs = cluster_cost_map.get(str(row.cluster_id), {"monthly": 0.0, "dbu": 0.0})
        monthly_cost = costs["monthly"]
        dbu_cost = costs["dbu"]

        cost_center = tags["cost_center"] or "unallocated"

        cluster_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "cluster",
            "resource_id": row.cluster_id,
            "resource_name": row.cluster_name if hasattr(row, 'cluster_name') else "",
            "cost_center": cost_center,
            "business_unit": tags["business_unit"] or "unallocated",
            "data_domain": tags["data_domain"] or "unallocated",
            "estimated_monthly_cost": monthly_cost,
            "estimated_dbu_cost": dbu_cost,
            "allocation_method": "tags" if tags["cost_center"] else "default",
            "tags": tags,
            "process_timestamp": current_timestamp()
        })

    # Custo por job: casa os runs (silver/compute/job_runs) com o custo do
    # cluster. Se a tabela/coluna não existir, degrada para 0.0 (sem quebrar) em
    # vez de fabricar 0.0 quando o dado EXISTE.
    try:
        df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
            .filter(col("workspace_name") == workspace_name)
        job_cost_map = _map_job_costs(df_runs.collect(), cluster_cost_map)
    except Exception as e:
        print(f"[cost_allocation] custo por job indisponível (runs não casaram): {e}")
        job_cost_map = {}

    job_allocation = []
    for row in df_jobs.collect():
        tags = parse_tags(row.tags if hasattr(row, 'tags') else "")

        cost_center = tags["cost_center"] or "unallocated"
        costs = job_cost_map.get(str(row.job_id), {"monthly": 0.0, "dbu": 0.0})
        has_cost = costs["monthly"] > 0 or costs["dbu"] > 0

        job_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "job",
            "resource_id": str(row.job_id),
            "resource_name": row.job_name if hasattr(row, 'job_name') else "",
            "cost_center": cost_center,
            "business_unit": tags["business_unit"] or "unallocated",
            "data_domain": tags["data_domain"] or "unallocated",
            "estimated_monthly_cost": costs["monthly"],
            "estimated_dbu_cost": costs["dbu"],
            # Reflete SE o custo do job foi de fato casado a um cluster e que ele
            # é uma PARCELA RATEADA do custo do cluster (não medição direta); sem
            # isso um 0.0 legítimo (job sem run no período) se confundia com "não
            # medido", e o número parecia mais preciso do que é.
            "allocation_method": (
                ("tags_rateio_cluster" if tags["cost_center"] else "rateio_cluster") if has_cost
                else "sem_custo_casado"
            ),
            "tags": tags,
            "process_timestamp": current_timestamp()
        })

    if cluster_allocation:
        df_cluster_alloc = spark.createDataFrame(cluster_allocation)
        df_cluster_alloc.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation")

    if job_allocation:
        df_job_alloc = spark.createDataFrame(job_allocation)
        df_job_alloc.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation")

def get_cost_by_domain(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    df_allocation = spark.read.format("delta").load("dbfs:/finops/gold/cost_allocation") \
        .filter(col("workspace_name") == workspace_name)

    if df_allocation.count() == 0:
        return {}

    def _rollup(resource_type: str):
        """Soma o custo por cada dimensão, para UM tipo de recurso. Acumula
        (antes um dict-comprehension sobre linhas agrupadas por 3 dimensões
        SOBRESCREVIA business_unit/data_domain repetidos — só a última linha
        sobrevivia; agora soma de verdade)."""
        rows = df_allocation.filter(col("resource_type") == resource_type) \
            .groupBy("cost_center", "business_unit", "data_domain") \
            .agg({"estimated_monthly_cost": "sum", "estimated_dbu_cost": "sum"}) \
            .collect()
        cc: Dict[str, float] = {}
        bu: Dict[str, float] = {}
        dd: Dict[str, float] = {}
        for r in rows:
            v = float(r["sum(estimated_monthly_cost)"] or 0.0)
            cc[r.cost_center] = cc.get(r.cost_center, 0.0) + v
            bu[r.business_unit] = bu.get(r.business_unit, 0.0) + v
            dd[r.data_domain] = dd.get(r.data_domain, 0.0) + v
        return cc, bu, dd

    # AUTORITATIVO: o custo real está nos CLUSTERS (onde o DBU é gasto). Somar
    # cluster + job na MESMA agregação contaria o mesmo dinheiro duas vezes — a
    # linha de job carrega uma PARCELA rateada do custo do cluster onde rodou.
    # Por isso o total por domínio vem das linhas de cluster; a visão por job é
    # uma RE-ATRIBUIÇÃO do mesmo dinheiro (pelas tags do job), devolvida à parte
    # e NUNCA somada com a de cluster.
    cc, bu, dd = _rollup("cluster")
    jcc, jbu, jdd = _rollup("job")

    return {
        "by_cost_center": cc,
        "by_business_unit": bu,
        "by_data_domain": dd,
        # Re-atribuição pelas tags do JOB — para comparar quem RODOU vs. quem
        # é DONO do cluster. Não somar com as chaves acima (mesmo dinheiro).
        "by_cost_center_via_jobs": jcc,
        "by_business_unit_via_jobs": jbu,
        "by_data_domain_via_jobs": jdd,
    }
