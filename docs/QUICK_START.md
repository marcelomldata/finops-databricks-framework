# Quick Start - FinOps Databricks Framework

Guia rápido para começar a usar o framework em 15 minutos.

## Pré-requisitos

- Databricks Workspace (Azure, AWS ou GCP)
- Token de acesso ao Databricks
- Permissões de leitura nas APIs

## Passo 1: Clone e Setup (2 min)

```bash
# Clone o repositório
git clone https://github.com/[seu-repo]/finops-databricks-framework.git
cd finops-databricks-framework

# Instale dependências
pip install -r requirements.txt
```

## Passo 2: Configuração (3 min)

```bash
# Copie o template de ambiente
cp env.example .env

# Edite .env com suas credenciais
# WORKSPACE_NAME=meu_workspace
# WORKSPACE_URL=https://adb-xxxxx.azuredatabricks.net
# DATABRICKS_TOKEN=dapi_seu_token_aqui
```

## Passo 3: Criar Tabelas (5 min)

No Databricks SQL, execute em ordem:

1. `sql/ddl/bronze_ddl.sql`
2. `sql/ddl/silver_ddl.sql`
3. `sql/ddl/gold_ddl.sql`
4. `sql/ddl/gold_baselines_ddl.sql` (v2.0)

## Passo 4: Primeira Coleta (5 min)

Execute no Databricks (notebooks ou jobs):

```python
# 1. Coletar compute
notebooks/01_collect/01_collect_compute.py

# 2. Coletar storage
notebooks/01_collect/02_collect_storage.py

# 3. Processar dados
notebooks/02_process/01_process_bronze_to_silver.py
notebooks/02_process/02_process_silver_to_gold.py

# 4. Calcular custos DBU (v2.0)
notebooks/02_process/03_calculate_dbu_costs.py

# 5. Analisar
notebooks/03_analyze/01_calculate_maturity_score.py
notebooks/03_analyze/02_generate_recommendations.py

# 6. Criar baseline (v2.0)
notebooks/03_analyze/03_create_baseline.py
```

## Passo 5: Ver Resultados (2 min)

```sql
-- Maturity Score
SELECT * FROM finops_gold.maturity_scores
ORDER BY process_timestamp DESC
LIMIT 1;

-- Top 10 Recomendações
SELECT * FROM finops_gold.recommendations
ORDER BY 
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END
LIMIT 10;

-- Custos DBU (v2.0)
SELECT 
    cluster_name,
    estimated_monthly_cost
FROM finops_gold.costs_dbu_estimates
ORDER BY estimated_monthly_cost DESC
LIMIT 10;
```

## Próximos Passos

1. Revisar recomendações
2. Implementar quick wins
3. Configurar agendamento diário
4. Ler [HOW TO Completo](HOW_TO.md) para detalhes

## Troubleshooting

**Erro: Tabela não encontrada**
- Verifique se DDLs foram executados
- Confirme nomes das tabelas

**Erro: Permissões insuficientes**
- Verifique token do Databricks
- Confirme permissões de leitura

**Erro: Dados não coletados**
- Verifique workspace URL
- Confirme token válido
- Revise logs dos notebooks

## Suporte

- [Documentação Completa](README.md)
- [HOW TO Detalhado](HOW_TO.md)
- [Issues no GitHub](https://github.com/[seu-repo]/issues)
