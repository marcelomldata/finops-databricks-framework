# Modelo de Dados FinOps - Documentação Completa

## Visão Geral

O modelo de dados segue arquitetura medalhão (Bronze/Silver/Gold) com particionamento otimizado para consultas e processamento incremental.

## Camada Bronze

### finops_bronze.compute_clusters

**Descrição:** Métricas brutas de clusters coletadas via Databricks REST API.

**Particionamento:** `workspace_name`, `cloud`

**Campos Principais:**
- `workspace_name` (STRING) - Nome do workspace
- `workspace_url` (STRING) - URL do workspace
- `cloud` (STRING) - Azure, AWS ou GCP
- `cluster_id` (STRING) - ID único do cluster
- `cluster_name` (STRING) - Nome do cluster
- `state` (STRING) - Estado (RUNNING, TERMINATED, etc.)
- `spark_version` (STRING) - Versão do Spark
- `node_type_id` (STRING) - Tipo de nó
- `num_workers` (INT) - Número de workers
- `cluster_memory_mb` (DOUBLE) - Memória total em MB
- `start_time` (BIGINT) - Timestamp de início
- `last_activity_time` (BIGINT) - Última atividade
- `collect_timestamp` (TIMESTAMP) - Quando foi coletado

**Exemplo de Dados:**
```sql
SELECT * FROM finops_bronze.compute_clusters
WHERE workspace_name = 'workspace_prod'
    AND collect_timestamp >= CURRENT_DATE - INTERVAL 7 DAYS
LIMIT 10;
```

### finops_bronze.compute_jobs

**Descrição:** Configuração de jobs coletada via Databricks REST API.

**Particionamento:** `workspace_name`, `cloud`

**Campos Principais:**
- `workspace_name` (STRING)
- `job_id` (INT) - ID único do job
- `job_name` (STRING) - Nome do job
- `job_type` (STRING) - Tipo do job
- `schedule` (STRING) - Configuração de schedule (JSON)
- `new_cluster` (STRING) - Configuração de novo cluster (JSON)
- `existing_cluster_id` (STRING) - ID do cluster existente
- `collect_timestamp` (TIMESTAMP)

**Exemplo de Dados:**
```sql
SELECT 
    job_id,
    job_name,
    CASE 
        WHEN schedule != 'null' THEN 'Agendado'
        ELSE 'Manual'
    END AS tipo_execucao
FROM finops_bronze.compute_jobs
WHERE workspace_name = 'workspace_prod';
```

### finops_bronze.compute_job_runs

**Descrição:** Histórico de execuções de jobs.

**Particionamento:** `workspace_name`, `cloud`

**Campos Principais:**
- `workspace_name` (STRING)
- `job_id` (INT)
- `run_id` (BIGINT) - ID único da execução
- `state` (STRING) - Estado da execução
- `result_state` (STRING) - Resultado (SUCCESS, FAILED, etc.)
- `start_time` (BIGINT) - Timestamp de início
- `end_time` (BIGINT) - Timestamp de fim
- `execution_duration` (BIGINT) - Duração em ms
- `error` (STRING) - Erro se falhou (JSON)
- `collect_timestamp` (TIMESTAMP)

**Exemplo de Dados:**
```sql
SELECT 
    job_id,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN result_state = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_runs,
    AVG(execution_duration / 1000.0 / 60.0) AS avg_duration_minutes
FROM finops_bronze.compute_job_runs
WHERE workspace_name = 'workspace_prod'
    AND start_time >= UNIX_TIMESTAMP(CURRENT_DATE - INTERVAL 30 DAYS) * 1000
GROUP BY job_id;
```

### finops_bronze.storage_tables

**Descrição:** Metadados de tabelas coletados via Spark SQL.

**Particionamento:** `workspace_name`, `cloud`

**Campos Principais:**
- `workspace_name` (STRING)
- `metastore_type` (STRING) - unity_catalog ou hive
- `catalog` (STRING) - Catálogo (Unity Catalog)
- `schema` (STRING) - Schema/Database
- `table_name` (STRING) - Nome da tabela
- `full_table_name` (STRING) - Nome completo
- `table_type` (STRING) - delta, parquet, etc.
- `location` (STRING) - Localização no storage
- `num_files` (INT) - Número de arquivos
- `size_in_bytes` (BIGINT) - Tamanho em bytes
- `partition_columns` (STRING) - Colunas de particionamento
- `last_modified` (TIMESTAMP) - Última modificação
- `last_access` (TIMESTAMP) - Último acesso
- `collect_timestamp` (TIMESTAMP)

