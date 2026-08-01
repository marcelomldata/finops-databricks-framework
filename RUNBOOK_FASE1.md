# Runbook — testar a Fase 1 (custo real via system tables) no Azure Databricks

Objetivo: rodar o coletor de custo REAL num Azure Databricks e validar que as
queries batem com o schema do seu ambiente. Segue na ordem — os passos 0–2 evitam
os 4 modos de falha que o portão (skeptic) apontou.

---

## Pré-requisitos (o que precisa existir ANTES)

1. **Workspace com Unity Catalog.** System tables não existem em workspace só-Hive.
2. **System schemas habilitados.** `billing` costuma vir ligada; **`compute` e
   `lakeflow` normalmente precisam ser habilitadas explicitamente** pelo account
   admin. Habilitar (uma vez, por metastore) via API:
   ```bash
   # lista os schemas e o estado (ENABLE_COMPLETED / DISABLE...)
   databricks system-schemas list <METASTORE_ID>
   # habilita os que faltam
   databricks system-schemas enable <METASTORE_ID> compute
   databricks system-schemas enable <METASTORE_ID> lakeflow
   ```
3. **Grants** para o usuário/SP que vai rodar o notebook (concedido por account/
   metastore admin — NÃO rode como admin):
   ```sql
   GRANT USE CATALOG ON CATALOG system TO `quem_roda`;
   GRANT USE SCHEMA, SELECT ON SCHEMA system.billing  TO `quem_roda`;
   GRANT USE SCHEMA, SELECT ON SCHEMA system.compute   TO `quem_roda`;
   GRANT USE SCHEMA, SELECT ON SCHEMA system.lakeflow  TO `quem_roda`;
   ```
4. **Workspace com histórico REAL de uso.** ⚠ Ponto crítico do teste: um workspace
   **recém-criado retorna tudo zerado** — `system.billing.usage` tem latência de
   ingestão (horas a ~1 dia) e as tabelas não têm histórico. **Teste num workspace
   que já roda cargas há ≥24–48h.** Zero aqui é latência/ausência de dado, não bug.

---

## Passo 0 — Pré-check de schema (30 segundos, evita o run morrer no passo 1)

Rode num notebook/SQL editor ANTES do run cheio. Confirma que os campos que a
query assume existem neste runtime:
```sql
-- (a) is_photon existe no struct product_features? (a query-coração usa)
SELECT product_features.is_serverless, product_features.is_photon
FROM system.billing.usage LIMIT 1;

-- (b) o preço aninhado resolve?
SELECT sku_name, pricing.effective_list.`default`
FROM system.billing.list_prices LIMIT 1;

-- (c) as quatro tabelas respondem?
SELECT 'usage' t, count(*) c FROM system.billing.usage WHERE usage_date >= current_date()-INTERVAL 2 DAYS
UNION ALL SELECT 'prices', count(*) FROM system.billing.list_prices
UNION ALL SELECT 'node_timeline', count(*) FROM system.compute.node_timeline WHERE start_time >= current_date()-INTERVAL 2 DAYS
UNION ALL SELECT 'jobs', count(*) FROM system.lakeflow.jobs;
```
- Se **(a)** falhar em `is_photon` → me avise: removo `is_photon` do `real_cost.py`
  (SELECT + GROUP BY de `custo_real_por_recurso`). É o único campo não 100%
  confirmado na doc.
- Se **(c)** mostrar `usage`/`node_timeline` com contagem 0 → é o caso "workspace
  sem histórico"; use outro workspace ou espere o billing ingerir.

---

## Passo 1 — Instalar e rodar

No repo, dentro do Databricks (Repos):
```bash
pip install -r requirements.txt
pip install -e .            # torna `from src...` importável
```
Variáveis (opcionais, com defaults):
```bash
export FINOPS_DIAS=30                 # janela em dias (fechados, terminando ontem)
export FINOPS_MOEDA=USD               # código ISO 3 letras (list_prices é em USD)
export FINOPS_TAG_NEGOCIO=cost_center # opcional: chave de custom_tags p/ custo serverless
```
Rode o notebook **`notebooks/01_collect/00_collect_system_tables.py`**.

---

## Passo 2 — Ler a saída

O notebook imprime, por tabela, quantas linhas gravou; se alguma tabela falhou
(ex.: `lakeflow` sem grant), ela aparece como `⚠ FALHOU` **sem abortar as outras**.
Tabelas gold gravadas em `dbfs:/finops/gold/...`:
- `costs/real_usage` — custo e DBU por recurso/dia (+ `dbus_sem_preco` = cobertura)
- `costs/by_job` — custo por job (só job/serverless compute)
- `compute/utilization` — CPU/mem/idle por cluster (candidatos a downsizing)
- `costs/serverless_by_tag` — custo serverless por tag (se `FINOPS_TAG_NEGOCIO`)

---

## O que o número É e o que NÃO É (leia antes de comparar com a fatura)

- **É** o DBU do Databricks a **preço de lista** (`effective_list`), medido, por
  recurso e dia. É comparável à **linha Databricks** do consumo.
- **NÃO é** a fatura Azure total: falta VM/compute, storage e rede (o Azure fatura
  à parte, fora das system tables). O total costuma ser **~2× o DBU**.
- **NÃO reflete** descontos de commit/negociados nem câmbio (list_prices em USD).
- Se `dbus_sem_preco` for alto, há SKU sem preço casado na janela — cobertura
  parcial, e o relatório deve dizer isso.

---

## Segurança / LGPD (do parecer security-lgpd)

- `costs/serverless_by_tag` pode conter identificador **se** você usa pessoa como
  valor de tag. Trate essa gold com **acesso restrito** (grant UC só a quem precisa),
  não legível pelo workspace inteiro.
- Nada sai do ambiente: todo o processamento é Spark SQL local, sem chamada externa.

---

## Me devolva do teste

1. A saída impressa do notebook (contagens + eventuais `⚠ FALHOU`).
2. Resultado do Passo 0 (principalmente se `is_photon` falhou).
3. Um `SELECT * FROM delta.\`dbfs:/finops/gold/costs/real_usage\` ORDER BY cost DESC LIMIT 20`
   — pra eu ver se os números fazem sentido e ajustar.

Com isso eu corrijo o que o ambiente real revelar e seguimos pra Fase 2 (o relatório
+ matriz de priorização em cima destas tabelas).
