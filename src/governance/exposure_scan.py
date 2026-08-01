"""
Exposure Scan (LGPD) — v1 METADATA-ONLY.

Scanner read-only de exposição de dado pessoal num workspace Databricks/Unity
Catalog. NÃO lê valor de dado — só metadado: nome de coluna, tags do UC, grants,
lineage e auditoria. É a isca de autoridade que alimenta o DPO-as-a-Service.

Design travado pelo portão security-lgpd (31/07):
- **Metadata-only.** Sem sampling na v1 (ler CPF para "confirmar" corroeria a
  confiança que a oferta de LGPD vende). O diferencial é a CORRELAÇÃO de metadado
  (grants × lineage × audit × tags), não confirmar valor.
- **O output é sensível** (mapa de onde está o dado). Antes de gravar, a ferramenta
  VERIFICA se o destino é amplamente legível e ABORTA se for — não se grava um mapa
  do tesouro num schema público. Saída em DUAS camadas: resumo agregado (circulável)
  × mapa coluna-a-coluna (restrito). Nenhum VALOR de PII no output.
- **Least privilege.** Rode como principal sujeito às máscaras do UC — NUNCA como
  metastore admin. Não persistir valor; a saída é só metadado + score.
- **O cliente é o controlador LGPD.** Mesmo metadata-only processa dado pessoal de
  FUNCIONÁRIOS (grants/audit identificam quem acessou) — finalidade limitada.
- **Funil:** matches são CANDIDATOS com tier de confiança. A confirmação definitiva
  é o handoff humano pago (DPO-as-a-Service), não a ferramenta grátis.

⚠ Enquadramento operador/controlador e base legal → confirmar com jurídico habilitado.
"""
import re
from pyspark.sql import SparkSession, DataFrame
from typing import Optional

# ── Biblioteca de padrões PT-BR, em TIERS DE CONFIANÇA (não boolean) ───────────
# A confiança é do próprio NOME da coluna sugerir PII. `alta` = documento
# inequívoco; `media` = contato/localização; `baixa` = ambíguo (precisa de olho
# humano — é onde o funil entrega ao DPO pago).
_PADROES = {
    "alta": [r"\bcpf\b", r"cpf", r"\bcnpj\b", r"\brg\b", r"num[_ ]?rg", r"passaporte",
             r"titulo[_ ]?eleitor", r"\bcns\b", r"cartao[_ ]?sus", r"\bpis\b", r"\bnis\b",
             r"\bnit\b", r"cnh", r"num[_ ]?cpf", r"nr[_ ]?cpf"],
    "media": [r"e[_ ]?mail", r"telefone", r"\bfone\b", r"celular", r"whatsapp",
              r"endereco", r"logradouro", r"\bcep\b", r"data[_ ]?nasc", r"dt[_ ]?nasc",
              r"nascimento", r"\bidade\b", r"salario", r"renda", r"conta[_ ]?bancaria",
              r"cartao[_ ]?credito", r"\biban\b", r"geoloc", r"latitude", r"longitude"],
    "baixa": [r"\bnome\b", r"sobrenome", r"\bname\b", r"documento", r"\bdoc\b",
              r"genero", r"\bsexo\b", r"raca", r"religiao", r"\bcor\b", r"nacionalidade",
              r"estado[_ ]?civil", r"\bfoto\b", r"\bbio\b", r"observacao"],
}
# Falsos positivos comuns de "nome"/"doc" — rebaixam para "não é PII".
_EXCLUIR = [r"nome[_ ]?(produto|arquivo|tabela|coluna|campo|fantasia|banco|servidor|"
            r"job|processo|host|db|schema|usuario_banco)",
            r"doc[_ ]?(tipo|type|status|id)", r"tipo[_ ]?doc"]

_RX = {t: [re.compile(p) for p in ps] for t, ps in _PADROES.items()}
_RX_EXC = [re.compile(p) for p in _EXCLUIR]


