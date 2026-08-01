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


# ── Segurança do OUTPUT: o destino é legível só por quem PODE? (bloqueia gravação) ─
# Grupos amplos conhecidos, para a DIAGNOSE (exposicao_grants) sinalizar exposição.
_GRUPOS_AMPLOS = ("account users", "users", "all users", "public")
_PRIV_LEITURA = ("SELECT", "ALL PRIVILEGES", "MODIFY")


def destino_seguro(spark: SparkSession, catalogo: str, schema: str,
                   principais_autorizados) -> tuple:
    """ALLOW-LIST (não denylist): o destino — que é um MAPA do dado sensível — só é
    seguro se TODO principal capaz de LER estiver na allow-list explícita
    (DPO/segurança). Checa:
    - grants de leitura no SCHEMA **e no CATÁLOGO** (grant de catálogo é HERDADO,
      lê todas as tabelas — o furo que o code-reviewer pegou);
    - os DONOS de schema e catálogo (owner contorna grant no UC).
    Qualquer principal fora da allow-list ⇒ RECUSA. Fail-closed se não verificar."""
    try:
        aut = {p.lower().strip() for p in (principais_autorizados or [])}
        priv = ", ".join(f"'{p}'" for p in _PRIV_LEITURA)

        # FURO FAIL-OPEN (security-lgpd): o information_schema do UC é ESCOPADO ao
        # chamador — quem não é dono do destino pode NÃO enxergar todos os grants
        # sobre ele, e a query não dá erro (só vêm menos linhas), então a
        # enumeração ficaria incompleta e passaria como "seguro". Exigimos que
        # quem roda seja DONO do catálogo E do schema de destino: só assim a lista
        # de leitores é confiável. Se nem o owner é visível, `donos` vem curto →
        # também recusa.
        usuario = (spark.sql("SELECT current_user()").collect()[0][0] or "").lower().strip()
        donos = spark.sql(f"""
          SELECT catalog_owner AS o FROM system.information_schema.catalogs
            WHERE catalog_name='{catalogo}'
          UNION ALL
          SELECT schema_owner FROM system.information_schema.schemata
            WHERE catalog_name='{catalogo}' AND schema_name='{schema}'
        """).collect()
        donos_set = {(r["o"] or "").lower().strip() for r in donos}
        if len(donos) < 2 or not donos_set.issubset({usuario}):
            return (False, f"Quem roda ({usuario}) precisa ser DONO do catálogo E do schema de "
                           f"destino ({catalogo}.{schema}). Sem isso, o Unity Catalog não expõe "
                           "todos os grants do destino ao chamador e a checagem de segurança "
                           "ficaria incompleta (fail-open). Use um catálogo+schema restrito de que "
                           "você é dono para gravar o mapa.")

        leitores = spark.sql(f"""
          SELECT grantee AS principal FROM system.information_schema.schema_privileges
            WHERE catalog_name='{catalogo}' AND schema_name='{schema}'
              AND privilege_type IN ({priv})
          UNION
          SELECT grantee FROM system.information_schema.catalog_privileges
            WHERE catalog_name='{catalogo}' AND privilege_type IN ({priv})
          UNION
          SELECT schema_owner FROM system.information_schema.schemata
            WHERE catalog_name='{catalogo}' AND schema_name='{schema}'
          UNION
          SELECT catalog_owner FROM system.information_schema.catalogs
            WHERE catalog_name='{catalogo}'
        """)
        fora = sorted({r["principal"] for r in leitores.collect()
                       if (r["principal"] or "").lower().strip() not in aut})
        if fora:
            return (False, f"Destino {catalogo}.{schema} tem principals com leitura FORA da "
                           f"allow-list (DPO/segurança): {', '.join(fora)}. O output é um mapa do "
                           "dado sensível — grave num schema onde só os autorizados leem (revogue "
                           "os demais, incluindo grants HERDADOS do catálogo e os donos).")
        return (True, f"Destino {catalogo}.{schema}: todos os leitores estão na allow-list")
    except Exception as e:
        # Fail-closed: sem conseguir VERIFICAR, não gravo o mapa às cegas.
        return (False, f"Não consegui verificar grants/donos do destino {catalogo}.{schema} — "
                       f"por segurança, não gravo sem confirmar que é restrito. Erro: {e}")


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
        # `.cast("string")`: um F.lit(None) cru é VoidType e quebra o saveAsTable.
        cand = (cand.withColumn("tag_name", F.lit(None).cast("string"))
                    .withColumn("tag_value", F.lit(None).cast("string")))
    return cand