**Exemplo de Dados:**
```sql
SELECT 
    full_table_name,
    size_in_bytes / 1024 / 1024 / 1024 AS size_gb,
    num_files,
    days_since_accessed
FROM finops_bronze.storage_tables
WHERE workspace_name = 'workspace_prod'
    AND size_in_bytes > 1073741824  -- > 1 GB
ORDER BY size_in_bytes DESC
LIMIT 20;
```

### finops_bronze.billing_costs

**Descrição:** Custos coletados via Cloud Billing APIs.

**Particionamento:** `workspace_name`, `cloud`, `date`

**Campos Principais:**
- `workspace_name` (STRING)
- `cloud` (STRING)
- `date` (STRING) - Data no formato YYYY-MM-DD
- `resource_id` (STRING) - ID do recurso
- `resource_type` (STRING) - Tipo do recurso
- `service` (STRING) - Serviço cloud
- `cost` (DOUBLE) - Custo
- `currency` (STRING) - Moeda
- `collect_timestamp` (TIMESTAMP)

**Exemplo de Dados:**
```sql
SELECT 
    date,
    SUM(cost) AS daily_cost,
    currency
FROM finops_bronze.billing_costs
WHERE workspace_name = 'workspace_prod'
    AND date >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY date, currency
ORDER BY date DESC;
```

## Camada Silver

### finops_silver.compute_clusters

**Descrição:** Clusters com métricas calculadas e enriquecidas.

**Campos Adicionais (além dos do Bronze):**
- `is_running` (BOOLEAN) - Está rodando?
- `is_terminated` (BOOLEAN) - Está terminado?
- `has_autoscaling` (BOOLEAN) - Tem autoscaling?
- `uptime_hours` (DOUBLE) - Horas de uptime
- `idle_hours` (DOUBLE) - Horas ociosas
- `memory_gb` (DOUBLE) - Memória em GB
- `estimated_cost_per_hour` (DOUBLE) - Custo estimado/hora
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    cluster_name,
    num_workers,
    memory_gb,
    uptime_hours,
    idle_hours,
    CASE 
        WHEN idle_hours > 4 THEN 'Ocioso'
        WHEN idle_hours > 2 THEN 'Subutilizado'
        ELSE 'Ativo'
    END AS status
FROM finops_silver.compute_clusters
WHERE workspace_name = 'workspace_prod'
    AND is_running = true
ORDER BY idle_hours DESC;
```

### finops_silver.storage_tables

**Descrição:** Tabelas com métricas calculadas.

**Campos Adicionais:**
- `size_gb` (DOUBLE) - Tamanho em GB
- `size_tb` (DOUBLE) - Tamanho em TB
- `avg_file_size_mb` (DOUBLE) - Tamanho médio de arquivo
- `days_since_modified` (INT) - Dias desde modificação
- `days_since_accessed` (INT) - Dias desde acesso
- `is_partitioned` (BOOLEAN) - Está particionada?
- `is_delta` (BOOLEAN) - É Delta Lake?
- `has_small_files` (BOOLEAN) - Tem arquivos pequenos?
- `is_cold_data` (BOOLEAN) - É dado frio?
- `is_abandoned` (BOOLEAN) - Está abandonada?

**Exemplo de Uso:**
```sql
SELECT 
    full_table_name,
    size_tb,
    num_files,
    avg_file_size_mb,
    CASE 
        WHEN is_abandoned THEN 'Abandonada'
        WHEN is_cold_data THEN 'Fria'
        ELSE 'Ativa'
    END AS status,
    days_since_accessed
FROM finops_silver.storage_tables
WHERE workspace_name = 'workspace_prod'
    AND (is_abandoned = true OR is_cold_data = true)
ORDER BY size_tb DESC;
```

## Camada Gold

### finops_gold.compute_clusters_summary

**Descrição:** Resumo de clusters com rankings e scores.

**Campos Principais:**
- `workspace_name` (STRING)
- `cluster_id` (STRING)
- `cluster_name` (STRING)
- `num_workers` (INT)
- `memory_gb` (DOUBLE)
- `uptime_hours` (DOUBLE)
- `idle_hours` (DOUBLE)
- `is_idle` (BOOLEAN) - Ocioso > 4 horas
- `is_overprovisioned` (BOOLEAN) - Overprovisionado
- `utilization_score` (DOUBLE) - Score de utilização (0-1)
- `has_autoscaling` (BOOLEAN)
- `rank_by_uptime` (INT) - Ranking por uptime
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    cluster_name,
    num_workers,
    uptime_hours,
    utilization_score,
    CASE 
        WHEN utilization_score >= 0.8 THEN 'Otimizado'
        WHEN utilization_score >= 0.6 THEN 'Bom'
        WHEN utilization_score >= 0.4 THEN 'Regular'
        ELSE 'Ruim'
    END AS classificacao
FROM finops_gold.compute_clusters_summary
WHERE workspace_name = 'workspace_prod'
ORDER BY utilization_score ASC
LIMIT 10;
```