def classificar_coluna(nome: str) -> Optional[str]:
    """Devolve o tier de confiança ('alta'/'media'/'baixa') se o NOME sugere PII,
    ou None. É heurística de nome — por isso a saída é CANDIDATO, não veredito.

    Normaliza separadores (_ - .) para espaço ANTES de casar: sem isso, `\\bnome\\b`
    não pegaria `nome_cliente` (o `_` é caractere de palavra, então não há fronteira
    `\\b` entre `nome` e `_`). Com a normalização, `nome_cliente` vira `nome cliente`
    e casa — mas `sobrenome`/`renomear` continuam de fora (sem fronteira antes)."""
    n = re.sub(r"[_\-.]+", " ", (nome or "").lower())
    if any(rx.search(n) for rx in _RX_EXC):
        return None
    for tier in ("alta", "media", "baixa"):
        if any(rx.search(n) for rx in _RX[tier]):
            return tier
    return None


# ── Least-privilege / preflight ───────────────────────────────────────────────
def _pode_ler_infoschema(spark: SparkSession) -> tuple:
    try:
        spark.sql("SELECT 1 FROM system.information_schema.columns LIMIT 1").collect()
        return (True, "information_schema acessível")
    except Exception as e:
        return (False, "Não consegui ler system.information_schema. Precisa de Unity "
                       "Catalog + SELECT no information_schema (NÃO rode como metastore "
                       f"admin — só o mínimo). Erro: {e}")


# ── Segurança do OUTPUT: o destino é amplamente legível? (bloqueia gravação) ───
_GRUPOS_AMPLOS = ("account users", "users", "all users", "public")


def destino_seguro(spark: SparkSession, catalogo: str, schema: str) -> tuple:
    """A saída é um MAPA de onde está o dado sensível — gravá-la num schema que
    todo mundo lê AUMENTA a superfície de ataque. Antes de gravar, checamos os
    grants do schema de destino; se houver SELECT/USE para um grupo amplo
    (`account users` etc.), RECUSAMOS. Retorna (True, msg) ou (False, motivo)."""
    try:
        df = spark.sql(f"""
          SELECT grantee, privilege_type
          FROM system.information_schema.schema_privileges
          WHERE catalog_name = '{catalogo}' AND schema_name = '{schema}'
        """)
        amplos = [r["grantee"] for r in df.collect()
                  if (r["grantee"] or "").lower() in _GRUPOS_AMPLOS]
        if amplos:
            return (False, f"Destino {catalogo}.{schema} é legível por grupo amplo "
                           f"({', '.join(set(amplos))}). Grave o Exposure Scan num schema "
                           "RESTRITO (grant default-deny, allow-list só do DPO/segurança) — "
                           "o output é um mapa do dado sensível.")
        return (True, f"Destino {catalogo}.{schema} não tem grant amplo detectado")
    except Exception as e:
        # Fail-closed: se não consigo VERIFICAR o destino, não gravo às cegas.
        return (False, f"Não consegui verificar os grants do destino {catalogo}.{schema} "
                       f"— por segurança, não gravo sem confirmar que é restrito. Erro: {e}")


# ── Coleta (tudo metadado) ────────────────────────────────────────────────────
def candidatas_pii(spark: SparkSession) -> DataFrame:
    """Colunas candidatas a PII por NOME, enriquecidas com tag do UC (respeita o
    que já está classificado). NÃO lê valor. Retorna uma linha por coluna candidata."""
    cols = spark.sql("""
      SELECT table_catalog, table_schema, table_name, column_name, data_type
      FROM system.information_schema.columns
      WHERE table_schema <> 'information_schema'
    """)
    from pyspark.sql import functions as F, types as T
    tier_udf = F.udf(classificar_coluna, T.StringType())
    cand = cols.withColumn("tier_confianca", tier_udf(F.col("column_name"))) \
               .filter(F.col("tier_confianca").isNotNull())

    # Tags de coluna já existentes (classificação prévia do cliente).
    try:
        tags = spark.sql("""
          SELECT catalog_name AS table_catalog, schema_name AS table_schema,
                 table_name, column_name, tag_name, tag_value
          FROM system.information_schema.column_tags
        """)
        cand = cand.join(tags, ["table_catalog", "table_schema", "table_name", "column_name"], "left")
    except Exception:
        cand = cand.withColumn("tag_name", F.lit(None)).withColumn("tag_value", F.lit(None))
    return cand


