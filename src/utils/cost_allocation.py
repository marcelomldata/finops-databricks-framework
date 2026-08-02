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


def _map_job_costs(job_run_rows: Iterable,
                   cluster_cost_map: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Custo por job a partir dos runs (BUG corrigido: antes o custo de job era
    SEMPRE 0.0). Casa `cluster_instance` (string com o id do cluster do run) com
    o custo do cluster em dbu_estimates. Deduplica por (job_id, cluster_id) para
    NÃO multiplicar o custo mensal do cluster a cada run do mesmo job."""
    seen_pairs = set()
    job_costs: Dict[str, Dict[str, float]] = {}
    for run in job_run_rows:
        job_id = getattr(run, "job_id", None)
        if job_id is None:
            continue
        job_id = str(job_id)
        instance = getattr(run, "cluster_instance", None)
        if instance is None:
            continue
        instance = str(instance)
        for cluster_id, costs in cluster_cost_map.items():
            if cluster_id and cluster_id in instance:
                pair = (job_id, cluster_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                bucket = job_costs.setdefault(job_id, {"monthly": 0.0, "dbu": 0.0})
                bucket["monthly"] += costs["monthly"]
                bucket["dbu"] += costs["dbu"]
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
            # Reflete SE o custo do job foi de fato casado a um cluster; sem isso
            # um 0.0 legítimo (job sem run no período) se confundia com "não medido".
            "allocation_method": (
                ("tags" if tags["cost_center"] else "default") if has_cost
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

    domain_costs = df_allocation \
        .groupBy("cost_center", "business_unit", "data_domain") \
        .agg({
            "estimated_monthly_cost": "sum",
            "estimated_dbu_cost": "sum"
        }) \
        .collect()

    return {
        "by_cost_center": {row.cost_center: row["sum(estimated_monthly_cost)"] for row in domain_costs},
        "by_business_unit": {row.business_unit: row["sum(estimated_monthly_cost)"] for row in domain_costs},
        "by_data_domain": {row.data_domain: row["sum(estimated_monthly_cost)"] for row in domain_costs}
    }
