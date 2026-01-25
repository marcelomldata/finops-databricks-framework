# FinOps Maturity Score

## Visão Geral

O FinOps Maturity Score é um indicador composto que avalia a maturidade de um workspace Databricks em relação às melhores práticas de FinOps.

## Cálculo

### Fórmula

```
Maturity Score = 
    (Compute Score × 0.25) +
    (Storage Score × 0.25) +
    (Governance Score × 0.20) +
    (Pipelines Score × 0.15) +
    (Observability Score × 0.10) +
    (Costs Score × 0.05)
```

### Pesos Configuráveis

Os pesos podem ser ajustados em `config/config.yaml`:

```yaml
analysis:
  maturity_score:
    weights:
      compute: 0.25
      storage: 0.25
      governance: 0.20
      pipelines: 0.15
      observability: 0.10
      costs: 0.05
```

## Dimensões

### Compute Score (0.0 - 1.0)

Fatores:
- Utilização média de clusters (50%)
- Taxa de clusters ociosos (25%)
- Configuração de autoscaling (20%)
- Eficiência de jobs (30%)

Cálculo:
```
Utilization Score = avg_utilization × (1 - idle_ratio × 0.5)
Autoscaling Score = autoscaling_ratio × 0.3
Job Score = (success_rate × 0.4) + (efficiency_score × 0.3)

Compute Score = (Utilization Score × 0.5) + (Autoscaling Score × 0.2) + (Job Score × 0.3)
```

### Storage Score (0.0 - 1.0)

Fatores:
- Taxa de particionamento (40%)
- Otimização (ausência de small files) (30%)
- Limpeza (ausência de dados abandonados) (30%)

Cálculo:
```
Partitioning Score = partitioned_ratio × 0.4
Optimization Score = (1 - small_files_ratio) × 0.3
Cleanup Score = (1 - abandoned_ratio) × 0.3

Storage Score = Partitioning Score + Optimization Score + Cleanup Score
```

### Governance Score (0.0 - 1.0)

Fatores:
- Uso de Unity Catalog (50%)
- Ownership de tabelas
- Tags e metadados

Cálculo:
```
Unity Score = 0.5 se Unity Catalog, 0.0 caso contrário
Governance Score = Unity Score + (outros fatores)
```

### Pipelines Score (0.0 - 1.0)

Fatores:
- Taxa de jobs agendados (30%)
- Taxa de sucesso (40%)
- Eficiência (30%)

Cálculo:
```
Scheduled Ratio = scheduled_jobs / total_jobs
Success Score = avg_success_rate
Efficiency Score = avg_efficiency_score

Pipelines Score = (Scheduled Ratio × 0.3) + (Success Score × 0.4) + (Efficiency Score × 0.3)
```

### Observability Score (0.0 - 1.0)

Fatores:
- Cobertura de tags em clusters e jobs

Cálculo:
```
Tagging Score = (clusters_with_tags / total_clusters × 0.5) + (jobs_with_tags / total_jobs × 0.5)
Observability Score = Tagging Score
```

### Costs Score (0.0 - 1.0)

Fatores:
- Tendência de custos (redução = melhor)

Cálculo:
```
Cost Change Ratio = (recent_avg - older_avg) / older_avg

Se cost_change_ratio < -0.1: 1.0
Se cost_change_ratio < 0: 0.7
Se cost_change_ratio < 0.1: 0.5
Caso contrário: 0.3
```

## Níveis de Maturidade

### Otimizado (≥ 0.8)
- Todas as dimensões bem otimizadas
- Processos maduros
- Monitoramento contínuo

### Avançado (0.6 - 0.8)
- Maioria das dimensões otimizadas
- Algumas melhorias necessárias
- Processos estabelecidos

### Intermediário (0.4 - 0.6)
- Algumas dimensões otimizadas
- Oportunidades claras de melhoria
- Processos em evolução

### Básico (< 0.4)
- Poucas dimensões otimizadas
- Muitas oportunidades de melhoria
- Processos iniciais

## Interpretação

### Score Alto (≥ 0.8)
- Workspace bem gerenciado
- Custos otimizados
- Boas práticas implementadas
- Foco em refinamento contínuo

### Score Médio (0.4 - 0.8)
- Oportunidades de otimização identificadas
- Implementação de recomendações priorizadas
- Evolução gradual

### Score Baixo (< 0.4)
- Necessidade de ações imediatas
- Implementação de quick wins
- Estabelecimento de processos básicos

## Uso

O maturity score é calculado automaticamente após o processamento das camadas Gold e armazenado em `finops_gold.maturity_scores`.

Pode ser consultado via:
- SQL queries
- Dashboards
- APIs

## Evolução

O score deve ser monitorado ao longo do tempo para:
- Acompanhar progresso
- Validar eficácia de melhorias
- Identificar regressões
- Estabelecer metas