def exposicao_grants(spark: SparkSession, candidatas: DataFrame) -> DataFrame:
    """Tabelas com PII expostas a um grupo AMPLO — em QUALQUER nível de herança:
    grant direto na tabela, ou no SCHEMA, ou no CATÁLOGO (grant de catálogo lê
    todas as tabelas). Ignorar a herança subnotificaria exposição — o falso-
    negativo perigoso numa ferramenta de LGPD. Uma linha por (tabela, grantee,
    nível). Metadado puro. `nivel` diz de onde vem a exposição."""
    from pyspark.sql import functions as F
    tabelas_pii = candidatas.select("table_catalog", "table_schema", "table_name").distinct()
    grupos = [g for g in _GRUPOS_AMPLOS]
    priv = ", ".join(f"'{p}'" for p in _PRIV_LEITURA)

    amplo_tab = spark.sql(f"""SELECT table_catalog, table_schema, table_name, grantee
        FROM system.information_schema.table_privileges WHERE privilege_type IN ({priv})""") \
        .filter(F.lower("grantee").isin(grupos)).distinct()
    amplo_sch = spark.sql(f"""SELECT catalog_name AS table_catalog, schema_name AS table_schema, grantee
        FROM system.information_schema.schema_privileges WHERE privilege_type IN ({priv})""") \
        .filter(F.lower("grantee").isin(grupos)).distinct()
    amplo_cat = spark.sql(f"""SELECT catalog_name AS table_catalog, grantee
        FROM system.information_schema.catalog_privileges WHERE privilege_type IN ({priv})""") \
        .filter(F.lower("grantee").isin(grupos)).distinct()

    cols = ["table_catalog", "table_schema", "table_name", "grantee", "nivel"]
    r_tab = tabelas_pii.join(amplo_tab, ["table_catalog", "table_schema", "table_name"]) \
        .withColumn("nivel", F.lit("tabela")).select(*cols)
    r_sch = tabelas_pii.join(amplo_sch, ["table_catalog", "table_schema"]) \
        .withColumn("nivel", F.lit("schema")).select(*cols)
    r_cat = tabelas_pii.join(amplo_cat, ["table_catalog"]) \
        .withColumn("nivel", F.lit("catalogo")).select(*cols)
    return r_tab.unionByName(r_sch).unionByName(r_cat)


def escanear(spark: SparkSession, catalogo_destino: str, schema_destino: str,
             principais_autorizados) -> dict:
    """Roda o Exposure Scan v1 (metadata-only) e grava DUAS camadas de saída num
    destino que ele CONFIRMA (por allow-list) ser restrito antes de escrever.
    `principais_autorizados`: os únicos principals que podem ler o output (DPO/
    segurança). Retorna resumo."""
    if not principais_autorizados or isinstance(principais_autorizados, str):
        # `isinstance str`: um set-comprehension sobre string itera CARACTERES —
        # a allow-list viraria {'d','p','o',...} e quase tudo cairia como não
        # autorizado (fail-closed, mas mascara erro de config). Exige lista/set.
        raise RuntimeError("[exposure_scan] principais_autorizados deve ser uma LISTA de "
                           "principals autorizados (não string) — allow-list de quem pode ler o "
                           "mapa do dado sensível. Não há default seguro.")
    ok, msg = _pode_ler_infoschema(spark)
    if not ok:
        raise RuntimeError(f"[exposure_scan] {msg}")

    # PORTÃO DE SEGURANÇA: não grava o mapa do tesouro se o destino for legível por
    # alguém fora da allow-list (inclui grants herdados do catálogo e os donos).
    seguro, motivo = destino_seguro(spark, catalogo_destino, schema_destino, principais_autorizados)
    if not seguro:
        raise RuntimeError(f"[exposure_scan] destino recusado — {motivo}")

    from pyspark.sql import functions as F
    cand = candidatas_pii(spark).cache()
    grants = exposicao_grants(spark, cand).cache()  # toda linha JÁ é exposição ampla
    base = f"{catalogo_destino}.{schema_destino}"

    # Furo nº2 (security-lgpd): um GRANT DIRETO numa tabela de saída de um run
    # anterior poderia sobreviver ao overwrite (semântica ambígua no UC). DROP
    # explícito zera os grants — a tabela nova herda só do schema já validado.
    for _t in ("pii_mapa", "grants_amplos", "resumo_executivo"):
        spark.sql(f"DROP TABLE IF EXISTS {base}.{_t}")

    # CAMADA 1 (RESTRITA) — mapa coluna-a-coluna. Sem valor de PII, só metadado.
    mapa = cand.select(
        "table_catalog", "table_schema", "table_name", "column_name",
        "data_type", "tier_confianca", "tag_name", "tag_value")
    mapa.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{base}.pii_mapa")

    grants.write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{base}.grants_amplos")

    # CAMADA 2 (CIRCULÁVEL) — só agregados/score, sem apontar coluna específica.
    resumo = {
        "colunas_candidatas_pii": cand.count(),
        "por_tier": {r["tier_confianca"]: r["c"] for r in
                     cand.groupBy("tier_confianca").agg(F.count("*").alias("c")).collect()},
        "tabelas_com_pii": cand.select("table_catalog", "table_schema", "table_name").distinct().count(),
        "tabelas_pii_com_grant_amplo": grants.select(
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
