"""
05 — Exposure Scan (LGPD), v1 metadata-only.

Mapeia exposição de dado pessoal por METADADO (nome de coluna, tags, grants) —
NÃO lê valor de dado. Grava duas camadas de saída num destino que a ferramenta
CONFIRMA ser restrito antes de escrever (o output é um mapa do dado sensível).

⚠ O DESTINO precisa ser um schema RESTRITO (grant default-deny, allow-list só do
DPO/segurança). A ferramenta RECUSA gravar se detectar grant amplo no destino.
⚠ Rode como principal de MENOR privilégio (SELECT no information_schema) —
   NUNCA como metastore admin.
⚠ O cliente é o controlador LGPD. Finalidade única: avaliação de exposição para
   remediação. Matches são CANDIDATOS; a confirmação é o handoff (DPO-as-a-Service).
"""
from pyspark.sql import SparkSession
from src.governance.exposure_scan import escanear
import os

spark = SparkSession.builder.appName("FinOps_ExposureScan").getOrCreate()

# Destino OBRIGATÓRIO e restrito — sem default para lugar público de propósito.
catalogo = os.getenv("EXPOSURE_CATALOGO")
schema = os.getenv("EXPOSURE_SCHEMA")
if not catalogo or not schema:
    raise ValueError(
        "Defina EXPOSURE_CATALOGO e EXPOSURE_SCHEMA apontando para um schema RESTRITO "
        "(legível só pelo DPO/segurança). O output é um mapa do dado sensível — não pode "
        "ir para um schema público.")

r = escanear(spark, catalogo, schema)

print(f"Exposure Scan gravado em {r['destino']} (3 tabelas):")
print("  - resumo_executivo : agregados/score — CIRCULÁVEL")
print("  - pii_mapa         : coluna-a-coluna — RESTRITO (mapa do dado sensível)")
print("  - grants_amplos    : tabelas com PII e grant amplo — RESTRITO")
print("\nResumo:")
for k, v in r["resumo"].items():
    print(f"  {k}: {v}")
print(f"\n{r['aviso']}")