### finops_gold.compute_jobs_summary

**Descrição:** Resumo de jobs com métricas agregadas.

**Campos Principais:**
- `workspace_name` (STRING)
- `job_id` (INT)
- `job_name` (STRING)
- `total_runs` (BIGINT) - Total de execuções
- `successful_runs` (BIGINT) - Execuções bem-sucedidas
- `failed_runs` (BIGINT) - Execuções falhadas
- `avg_duration_hours` (DOUBLE) - Duração média
- `success_rate` (DOUBLE) - Taxa de sucesso (0-1)
- `failure_rate` (DOUBLE) - Taxa de falha (0-1)
- `efficiency_score` (DOUBLE) - Score de eficiência (0-1)
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    job_name,
    total_runs,
    success_rate,
    failure_rate,
    avg_duration_hours,
    CASE 
        WHEN failure_rate > 0.2 THEN 'Crítico'
        WHEN failure_rate > 0.1 THEN 'Atenção'
        ELSE 'OK'
    END AS status
FROM finops_gold.compute_jobs_summary
WHERE workspace_name = 'workspace_prod'
    AND total_runs > 10
ORDER BY failure_rate DESC;
```

### finops_gold.storage_tables_summary

**Descrição:** Resumo de tabelas com classificações.

**Campos Principais:**
- `workspace_name` (STRING)
- `full_table_name` (STRING)
- `size_gb` (DOUBLE)
- `size_tb` (DOUBLE)
- `num_files` (INT)
- `avg_file_size_mb` (DOUBLE)
- `days_since_accessed` (INT)
- `is_partitioned` (BOOLEAN)
- `is_delta` (BOOLEAN)
- `has_small_files` (BOOLEAN)
- `is_cold_data` (BOOLEAN)
- `is_abandoned` (BOOLEAN)
- `storage_tier` (STRING) - hot, warm, cold
- `optimization_priority` (STRING) - high, medium, low
- `estimated_savings_gb` (DOUBLE) - Economia estimada
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    full_table_name,
    size_tb,
    storage_tier,
    optimization_priority,
    estimated_savings_gb,
    CASE 
        WHEN optimization_priority = 'high' THEN 'Ação Imediata'
        WHEN optimization_priority = 'medium' THEN 'Planejar Ação'
        ELSE 'Monitorar'
    END AS acao
FROM finops_gold.storage_tables_summary
WHERE workspace_name = 'workspace_prod'
    AND optimization_priority IN ('high', 'medium')
ORDER BY estimated_savings_gb DESC;
```

### finops_gold.storage_workspace_summary

**Descrição:** Resumo agregado de storage por workspace.

**Campos Principais:**
- `workspace_name` (STRING)
- `total_tables` (BIGINT) - Total de tabelas
- `total_size_tb` (DOUBLE) - Tamanho total
- `cold_size_tb` (DOUBLE) - Tamanho de dados frios
- `abandoned_size_tb` (DOUBLE) - Tamanho de dados abandonados
- `small_files_size_tb` (DOUBLE) - Tamanho com small files
- `total_schemas` (BIGINT) - Total de schemas
- `avg_file_size_mb` (DOUBLE) - Tamanho médio de arquivo
- `cold_data_percentage` (DOUBLE) - % de dados frios
- `abandoned_data_percentage` (DOUBLE) - % de dados abandonados
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    workspace_name,
    total_tables,
    total_size_tb,
    cold_data_percentage,
    abandoned_data_percentage,
    CASE 
        WHEN cold_data_percentage > 30 THEN 'Alto'
        WHEN cold_data_percentage > 15 THEN 'Médio'
        ELSE 'Baixo'
    END AS risco_dados_frios
