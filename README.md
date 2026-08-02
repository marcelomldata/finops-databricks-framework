# FinOps Databricks Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5%2B-orange.svg)](https://spark.apache.org/)

Framework **open source de assessment de FinOps** para Databricks. Coleta métricas do
workspace, organiza em arquitetura medalhão (bronze/silver/gold), calcula um score de
maturidade e gera **recomendações acionáveis** — para **priorizar onde otimizar custo**.
Não substitui a fatura da nuvem nem é veredito de conformidade: é um levantamento para
decidir onde agir primeiro.

> **Estado honesto (atualizado em 2026-08):** o núcleo de assessment (coleta → medalhão →
> score → recomendações → relatório) é **executável e testado** nas partes puras. O **motor
> de custo medido** (via `system.billing.usage`) e a **atribuição por modelo dbt** estão
> **implementados, mas ainda não validados num Databricks de produção** — tratados aqui como
> "prontos para validação", não como resultado garantido. Preferimos declarar isso a inflar.

## O que é real hoje (executável)

- **Arquitetura medalhão** bronze/silver/gold, com o fluxo coleta → processamento → análise
  → revalidação, ponta a ponta em notebooks.
- **Coleta** de clusters, jobs, runs e storage via API/SQL do Databricks.
- **Estimativa de custo DBU** por `uptime × taxa` — declarada como **estimativa** (não
  medição): a fatura real depende de preço negociado e descontos.
- **Motor de custo medido** via `system.billing.usage × system.billing.list_prices`
  (utilização por `system.compute.node_timeline`, custo por job via `system.lakeflow`), com
  as limitações escritas no próprio código: DBU a **preço de lista** (tipicamente abaixo do
  total faturado), janela de retenção das system tables, e um campo de **cobertura** para o
  que ficou sem preço. *Implementado; a validar em ambiente cliente.*
- **Atribuição de custo por modelo dbt e por tag** — cruza o `statement_id` do
  `system.query.history` (hoje em **Public Preview**) com o comentário que o dbt injeta na
  query, atribuindo o custo do warehouse ao modelo que o gerou. *Método implementado; a
  validar em ambiente real.*
- **Baseline versionado** — compara maturidade e custo entre períodos.
- **Recomendações acionáveis** ancoradas ao recurso, com comandos de automação
  **não-executáveis por padrão** (`can_execute=False`, exigindo aprovação): o framework
  **sugere e mostra o comando + o rollback**. Há um modo `auto` **opt-in** (desligado por
  padrão) que pode marcar `can_execute=True` para ações de baixo risco.
- **Relatório técnico** (Markdown/HTML autocontido) com matriz **Desperdício × Esforço ×
  Risco**, SWOT executivo e seção de **metodologia e limitações**.
- **Testes de unidade** das fórmulas puras (custo, alocação, parser de tags, thresholds) que
  rodam **sem Spark**.

## Limites honestos (declarados de propósito — é o que torna a ferramenta crível)

- O custo "real" via system tables é **DBU a preço de lista**: não inclui desconto de
  contrato/compromisso. Use como **ordem de grandeza e tendência**, não como valor de fatura.
- A **atribuição por pipeline/produto/SLA** depende de **convenção de nome de job / tags**.
  Onde não há convenção, é **heurística explícita** (marcada como tal na saída), não medição.
- A **atribuição de custo por job** cobre **jobs e serverless compute**; job rodando em
  **all-purpose compute** não é faturado como job e cai na heurística de nome/tag, não na
  medição por job.
- Os limiares de nível (bom/médio/ruim) são **referências heurísticas internas — NÃO
  benchmark de indústria** (não há fonte pública citável; são ponto de partida configurável).
- O motor de custo medido e a atribuição dbt **ainda não foram executados contra um
  Databricks de produção** — a validação em ambiente real é a próxima frente (ver Roadmap).
- Exige **Unity Catalog** para o motor de custo real (as system tables são UC-only); o
  caminho Hive Metastore cobre só a coleta básica.

## Roadmap (ainda NÃO pronto — declarado como tal)

- **Validação do motor de custo medido** e da atribuição dbt em ambiente cliente real.
- **Reconciliação estimado × faturado** com a API de billing da nuvem (Azure Cost Management
  / AWS Cost Explorer / GCP Billing) — hoje condicional à ingestão dessa fonte.
- **Benchmarks externos** com fonte citável (hoje são heurísticos internos).
- **Automação recorrente multi-workspace** end-to-end e alertas contínuos.
- **Observabilidade** aprofundada (hoje é agregação simples de falhas/performance).

## Arquitetura

**Camadas de dados** — Bronze (bruto coletado) → Silver (normalizado/enriquecido) → Gold
(KPIs, scores, rankings). **Dimensões** — Compute (clusters & jobs), Storage (Delta),
Governança & Qualidade, Pipelines & Orquestração, Custos & Billing. **Multi-cloud** — Azure,
AWS e GCP (a detecção é real; as taxas DBU default são iguais entre nuvens — ajuste às suas).
**Multi-metastore** — Unity Catalog (necessário para o custo real) e Hive (coleta básica).

```
finops-databricks-framework/
├── src/                  # collectors, processors, analyzers, auditors, utils, reporting
├── notebooks/            # 01_collect, 02_process, 03_analyze, 04_revalidate
├── sql/ddl/              # definições de tabela (ilustrativas)
├── tests/                # testes das fórmulas puras (sem Spark)
├── config/  docs/  LICENSE  ROADMAP.md
```

## Instalação

```bash
pip install -r requirements.txt
pip install -e .                          # torna `from src...` importável nos notebooks
pip install -r requirements-billing.txt   # opcional: SDKs de billing das nuvens
cp env.example .env                        # configure credenciais/workspaces
```

Depois: execute os DDLs em `sql/ddl/`, rode os notebooks de coleta → processamento →
análise. Guia passo a passo em [docs/QUICK_START.md](docs/QUICK_START.md) e
[docs/HOW_TO.md](docs/HOW_TO.md).

## O que é aberto e o que é serviço

**Aberto (este repositório, Apache 2.0):** toda a arquitetura, o modelo de dados, os scripts
de coleta (inclusive os coletores de billing das nuvens), as regras de diagnóstico, o motor
de custo (estimado e medido), a atribuição por dbt/tag, o baseline e o relatório técnico.

**Serviço profissional (ML Data e IA):** a **implementação e validação em ambiente real**, a
calibração da reconciliação com a fatura da nuvem, os playbooks de correção profunda
(reescrita de pipeline, particionamento, refatoração de join) e os dashboards executivos.
Não é "código escondido" — é o **trabalho de aplicar e validar** o framework no seu ambiente.

## Precisa implementar, validar e agir sobre o diagnóstico?

Rodar o assessment, **validar as estimativas contra a sua fatura real** e executar a
otimização é o trabalho da **[ML Data e IA](mailto:marcelo@mldata.com.br)**.

## Contribuindo · Licença

Contribuições bem-vindas ([CONTRIBUTING.md](CONTRIBUTING.md)). Licenciado sob
[Apache License 2.0](LICENSE). Roadmap público em [ROADMAP.md](ROADMAP.md).

Contato: marcelo@mldata.com.br