def exposicao_grants(spark: SparkSession, candidatas: DataFrame) -> DataFrame:
    """Cruza as tabelas com coluna candidata a PII contra os grants: quem tem
    SELECT, e destaca grupo AMPLO (o vetor nº1). Metadado puro."""
    from pyspark.sql import functions as F
    tabelas_pii = candidatas.select("table_catalog", "table_schema", "table_name").distinct()
    priv = spark.sql("""
      SELECT table_catalog, table_schema, table_name, grantee, privilege_type
      FROM system.information_schema.table_privileges
      WHERE privilege_type IN ('SELECT', 'ALL PRIVILEGES', 'MODIFY')
    """)
    j = tabelas_pii.join(priv, ["table_catalog", "table_schema", "table_name"], "inner")
    grupos_amplos = [g for g in _GRUPOS_AMPLOS]
    return j.withColumn("grant_amplo", F.lower(F.col("grantee")).isin(grupos_amplos))


def escanear(spark: SparkSession, catalogo_destino: str, schema_destino: str) -> dict:
    """Roda o Exposure Scan v1 (metadata-only) e grava DUAS camadas de saída num
    destino que ele CONFIRMA ser restrito antes de escrever. Retorna resumo."""
    ok, msg = _pode_ler_infoschema(spark)
    if not ok:
        raise RuntimeError(f"[exposure_scan] {msg}")

    # PORTÃO DE SEGURANÇA: não grava o mapa do tesouro num schema público.
    seguro, motivo = destino_seguro(spark, catalogo_destino, schema_destino)
    if not seguro:
        raise RuntimeError(f"[exposure_scan] destino recusado — {motivo}")

    from pyspark.sql import functions as F
    cand = candidatas_pii(spark).cache()
    grants = exposicao_grants(spark, cand).cache()
    base = f"{catalogo_destino}.{schema_destino}"

    # CAMADA 1 (RESTRITA) — mapa coluna-a-coluna. Sem valor de PII, só metadado.
    mapa = cand.select(
        "table_catalog", "table_schema", "table_name", "column_name",
        "data_type", "tier_confianca", "tag_name", "tag_value")
    mapa.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{base}.pii_mapa")

    tabelas_expostas = grants.filter(F.col("grant_amplo"))
    tabelas_expostas.write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{base}.grants_amplos")

    # CAMADA 2 (CIRCULÁVEL) — só agregados/score, sem apontar coluna específica.
    resumo = {
        "colunas_candidatas_pii": cand.count(),
        "por_tier": {r["tier_confianca"]: r["c"] for r in
                     cand.groupBy("tier_confianca").agg(F.count("*").alias("c")).collect()},
        "tabelas_com_pii": cand.select("table_catalog", "table_schema", "table_name").distinct().count(),
        "tabelas_pii_com_grant_amplo": tabelas_expostas.select(
            "table_catalog", "table_schema", "table_name").distinct().count(),
        "ja_classificadas_por_tag": cand.filter(F.col("tag_name").isNotNull()).count(),
    }
    spark.createDataFrame([resumo["por_tier"] | {
        "colunas_candidatas_pii": resumo["colunas_candidatas_pii"],
        "tabelas_com_pii": resumo["tabelas_com_pii"],
        "tabelas_pii_com_grant_amplo": resumo["tabelas_pii_com_grant_amplo"],
    }]).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{base}.resumo_executivo")

    cand.unpersist(); grants.unpersist()
    return {"destino": base, "resumo": resumo,
            "aviso": "matches são CANDIDATOS (por nome); confirmação definitiva = handoff "
                     "DPO-as-a-Service. O cliente é o controlador LGPD."}
