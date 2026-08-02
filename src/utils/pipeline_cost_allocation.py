from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, sum as spark_sum, avg, count, struct, current_timestamp
)
from typing import Dict, List, Optional
from datetime import datetime

# Limiares (em horas) do SLA tier derivado da DURAÇÃO média — heurística interna.
SLA_FAST_MAX_HOURS = 0.5
SLA_SLOW_MIN_HOURS = 4.0


def _derive_pipeline_meta(job_name: Optional[str], avg_duration_hours: float) -> Dict:
    """Deriva pipeline/produto/SLA a partir do NOME do job — HEURÍSTICA FRÁGIL,
    dependente de convenção de nomenclatura. Explicitada como tal:
    `allocation_method='heuristica_nome_do_job'`.

    - pipeline_name = trecho antes do 1º '_'; product_name = antes do 1º '-'.
    - Robusto a nome None/vazio/sem separador (antes `job_name.split(...)` estourava
      AttributeError em job sem nome).
    - Se não há separador, o campo cai para '(indefinido)' em vez de repetir o nome
      inteiro como se fosse um pipeline/produto de verdade.
    """
    name = (job_name or "").strip()
    if not name:
        pipeline_name = "(sem_nome)"
        product_name = "(sem_nome)"
    else:
        pipeline_name = name.split("_", 1)[0] if "_" in name else "(indefinido)"
        product_name = name.split("-", 1)[0] if "-" in name else "(indefinido)"

    duration = avg_duration_hours or 0.0
    if duration < SLA_FAST_MAX_HOURS:
        sla_tier = "fast"
    elif duration > SLA_SLOW_MIN_HOURS:
        sla_tier = "slow"
    else:
        sla_tier = "standard"

    return {
        "pipeline_name": pipeline_name,
        "product_name": product_name,
        "sla_tier": sla_tier,
    }


def allocate_cost_by_pipeline(
    spark: SparkSession,
    workspace_name: str
) -> None:
    df_jobs = spark.read.format("delta").load("dbfs:/finops/gold/compute/jobs_summary") \
        .filter(col("workspace_name") == workspace_name)
    
    df_runs = spark.read.format("delta").load("dbfs:/finops/silver/compute/job_runs") \
        .filter(col("workspace_name") == workspace_name) \
        .filter(col("start_time") >= int((datetime.utcnow().timestamp() - 30 * 24 * 3600) * 1000))
    
    df_costs = spark.read.format("delta").load("dbfs:/finops/gold/costs/dbu_estimates") \
        .filter(col("workspace_name") == workspace_name)
    
    df_job_costs = df_runs \
        .join(df_costs, df_runs.cluster_instance.contains(df_costs.cluster_id), "left") \
        .groupBy("job_id") \
        .agg(
            spark_sum("estimated_dbu_cost").alias("total_dbu_cost"),
            avg("estimated_dbu_cost").alias("avg_dbu_cost_per_run"),
            count("*").alias("total_runs"),
            avg("duration_hours").alias("avg_duration_hours")
        )
    
    pipeline_allocation = []
    
    for row in df_jobs.join(df_job_costs, "job_id", "left").collect():
        job_id = row.job_id
        job_name = row.job_name
        
        total_cost = row.total_dbu_cost or 0.0
        avg_cost_per_run = row.avg_dbu_cost_per_run or 0.0
        total_runs = row.total_runs or 0
        avg_duration = row.avg_duration_hours or 0.0
        
        meta = _derive_pipeline_meta(job_name, avg_duration)

        pipeline_allocation.append({
            "workspace_name": workspace_name,
            "resource_type": "pipeline",
            "resource_id": str(job_id),
            "resource_name": job_name,
            "pipeline_name": meta["pipeline_name"],
            "product_name": meta["product_name"],
            "sla_tier": meta["sla_tier"],
            "estimated_monthly_cost": total_cost * 30,
            "estimated_dbu_cost": total_cost,
            "cost_per_run": avg_cost_per_run,
            "total_runs_monthly": total_runs,
            "avg_duration_hours": avg_duration,
            # Custo vem de job_runs; pipeline/produto/SLA são HEURÍSTICA de nome.
            "allocation_method": "job_runs",
            "meta_derivation": "heuristica_nome_do_job",
            "process_timestamp": current_timestamp()
        })
    
    if pipeline_allocation:
        df_allocation = spark.createDataFrame(pipeline_allocation)
        df_allocation.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save("dbfs:/finops/gold/cost_allocation_pipelines")

def get_cost_by_product(
    spark: SparkSession,
    workspace_name: str
) -> Dict:
    try:
        df_allocation = spark.read.format("delta").load("dbfs:/finops/gold/cost_allocation_pipelines") \
            .filter(col("workspace_name") == workspace_name)
        
        if df_allocation.count() == 0:
            return {}
        
        product_costs = df_allocation \
            .groupBy("product_name") \
            .agg({
                "estimated_monthly_cost": "sum",
                "resource_id": "count"
            }) \
            .collect()
        
        return {
            "by_product": {row.product_name: row["sum(estimated_monthly_cost)"] for row in product_costs},
            "by_pipeline": df_allocation.groupBy("pipeline_name").agg({"estimated_monthly_cost": "sum"}).collect(),
            "by_sla": df_allocation.groupBy("sla_tier").agg({"estimated_monthly_cost": "sum"}).collect()
        }
    except Exception as e:
        # Antes engolia QUALQUER falha e devolvia alocação vazia — o assessment
        # "passava" sem custo por pipeline e ninguém sabia por quê. Agora loga.
        print(f"[pipeline_cost_allocation] alocação por pipeline/produto/SLA falhou: {e}")
        return {}
