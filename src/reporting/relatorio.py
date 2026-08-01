"""
Relatório técnico + matriz de priorização (Fase 2 do PLANO_DE_ACAO).

Costura as tabelas gold (custo real da Fase 1 + maturity/recomendações) num
RELATÓRIO acionável, em Markdown e HTML. Substitui os 4 dicts soltos que só eram
salvos como Delta + print (e que quebravam ao materializar).

Decisões que vieram do portão (domain-expert + skeptic):
- O "SWOT" NÃO é o núcleo — o núcleo é a **matriz Waste × Esforço × Risco**
  (quadrante acionável). SWOT clássico entra como uma seção executiva curta.
- Todo achado é ANCORADO ao recurso (cluster_id/job_id) e à métrica que o gerou —
  o cliente confere no próprio workspace.
- METODOLOGIA E LIMITAÇÕES são declaradas (o número é DBU a preço de lista, não a
  fatura Azure total). Sem isso, um sênior não confia.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional
from pyspark.sql import SparkSession

_BASE = "dbfs:/finops"

# Limitações fixas do custo medido (Fase 1) — sempre no rodapé do relatório.
LIMITACOES = [
    "Custo = DBU do Databricks a preço de LISTA (effective_list). NÃO inclui a "
    "VM/compute, storage e rede da cloud — o provedor fatura à parte; o total "
    "costuma ser ~2x o valor de DBU.",
    "Não reflete descontos de commit/negociados nem câmbio (list_prices em USD).",
    "Custo por job cobre apenas job/serverless compute; job em all-purpose não "
    "popula job_id no billing e fica fora da atribuição por job.",
    "node_timeline (utilização) retém 90 dias; janelas maiores ficam incompletas.",
]


@dataclass
class Achado:
    """Um achado do assessment, ancorado ao recurso e à métrica de origem."""
    id: str
    dimensao: str                 # custo | utilizacao | pipelines | governanca | cobertura
    severidade: str               # alta | media | baixa
    titulo: str
    recurso: str                  # cluster_id / job_id / tabela / "-"
    metrica: str                  # o número que originou o achado
    economia_mensal: float        # estimativa em moeda (0 se não estimável)
    esforco: str                  # baixo | medio | alto
    risco: str                    # baixo | medio | alto
    acao: str                     # o que fazer, concreto


# ── Leitura defensiva das tabelas gold ────────────────────────────────────────
def _ler(spark: SparkSession, caminho: str):
    """Lê uma tabela gold por path; devolve None se ainda não existe (o Fase 1
    pode não ter rodado, ou o coletor daquela tabela falhou). O relatório então
    marca a seção como indisponível em vez de quebrar."""
    try:
        return spark.read.format("delta").load(f"{_BASE}/{caminho}")
    except Exception:
        return None


# ── Coleta de achados a partir das gold ───────────────────────────────────────
def coletar_achados(spark: SparkSession, moeda: str = "USD") -> List[Achado]:
    achados: List[Achado] = []

    # 1. Clusters ociosos (desperdício direto) — cruza utilização × custo.
    util = _ler(spark, "gold/compute/utilization")
    custo = _ler(spark, "gold/costs/real_usage")
    if util is not None and custo is not None:
        from pyspark.sql import functions as F
        custo_por_cluster = (custo.groupBy("resource_id")
                             .agg(F.sum("cost").alias("cost")))
        ociosos = (util.filter((F.col("driver") == False) &
                               (F.col("cpu_medio_pct") < 20) &
                               (F.col("minutos_observados") > 60))
                   .join(custo_por_cluster,
                         util.cluster_id == custo_por_cluster.resource_id, "left"))
        for r in ociosos.select("cluster_id", "cpu_medio_pct", "pct_minutos_idle",
                                "cost").collect():
            custo_c = float(r["cost"] or 0.0)
            # Desperdício ~ custo × fração ociosa (estimativa conservadora).
            economia = custo_c * (float(r["pct_minutos_idle"] or 0) / 100.0)
            achados.append(Achado(
                id=f"idle-{r['cluster_id']}",
                dimensao="utilizacao", severidade="alta" if economia > 0 else "media",
                titulo=f"Cluster {r['cluster_id']} subutilizado",
                recurso=str(r["cluster_id"]),
                metrica=f"CPU média {r['cpu_medio_pct']}%, {r['pct_minutos_idle']}% dos minutos ociosos",
                economia_mensal=round(economia, 2), esforco="baixo", risco="baixo",
                acao="Reduzir worker count / habilitar autoscaling agressivo / "
                     "auto-termination menor. Validar o pico antes de redimensionar."))

    # 2. Cobertura de preço (honestidade): quanto do DBU não casou preço.
    if custo is not None:
        from pyspark.sql import functions as F
        tot = custo.agg(F.sum("dbus").alias("dbus"),
                        F.sum("dbus_sem_preco").alias("sem_preco")).collect()[0]
        dbus = float(tot["dbus"] or 0.0)
        sem = float(tot["sem_preco"] or 0.0)
        if dbus > 0 and sem / dbus > 0.02:
            achados.append(Achado(
                id="cobertura-preco", dimensao="cobertura",
                severidade="media", titulo="Parte do DBU sem preço casado",
                recurso="-",
                metrica=f"{100*sem/dbus:.1f}% do DBU sem linha em list_prices",
                economia_mensal=0.0, esforco="baixo", risco="baixo",
                acao="SKU novo/free-tier ou moeda sem preço na janela. O custo desse "
                     "recorte lê 0 — tratar como cobertura parcial, não economia."))

    # 3. Recomendações já existentes (small files, jobs falhando etc.).
    recs = _ler(spark, "gold/recommendations")
    if recs is not None:
        cols = set(recs.columns)
        for i, r in enumerate(recs.collect()):
            acao = r["action"] if "action" in cols else (r["title"] if "title" in cols else "")
            achados.append(Achado(
                id=f"rec-{i}", dimensao=r["category"] if "category" in cols else "geral",
                severidade=(r["priority"] if "priority" in cols else "media")
                           .replace("high", "alta").replace("medium", "media").replace("low", "baixa"),
                titulo=r["title"] if "title" in cols else str(acao)[:80],
                recurso="-", metrica=r["description"] if "description" in cols else "",
                economia_mensal=0.0,
                esforco="medio", risco="baixo", acao=str(acao)))

    return achados


# ── Matriz Waste × Esforço × Risco (o núcleo, no lugar do SWOT) ────────────────
def _quadrante(a: Achado) -> str:
    """Classifica cada achado num quadrante acionável. 'Waste' aqui é a economia
    estimada; combinamos com esforço para separar quick-win de projeto."""
    alto_valor = a.economia_mensal > 0 or a.severidade == "alta"
    baixo_esforco = a.esforco == "baixo"
    if alto_valor and baixo_esforco:
        return "quick_win"        # faça já
    if alto_valor and not baixo_esforco:
        return "projeto"          # planeje
    if not alto_valor and baixo_esforco:
        return "incremental"      # quando sobrar tempo
    return "monitorar"            # só observe


def matriz_priorizacao(achados: List[Achado]) -> dict:
    m = {"quick_win": [], "projeto": [], "incremental": [], "monitorar": []}
    for a in achados:
        m[_quadrante(a)].append(a)
    # Dentro de cada quadrante, maior economia primeiro.
    for q in m:
        m[q].sort(key=lambda a: a.economia_mensal, reverse=True)
    return m


# ── SWOT executivo (seção curta, derivado dos scores) ─────────────────────────
def montar_swot(spark: SparkSession, achados: List[Achado]) -> dict:
    mat = _ler(spark, "gold/maturity_scores")
    forcas, fraquezas = [], []
    if mat is not None and mat.take(1):
        r = mat.orderBy(mat.process_timestamp.desc()).take(1)[0] if "process_timestamp" in mat.columns else mat.take(1)[0]
        dims = [("compute", "compute_score"), ("storage", "storage_score"),
                ("governança", "governance_score"), ("pipelines", "pipelines_score"),
                ("observabilidade", "observability_score"), ("custos", "costs_score")]
        for nome, col in dims:
            if col in mat.columns:
                v = float(r[col] or 0)
                (forcas if v >= 0.7 else fraquezas).append(f"{nome}: score {v:.2f}")
    quick = [a for a in achados if _quadrante(a) == "quick_win"]
    oportunidades = [f"{a.titulo} (economia ~{a.economia_mensal:.0f}/mês)" for a in quick[:5]]
    ameacas = [a.titulo for a in achados if a.severidade == "alta"][:5]
    return {"forcas": forcas or ["(rode o assessment para popular)"],
            "fraquezas": fraquezas or ["(sem dados de maturidade)"],
            "oportunidades": oportunidades or ["(sem quick-wins identificados)"],
            "ameacas": ameacas or ["(nenhuma issue de severidade alta)"]}


# ── Renderização Markdown ─────────────────────────────────────────────────────
def _tabela_achados(achados: List[Achado]) -> str:
    if not achados:
        return "_Nenhum achado nesta categoria._\n"
    linhas = ["| Recurso | Achado | Métrica | Economia/mês | Esforço | Risco | Ação |",
              "|---|---|---|---:|---|---|---|"]
    for a in achados:
        eco = f"{a.economia_mensal:,.0f}" if a.economia_mensal else "—"
        linhas.append(f"| `{a.recurso}` | {a.titulo} | {a.metrica} | {eco} | "
                      f"{a.esforco} | {a.risco} | {a.acao} |")
    return "\n".join(linhas) + "\n"


def renderizar_markdown(spark: SparkSession, workspace: str = "-",
                        dias: int = 30, moeda: str = "USD") -> str:
    achados = coletar_achados(spark, moeda)
    matriz = matriz_priorizacao(achados)
    swot = montar_swot(spark, achados)
    custo = _ler(spark, "gold/costs/real_usage")

    from pyspark.sql import functions as F
    total_custo = 0.0
    if custo is not None and custo.take(1):
        total_custo = float(custo.agg(F.sum("cost").alias("c")).collect()[0]["c"] or 0.0)
    economia_total = sum(a.economia_mensal for a in achados)

    fim = (date.today() - timedelta(days=1)).isoformat()
    p = [f"# Relatório FinOps — {workspace}",
         f"_Janela: {dias} dias fechados (até {fim}) · moeda: {moeda} · fonte: system tables_\n",
         "## Resumo executivo",
         f"- **Custo medido (DBU) no período:** {total_custo:,.0f} {moeda}",
         f"- **Economia estimada nos achados:** ~{economia_total:,.0f} {moeda}/mês",
         f"- **Quick-wins (alto valor, baixo esforço):** {len(matriz['quick_win'])}",
         f"- **Achados no total:** {len(achados)}\n",
         "> ⚠ O custo acima é DBU a preço de lista, **não** a fatura total do provedor. "
         "Ver Metodologia & Limitações no fim.\n",
         "## Matriz de priorização (Waste × Esforço × Risco)",
         "### 🟢 Quick-wins — faça já (alto valor, baixo esforço)",
         _tabela_achados(matriz["quick_win"]),
         "### 🔵 Projetos — planeje (alto valor, esforço maior)",
         _tabela_achados(matriz["projeto"]),
         "### ⚪ Incrementais — quando sobrar tempo",
         _tabela_achados(matriz["incremental"]),
         "### 👁 Monitorar",
         _tabela_achados(matriz["monitorar"]),
         "## SWOT executivo",
         "**Forças:** " + "; ".join(swot["forcas"]),
         "**Fraquezas:** " + "; ".join(swot["fraquezas"]),
         "**Oportunidades:** " + "; ".join(swot["oportunidades"]),
         "**Ameaças:** " + "; ".join(swot["ameacas"]) + "\n",
         "## Metodologia & Limitações",
         "Fonte: `system.billing.usage` × `system.billing.list_prices` (custo medido), "
         "`system.compute.node_timeline` (utilização), `system.lakeflow.jobs` (jobs). "
         "Achados ancorados ao recurso e à métrica de origem.\n"]
    for lim in LIMITACOES:
        p.append(f"- {lim}")
    return "\n".join(p) + "\n"


def _md_para_html(md: str, titulo: str) -> str:
    """HTML mínimo e autocontido (sem CDN) a partir do Markdown do relatório —
    tabelas e títulos, o suficiente para abrir/exportar PDF pelo navegador."""
    import html as _h
    linhas, out, in_tbl = md.split("\n"), [], False
    for ln in linhas:
        if ln.startswith("|"):
            cels = [c.strip() for c in ln.strip().strip("|").split("|")]
            if set("".join(cels)) <= set("-: "):
                continue  # separador
            if not in_tbl:
                out.append("<table><tbody>"); in_tbl = True
            tag = "th" if all(c and c[0].isalpha() for c in cels[:1]) and out[-1].endswith("<tbody>") else "td"
            out.append("<tr>" + "".join(f"<{tag}>{_h.escape(c)}</{tag}>" for c in cels) + "</tr>")
        else:
            if in_tbl:
                out.append("</tbody></table>"); in_tbl = False
            if ln.startswith("# "): out.append(f"<h1>{_h.escape(ln[2:])}</h1>")
            elif ln.startswith("## "): out.append(f"<h2>{_h.escape(ln[3:])}</h2>")
            elif ln.startswith("### "): out.append(f"<h3>{_h.escape(ln[4:])}</h3>")
            elif ln.startswith("> "): out.append(f"<blockquote>{_h.escape(ln[2:])}</blockquote>")
            elif ln.startswith("- "): out.append(f"<p>• {_h.escape(ln[2:])}</p>")
            elif ln.strip(): out.append(f"<p>{_h.escape(ln)}</p>")
    if in_tbl:
        out.append("</tbody></table>")
    css = ("body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;"
           "color:#0E1626;line-height:1.55}h1{border-bottom:2px solid #B7841E}"
           "table{border-collapse:collapse;width:100%;font-size:14px;margin:1rem 0}"
           "th,td{border:1px solid #DBE2EC;padding:6px 10px;text-align:left}"
           "th{background:#EEF2F8}blockquote{border-left:3px solid #B5701A;margin:1rem 0;"
           "padding:.4rem 1rem;background:#FBF6EC;color:#5A4A2A}")
    return f"<!doctype html><meta charset='utf-8'><title>{_h.escape(titulo)}</title><style>{css}</style>" + "".join(out)


def gerar_relatorio(spark: SparkSession, workspace: str = "-", dias: int = 30,
                    moeda: str = "USD") -> dict:
    """Gera o relatório em Markdown e HTML e DEVOLVE os textos. A GRAVAÇÃO fica
    com o notebook (via `dbutils.fs.put`, que só existe lá) — assim o módulo não
    depende de dbutils e a escrita produz um arquivo único, não um diretório de
    part-files (o que `saveAsTextFile` faria). Retorna {md, html}."""
    md = renderizar_markdown(spark, workspace, dias, moeda)
    html = _md_para_html(md, f"Relatório FinOps — {workspace}")
    return {"md": md, "html": html}
