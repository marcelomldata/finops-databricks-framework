# HOW TO - FinOps Databricks Assessment Framework

## Índice

1. [Assessment Inicial](#assessment-inicial)
2. [Revalidação Contínua](#revalidação-contínua)
3. [Interpretação de Scores](#interpretação-de-scores)
4. [Priorização de Ações](#priorização-de-ações)
5. [Aplicação de Correções](#aplicação-de-correções)
6. [Medição de Ganhos](#medição-de-ganhos)
7. [Automação do Ciclo Contínuo](#automação-do-ciclo-contínuo)

---

## Assessment Inicial

### Pré-requisitos

1. Workspace Databricks configurado
2. Permissões de leitura nas APIs
3. Variáveis de ambiente configuradas
4. Tabelas Delta criadas (DDLs executados)

### Passo 1: Configuração

**Opção 1: Arquivo .env (Recomendado)**

```bash
# Copiar template (versão simples)
cp env.example .env

# OU copiar template detalhado com instruções
cp config/example.env .env

# Editar .env com suas credenciais reais
# ⚠️ IMPORTANTE: NUNCA commite o arquivo .env!
```

**Opção 2: Variáveis de Ambiente**

```bash
# Configurar variáveis de ambiente diretamente
export WORKSPACE_NAME="workspace_prod"
export WORKSPACE_URL="https://adb-xxxxx.azuredatabricks.net"
export DATABRICKS_TOKEN="dapi..."
```

**Segurança:**
- O arquivo `.env` está no `.gitignore` e não será versionado
- Padrões de segurança bloqueiam automaticamente arquivos sensíveis
- Para produção, use Azure Key Vault, AWS Secrets Manager ou GCP Secret Manager

### Passo 2: Executar Coleta

```python
# Executar notebooks de coleta em sequência
# 1. Compute
notebooks/01_collect/01_collect_compute.py

# 2. Storage
notebooks/01_collect/02_collect_storage.py

# 3. Billing
notebooks/01_collect/03_collect_billing.py
```

### Passo 3: Processar Dados

```python
# Bronze → Silver
notebooks/02_process/01_process_bronze_to_silver.py

# Silver → Gold
notebooks/02_process/02_process_silver_to_gold.py
```

### Passo 4: Calcular Custos DBU

```python
# Calcular custos DBU estimados
notebooks/02_process/03_calculate_dbu_costs.py
```

### Passo 5: Gerar Análise

```python
# Calcular Maturity Score
notebooks/03_analyze/01_calculate_maturity_score.py

# Gerar Recomendações
notebooks/03_analyze/02_generate_recommendations.py

# Criar Baseline (recomendado após primeiro assessment)
notebooks/03_analyze/03_create_baseline.py
```

### Passo 6: Consultar Resultados

```sql
-- Maturity Score
SELECT * FROM finops_gold.maturity_scores
WHERE workspace_name = 'workspace_prod'
ORDER BY process_timestamp DESC
LIMIT 1;

-- Custos DBU Estimados
SELECT 
    cluster_name,
    cluster_type,
    num_workers,
    estimated_monthly_cost,
    estimated_dbu_cost
FROM finops_gold.costs_dbu_estimates
WHERE workspace_name = 'workspace_prod'
ORDER BY estimated_monthly_cost DESC;

-- Baseline Criado
SELECT * FROM finops_gold.assessment_baselines
WHERE workspace_name = 'workspace_prod'
ORDER BY baseline_date DESC
LIMIT 1;

-- Recomendações
SELECT * FROM finops_gold.recommendations
WHERE workspace_name = 'workspace_prod'
ORDER BY 
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END;
```

---

## Revalidação Contínua

### Quando Executar

- Semanalmente: Para workspaces críticos
- Mensalmente: Para workspaces padrão
- Após mudanças significativas: Novos clusters, jobs, tabelas

### Passo 1: Definir Baseline

```python
# Baseline é a data do último assessment
# Padrão: 30 dias atrás
export BASELINE_DAYS=30
```

### Passo 2: Executar Revalidação

```python
# Executar notebook de revalidação
notebooks/04_revalidate/01_run_revalidation.py
```

### Passo 3: Analisar Resultados

```sql
-- Relatório Executivo
SELECT * FROM finops_gold.revalidation_executive_reports
WHERE workspace_name = 'workspace_prod'
ORDER BY report_date DESC
LIMIT 1;

-- Quick Wins
SELECT * FROM finops_gold.revalidation_quick_wins
WHERE workspace_name = 'workspace_prod'
ORDER BY estimated_savings_usd_month DESC;

-- Status de Recomendações
SELECT 
    recommendation_title,
    status,
    priority
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(recommendations_status) AS rec
WHERE workspace_name = 'workspace_prod';
```

### Passo 4: Identificar Regressões

```sql
-- Recomendações que regrediram
SELECT 
    recommendation_title,
    category,
    priority
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(recommendations_status) AS rec
WHERE workspace_name = 'workspace_prod'
    AND rec.status = 'regressão';
```

---

## Interpretação de Scores

### Maturity Score

#### Escala (0.0 - 1.0)

- **0.8 - 1.0**: Otimizado
  - Todas as dimensões bem otimizadas
  - Processos maduros
  - Foco em refinamento contínuo

- **0.6 - 0.8**: Avançado
  - Maioria das dimensões otimizadas
  - Algumas melhorias necessárias
  - Processos estabelecidos

- **0.4 - 0.6**: Intermediário
  - Algumas dimensões otimizadas
  - Oportunidades claras de melhoria
  - Processos em evolução

- **0.0 - 0.4**: Básico
  - Poucas dimensões otimizadas
  - Muitas oportunidades de melhoria
  - Processos iniciais

### Dimensões

#### Compute Score
- Utilização de clusters
- Taxa de clusters ociosos
- Configuração de autoscaling
- Eficiência de jobs

#### Storage Score
- Taxa de particionamento
- Otimização (ausência de small files)
- Limpeza (ausência de dados abandonados)

#### Governance Score
- Uso de Unity Catalog
- Ownership de tabelas
- Tags e metadados

#### Pipelines Score
- Taxa de jobs agendados
- Taxa de sucesso
- Eficiência

#### Observability Score
- Cobertura de tags
- Qualidade de metadados

#### Costs Score
- Tendência de custos
- Eficiência de alocação

---

## Priorização de Ações

### Critérios de Priorização

1. **Severidade**: Alta, Média, Baixa
2. **Impacto Financeiro**: Economia estimada
3. **Complexidade**: Baixa, Média, Alta
4. **Esforço**: Horas estimadas

### Matriz de Priorização

| Severidade | Impacto | Prioridade | Ação |
|------------|---------|------------|------|
| Alta | Alto | P0 | Imediata |
| Alta | Médio | P1 | Curto prazo |
| Média | Alto | P1 | Curto prazo |
| Média | Médio | P2 | Médio prazo |
| Baixa | Alto | P2 | Médio prazo |
| Baixa | Médio/Baixo | P3 | Longo prazo |

### Consultar Backlog Priorizado

```sql
SELECT 
    priority,
    category,
    issue,
    action,
    estimated_savings_usd_month,
    complexity,
    effort_hours
FROM finops_gold.revalidation_prioritized_backlog
WHERE workspace_name = 'workspace_prod'
ORDER BY priority ASC, estimated_savings_usd_month DESC;
```

### Quick Wins

Focar primeiro em quick wins:
- Alto impacto financeiro
- Baixa complexidade
- Baixo esforço

```sql
SELECT * FROM finops_gold.revalidation_quick_wins
WHERE workspace_name = 'workspace_prod'
ORDER BY estimated_savings_usd_month DESC
LIMIT 10;
```

---

## Aplicação de Correções

### Compute

#### Desligar Clusters Ociosos

```python
# Via Databricks API
from src.utils.databricks_client import DatabricksAPIClient, DatabricksConfig

config = DatabricksConfig(
    host=workspace_url,
    token=databricks_token
)
client = DatabricksAPIClient(config)

# Terminar cluster
client._request("POST", f"clusters/delete", json={"cluster_id": cluster_id})
```

#### Configurar Autoscaling

```python
# Atualizar cluster com autoscaling
client._request("POST", "clusters/edit", json={
    "cluster_id": cluster_id,
    "autoscale": {
        "min_workers": 2,
        "max_workers": 10
    }
})
```

#### Redimensionar Cluster

```python
# Reduzir número de workers
client._request("POST", "clusters/edit", json={
    "cluster_id": cluster_id,
    "num_workers": new_num_workers
})
```

### Storage

#### Executar OPTIMIZE

```sql
-- Otimizar tabela com Z-ORDER
OPTIMIZE catalog.schema.table_name
ZORDER BY (join_column1, join_column2);
```

#### Arquivar Tabelas Abandonadas

```sql
-- 1. Verificar dependências
SHOW TABLES IN catalog.schema LIKE 'table_name';

-- 2. Arquivar (mover para tier frio)
ALTER TABLE catalog.schema.table_name 
SET TBLPROPERTIES ('delta.dataSkippingNumIndexedCols' = '0');

-- 3. Ou excluir (após validação)
DROP TABLE IF EXISTS catalog.schema.table_name;
```

#### Executar VACUUM

```sql
-- Limpar versões antigas
VACUUM catalog.schema.table_name RETAIN 168 HOURS;
```

### Pipelines

#### Corrigir Jobs com Alta Taxa de Falha

1. Investigar logs de falha
2. Identificar causa raiz
3. Corrigir código/configuração
4. Implementar retry inteligente
5. Validar correção

#### Otimizar Jobs Longos

1. Analisar plano de execução
2. Identificar gargalos
3. Otimizar queries
4. Particionar dados
5. Revisar lógica

---

## Medição de Ganhos

### Métricas de Sucesso

1. **Redução de Custos**
   - Custo mensal antes vs depois
   - Percentual de redução
   - Economia anual projetada

2. **Melhoria de Performance**
   - Duração média de jobs
   - Taxa de sucesso
   - Utilização de recursos

3. **Maturity Score**
   - Score antes vs depois
   - Evolução por dimensão
   - Progresso ao longo do tempo

### Consultar ROI

```sql
-- ROI Analysis
SELECT 
    current_monthly_cost,
    estimated_monthly_cost,
    estimated_monthly_savings,
    estimated_annual_savings,
    reduction_percentage,
    confidence,
    margin_of_error
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(ARRAY(roi_analysis)) AS roi
WHERE workspace_name = 'workspace_prod'
ORDER BY report_date DESC
LIMIT 1;
```

### Comparar Estados

```sql
-- Maturity Score ao longo do tempo
SELECT 
    process_timestamp,
    maturity_score,
    maturity_level,
    compute_score,
    storage_score
FROM finops_gold.maturity_scores
WHERE workspace_name = 'workspace_prod'
ORDER BY process_timestamp DESC;
```

### Validar Implementações

```sql
-- Status de recomendações
SELECT 
    recommendation_title,
    status,
    validation_timestamp
FROM finops_gold.revalidation_executive_reports
LATERAL VIEW EXPLODE(recommendations_status) AS rec
WHERE workspace_name = 'workspace_prod'
    AND rec.status IN ('implementada', 'regressão');
```

---

## Automação do Ciclo Contínuo

### Jobs Agendados

#### Coleta Diária (00:00 UTC)

```json
{
  "name": "FinOps - Coleta Diária",
  "schedule": {
    "quartz_cron_expression": "0 0 0 * * ?",
    "timezone_id": "UTC"
  },
  "tasks": [
    {
      "task_key": "collect_compute",
      "notebook_task": {
        "notebook_path": "/notebooks/01_collect/01_collect_compute"
      }
    },
    {
      "task_key": "collect_storage",
      "notebook_task": {
        "notebook_path": "/notebooks/01_collect/02_collect_storage"
      },
      "depends_on": [{"task_key": "collect_compute"}]
    },
    {
      "task_key": "collect_billing",
      "notebook_task": {
        "notebook_path": "/notebooks/01_collect/03_collect_billing"
      },
      "depends_on": [{"task_key": "collect_storage"}]
    }
  ]
}
```

#### Processamento Diário (01:00 UTC)

```json
{
  "name": "FinOps - Processamento",
  "schedule": {
    "quartz_cron_expression": "0 0 1 * * ?",
    "timezone_id": "UTC"
  },
  "tasks": [
    {
      "task_key": "process_bronze_silver",
      "notebook_task": {
        "notebook_path": "/notebooks/02_process/01_process_bronze_to_silver"
      }
    },
    {
      "task_key": "process_silver_gold",
      "notebook_task": {
        "notebook_path": "/notebooks/02_process/02_process_silver_to_gold"
      },
      "depends_on": [{"task_key": "process_bronze_silver"}]
    }
  ]
}
```

#### Análise Diária (02:00 UTC)

```json
{
  "name": "FinOps - Análise",
  "schedule": {
    "quartz_cron_expression": "0 0 2 * * ?",
    "timezone_id": "UTC"
  },
  "tasks": [
    {
      "task_key": "calculate_maturity",
      "notebook_task": {
        "notebook_path": "/notebooks/03_analyze/01_calculate_maturity_score"
      }
    },
    {
      "task_key": "generate_recommendations",
      "notebook_task": {
        "notebook_path": "/notebooks/03_analyze/02_generate_recommendations"
      },
      "depends_on": [{"task_key": "calculate_maturity"}]
    }
  ]
}
```

#### Revalidação Semanal (Domingo 03:00 UTC)

```json
{
  "name": "FinOps - Revalidação Semanal",
  "schedule": {
    "quartz_cron_expression": "0 0 3 ? * SUN",
    "timezone_id": "UTC"
  },
  "tasks": [
    {
      "task_key": "run_revalidation",
      "notebook_task": {
        "notebook_path": "/notebooks/04_revalidate/01_run_revalidation",
        "base_parameters": {
          "BASELINE_DAYS": "30"
        }
      }
    }
  ]
}
```

### Alertas e Notificações

#### Configurar Email Notifications

```python
# Adicionar ao job
"email_notifications": {
    "on_success": ["finops-team@company.com"],
    "on_failure": ["finops-team@company.com", "admin@company.com"],
    "on_start": ["finops-team@company.com"]
}
```

#### Alertas de Quick Wins

```python
# Criar job que verifica quick wins e envia alerta
# Executar após revalidação
quick_wins = generate_quick_wins_alerts(spark, workspace_name)
if quick_wins:
    # Enviar email/Slack com quick wins
    send_alert(quick_wins)
```

### Dashboards

#### Power BI / Tableau

Conectar às tabelas Gold:
- `finops_gold.maturity_scores`
- `finops_gold.recommendations`
- `finops_gold.revalidation_executive_reports`
- `finops_gold.revalidation_quick_wins`

#### Databricks SQL Dashboard

Criar dashboard com queries de `sql/queries/kpi_queries.sql` e `sql/queries/revalidation_queries.sql`

---

## Troubleshooting

### Erro: Tabela não encontrada

```sql
-- Verificar se tabelas foram criadas
SHOW TABLES IN finops_bronze;
SHOW TABLES IN finops_silver;
SHOW TABLES IN finops_gold;
```

### Erro: Permissões insuficientes

Verificar:
- Token do Databricks válido
- Permissões de leitura nas APIs
- Permissões de escrita no DBFS

### Erro: Dados não coletados

Verificar:
- Workspace URL correto
- Token válido
- APIs acessíveis
- Logs dos notebooks

### Performance lenta

Otimizar:
- Particionamento adequado
- Executar OPTIMIZE nas tabelas
- Ajustar configurações de cluster

---

## Próximos Passos

1. Executar assessment inicial
2. Criar baseline (v2.0)
3. Revisar recomendações
4. Priorizar quick wins
5. Implementar correções
6. Medir ganhos
7. Comparar com baseline (v2.0)
8. Automatizar ciclo contínuo
9. Revalidar periodicamente

## Checklist de Validação

Após implementação completa, validar:

- [ ] Dados coletados nas camadas Bronze
- [ ] Processamento Bronze → Silver concluído
- [ ] Processamento Silver → Gold concluído
- [ ] Custos DBU calculados (v2.0)
- [ ] Maturity score calculado
- [ ] Recomendações geradas
- [ ] Baseline criado (v2.0)
- [ ] Cost allocation extraído (v2.0)
- [ ] Queries de exemplo funcionando
- [ ] Documentação consultada
