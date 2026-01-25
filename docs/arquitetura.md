# Arquitetura FinOps Databricks

## Visão Geral

O framework FinOps Databricks é uma solução completa de assessment contínuo para otimização de custos e performance em workspaces Databricks multi-cloud.

## Arquitetura de Dados

### Camadas de Dados (Medalhão)

#### Bronze
Armazena métricas brutas coletadas diretamente das APIs:
- Compute: clusters, jobs, job runs
- Storage: tabelas, metadados, histórico de acesso
- Billing: custos diários por recurso

#### Silver
Métricas normalizadas e enriquecidas:
- Cálculos de utilização, idle time, scores
- Classificação de dados (hot/warm/cold)
- Normalização de custos para USD
- Flags de otimização

#### Gold
KPIs, scores e rankings:
- Maturity scores por dimensão
- Rankings de clusters e jobs
- Recomendações priorizadas
- Resumos agregados por workspace

## Componentes

### Coletores (Collectors)
- `compute_collector.py`: Clusters e Jobs via Databricks REST API
- `storage_collector.py`: Tabelas via Spark SQL (Unity Catalog ou Hive)
- `billing_collector.py`: Custos via Cloud APIs (Azure Cost Management, AWS Cost Explorer, GCP Billing)

### Processadores (Processors)
- `bronze_to_silver.py`: Normalização e enriquecimento
- `silver_to_gold.py`: Agregações e KPIs

### Analisadores (Analyzers)
- `finops_analyzer.py`: Cálculo de scores e geração de recomendações

## Fluxo de Dados

1. **Coleta**: Notebooks executam coletores via Jobs agendados
2. **Bronze**: Dados brutos salvos em Delta Lake
3. **Silver**: Processamento de normalização
4. **Gold**: Agregação e análise
5. **Análise**: Cálculo de maturity score e recomendações

## Suporte Multi-Cloud

### Azure Databricks
- Billing via Azure Cost Management API
- Detecção automática via URL pattern
- Suporte a Unity Catalog e Hive Metastore

### AWS Databricks
- Billing via AWS Cost Explorer API
- Detecção automática via URL pattern
- Suporte a Unity Catalog e Hive Metastore

### GCP Databricks
- Billing via GCP Billing API / BigQuery
- Detecção automática via URL pattern
- Suporte a Unity Catalog e Hive Metastore

## Metastore

### Unity Catalog
- Coleta via `SHOW CATALOGS` e navegação hierárquica
- Suporte completo a catálogos, schemas e tabelas

### Hive Metastore (Legado)
- Coleta via `SHOW DATABASES` e navegação tradicional
- Compatibilidade com ambientes legados

## Performance

- Particionamento por workspace e cloud
- Auto-optimize e auto-compact habilitados
- Processamento incremental quando possível
- Retenção configurável por camada