FROM finops_gold.storage_workspace_summary
ORDER BY cold_data_percentage DESC;
```

### finops_gold.maturity_scores

**Descrição:** Maturity scores calculados por workspace.

**Campos Principais:**
- `workspace_name` (STRING)
- `maturity_score` (DOUBLE) - Score geral (0-1)
- `maturity_level` (STRING) - Básico, Intermediário, Avançado, Otimizado
- `compute_score` (DOUBLE) - Score de compute (0-1)
- `storage_score` (DOUBLE) - Score de storage (0-1)
- `governance_score` (DOUBLE) - Score de governança (0-1)
- `pipelines_score` (DOUBLE) - Score de pipelines (0-1)
- `observability_score` (DOUBLE) - Score de observabilidade (0-1)
- `costs_score` (DOUBLE) - Score de custos (0-1)
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    workspace_name,
    maturity_score,
    maturity_level,
    compute_score,
    storage_score,
    governance_score,
    process_timestamp
FROM finops_gold.maturity_scores
WHERE workspace_name = 'workspace_prod'
ORDER BY process_timestamp DESC
LIMIT 1;
```

### finops_gold.recommendations

**Descrição:** Recomendações priorizadas geradas.

**Campos Principais:**
- `workspace_name` (STRING)
- `category` (STRING) - compute, storage, pipelines
- `priority` (STRING) - high, medium, low
- `title` (STRING) - Título da recomendação
- `description` (STRING) - Descrição detalhada
- `impact` (STRING) - Alto, Médio, Baixo
- `complexity` (STRING) - Alta, Média, Baixa
- `action` (STRING) - Ação recomendada
- `estimated_savings` (STRING) - Economia estimada
- `process_timestamp` (TIMESTAMP)

**Exemplo de Uso:**
```sql
SELECT 
    title,
    category,
    priority,
    impact,
    complexity,
    action,
    estimated_savings
FROM finops_gold.recommendations
WHERE workspace_name = 'workspace_prod'
ORDER BY 
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    category;
```

## Relacionamentos entre Tabelas

```
finops_bronze.compute_clusters
    ↓ (processamento)
finops_silver.compute_clusters
    ↓ (agregação)
finops_gold.compute_clusters_summary

finops_bronze.compute_jobs
    ↓ (processamento)
finops_silver.compute_jobs
    ↓ (agregação)
finops_gold.compute_jobs_summary

finops_bronze.compute_job_runs
    ↓ (processamento)
finops_silver.compute_job_runs
    ↓ (agregação)
finops_gold.compute_jobs_summary (via job_id)

finops_bronze.storage_tables
    ↓ (processamento)
finops_silver.storage_tables
    ↓ (agregação)
finops_gold.storage_tables_summary
    ↓ (agregação workspace)
finops_gold.storage_workspace_summary
```

## Particionamento e Performance

### Estratégia de Particionamento

**Bronze:**
- Particionado por `workspace_name` e `cloud`
- Permite queries eficientes por workspace
- Facilita limpeza de dados antigos

**Silver:**
- Particionado por `workspace_name` e `cloud`
- Mantém alinhamento com Bronze
- Facilita processamento incremental

**Gold:**
- Particionado por `workspace_name`
- Otimizado para consultas analíticas
- Facilita comparações entre workspaces

### Otimizações Aplicadas

- **Auto-optimize**: Habilitado em todas as tabelas
- **Auto-compact**: Habilitado em todas as tabelas
- **Z-ORDER**: Aplicado em colunas de filtro frequente
- **Bloom Filters**: Para joins eficientes

## Retenção de Dados

### Bronze
- **Retenção**: 90 dias (configurável)
- **Razão**: Dados brutos, alto volume

### Silver
- **Retenção**: 90 dias (configurável)
- **Razão**: Dados processados, volume médio

### Gold
- **Retenção**: Indefinida (apenas última versão)
- **Razão**: Dados agregados, baixo volume, histórico importante

## Limites e Considerações

### Limites Técnicos

- **Tamanho máximo de tabela**: Sem limite prático (Delta Lake)
- **Número de partições**: Recomendado < 10.000
- **Frequência de coleta**: Mínimo 1x por dia
- **Retenção mínima**: 30 dias para análises comparativas

### Limites de Open Source

✅ **Incluído:**
- Modelo de dados completo
- DDLs de todas as tabelas
- Queries de exemplo
- Documentação completa

❌ **Não Incluído (Premium):**
- Otimizações avançadas de performance
- Particionamento customizado por negócio
- Retenção configurável por domínio
- Modelos de dados estendidos

## Dicionário de Dados Completo

Ver [DICIONARIO_DADOS.md](DICIONARIO_DADOS.md) para detalhes completos de todos os campos.
