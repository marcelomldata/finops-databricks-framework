# Guia de Implementação

## Pré-requisitos

- Databricks Workspace (Azure, AWS ou GCP)
- Permissões de leitura nas APIs do Databricks
- Permissões de leitura nas APIs de billing da cloud
- Python 3.8+
- PySpark 3.5+

## Instalação

### 1. Configuração do Ambiente

```bash
pip install -r requirements.txt
```

### 2. Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto baseado em `env.example` ou `config/example.env`:

```bash
# Copiar template (versão simples)
cp env.example .env

# OU copiar template detalhado
cp config/example.env .env

# Editar .env com suas credenciais reais
# ⚠️ IMPORTANTE: NUNCA commite o arquivo .env com credenciais!
```

**Arquivos de exemplo disponíveis:**
- `env.example` - Versão simplificada
- `config/example.env` - Versão detalhada com instruções

**Segurança:**
- O arquivo `.env` está no `.gitignore` e não será versionado
- Padrões de segurança bloqueiam automaticamente:
  - `**/tokens/`, `**/secrets/`
  - `*.pem`, `*.pfx`, `*.key`
  - `*databricks*.cfg`, `*profile*`
  - `terraform.tfstate*`
  - Credenciais de cloud providers

**Para produção:** Use Azure Key Vault, AWS Secrets Manager ou GCP Secret Manager.

### 3. Configuração YAML

Editar `config/config.yaml` com workspaces e parâmetros de análise.

### 4. Criação das Tabelas

Executar DDLs em ordem:
1. `sql/ddl/bronze_ddl.sql`
2. `sql/ddl/silver_ddl.sql`
3. `sql/ddl/gold_ddl.sql`
4. `sql/ddl/gold_baselines_ddl.sql` (v2.0 - baselines e cost allocation)
5. `sql/ddl/gold_enhanced_ddl.sql` (v2.1 - billing, automação, benchmarks, observabilidade)

## Execução

### Coleta de Dados

#### Compute
```python
# notebooks/01_collect/01_collect_compute.py
```

#### Storage
```python
# notebooks/01_collect/02_collect_storage.py
```

#### Billing
```python
# notebooks/01_collect/03_collect_billing.py
```

### Processamento

#### Bronze → Silver
```python
# notebooks/02_process/01_process_bronze_to_silver.py
```

#### Silver → Gold
```python
# notebooks/02_process/02_process_silver_to_gold.py
```

#### Calcular Custos DBU (v2.0)
```python
# notebooks/02_process/03_calculate_dbu_costs.py
```

### Análise

#### Maturity Score
```python
# notebooks/03_analyze/01_calculate_maturity_score.py
```

#### Recomendações
```python
# notebooks/03_analyze/02_generate_recommendations.py
```

#### Criar Baseline (v2.0)
```python
# notebooks/03_analyze/03_create_baseline.py
```

#### Calcular Benchmarks (v2.1)
```python
# notebooks/03_analyze/04_calculate_benchmarks.py
```

#### Reconciliar Billing (v2.1)
```python
# notebooks/03_analyze/05_reconcile_billing.py
```

#### Alocar Custos por Pipeline (v2.1)
```python
# notebooks/03_analyze/06_allocate_pipeline_costs.py
```

#### Gerar Alertas de Automação (v2.1)
```python
# notebooks/03_analyze/07_generate_automation_alerts.py
```

## Agendamento

### Jobs Databricks

Criar jobs no Databricks Workflows:

1. **Coleta Diária** (00:00 UTC)
   - `01_collect_compute`
   - `02_collect_storage`
   - `03_collect_billing`

2. **Processamento** (01:00 UTC)
   - `01_process_bronze_to_silver`
   - `02_process_silver_to_gold`

3. **Análise** (02:00 UTC)
   - `01_calculate_maturity_score`
   - `02_generate_recommendations`

### Dependências

```
Coleta → Processamento → Análise
```

## Múltiplos Workspaces

Para múltiplos workspaces, executar coletas em paralelo ou sequencialmente, garantindo que cada workspace tenha seu próprio conjunto de dados particionado.

## Monitoramento

- Verificar logs dos jobs
- Validar contagem de registros nas tabelas Gold
- Acompanhar maturity scores ao longo do tempo
- Revisar recomendações geradas
- Comparar baselines (v2.0)
- Monitorar custos DBU estimados (v2.0)
- Verificar cost allocation por domínio (v2.0)

## Verificações Pós-Implementação

### Validar Coleta

```sql
-- Verificar se dados foram coletados
SELECT COUNT(*) FROM finops_bronze.compute_clusters;
SELECT COUNT(*) FROM finops_bronze.storage_tables;
```

### Validar Processamento

```sql
-- Verificar camada Silver
SELECT COUNT(*) FROM finops_silver.compute_clusters;

-- Verificar camada Gold
SELECT COUNT(*) FROM finops_gold.compute_clusters_summary;
```

### Validar Custos DBU (v2.0)

```sql
-- Verificar estimativas de custo
SELECT 
    COUNT(*) AS total_clusters,
    SUM(estimated_monthly_cost) AS total_monthly_cost
FROM finops_gold.costs_dbu_estimates;
```

### Validar Baseline (v2.0)

```sql
-- Verificar baseline criado
SELECT * FROM finops_gold.assessment_baselines
ORDER BY baseline_date DESC
LIMIT 1;
```
