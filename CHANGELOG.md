# Changelog - FinOps Databricks Framework

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [2.1.0] - 2025-01-25

### Adicionado

#### Reconciliador de Billing (Open Source)
- Módulo `src/utils/billing_reconciler.py` para reconciliação de custos
- Tabela `finops_gold.billing_reconciliation` com reconciliações
- Função `reconcile_dbu_vs_actual()` para comparar estimado vs real
- Função `calculate_roi_confidence()` para score de confiabilidade do ROI
- Notebook `notebooks/03_analyze/05_reconcile_billing.py`

#### Cost Allocation por Pipeline/Produto/SLA
- Módulo `src/utils/pipeline_cost_allocation.py` para alocação granular
- Tabela `finops_gold.cost_allocation_pipelines` com alocação por pipeline
- Alocação por produto de dados
- Alocação por SLA tier (fast/standard/slow)
- Notebook `notebooks/03_analyze/06_allocate_pipeline_costs.py`

#### Safe Automation
- Módulo `src/utils/safe_automation.py` para automação segura
- Tabela `finops_gold.automation_actions` com ações de automação
- Geração de alertas com comandos de ação sugeridos
- Níveis de automação (alert/semi-auto/auto)
- Comandos de rollback incluídos
- Notebook `notebooks/03_analyze/07_generate_automation_alerts.py`

#### Observabilidade Avançada
- Módulo `src/utils/observability_enhanced.py` para análise avançada
- Análise de padrões de falha recorrentes
- Análise de performance por etapa (setup/execution/cleanup)
- Ligação custo ↔ performance ↔ falha
- Tabela `finops_gold.observability_enhanced`

#### Benchmarks Externos
- Módulo `src/utils/benchmark_calculator.py` para benchmarks
- Tabela `finops_gold.benchmarks` com benchmarks
- Comparação com níveis da indústria (excellent/good/average/poor)
- Métricas: custo por TB, utilização, taxa de sucesso, dados frios
- Notebook `notebooks/03_analyze/04_calculate_benchmarks.py`

#### Documentação de Lacunas
- `docs/LACUNAS_EVOLUCAO.md` - Detalhamento de lacunas e evolução
- Atualização de `ROADMAP.md` com v2.1.0

### Melhorado

- Cost allocation agora inclui pipeline, produto e SLA
- ROI agora tem score de confiabilidade
- Observabilidade liga custo, performance e falhas
- Benchmarks fornecem contexto executivo

### Mudanças Técnicas

- DDL adicional: `sql/ddl/gold_enhanced_ddl.sql`
- Novos notebooks de análise (04-07)
- Módulos utilitários expandidos

---

## [2.0.0] - 2025-01-25

### Adicionado

#### Integração Real com Custos DBU (Open Source)
- Módulo `src/analyzers/cost_estimator.py` para estimativa de custos DBU
- Tabela `finops_gold.costs_dbu_estimates` com estimativas por cluster
- Cálculo baseado em uptime × DBU rate × tipo de cluster
- Tabela estática de preços DBU por cloud
- Notebook `notebooks/02_process/03_calculate_dbu_costs.py`

#### Baseline Técnico Versionado
- Módulo `src/utils/baseline_manager.py` para gerenciamento de baselines
- Tabela `finops_gold.assessment_baselines` com baselines versionados
- Função `create_baseline()` para criar baselines com ID único
- Função `compare_baselines()` para comparar múltiplos períodos
- Notebook `notebooks/03_analyze/03_create_baseline.py`
- Queries SQL em `sql/queries/baseline_queries.sql`

#### Cost Allocation por Domínio
- Módulo `src/utils/cost_allocation.py` para alocação de custos
- Tabela `finops_gold.cost_allocation` com alocação por domínio
- Suporte a cost_center, business_unit, data_domain
- Hierarquia: job > cluster > workspace
- Extração automática de tags

#### Modelo Operacional FinOps
- Documento `docs/MODELO_OPERACIONAL.md` com:
  - RACI (papéis e responsabilidades)
  - Ritmo mensal de FinOps
  - Rituais definidos
  - KPIs de acompanhamento
  - Checklist de adoção

#### Documentação de Melhorias
- `docs/MELHORIAS_V2.md` - Detalhamento completo das melhorias
- Atualização de `ROADMAP.md` com v2.0.0
- Atualização de `HOW_TO.md` com novos passos
- Atualização de `docs/implementacao.md` com novas tabelas

### Melhorado

- `calculate_costs_score()` agora usa estimativas DBU quando disponível
- Costs Score mais preciso (baseado em dados reais vs estimativas)
- Revalidação agora compara com baselines versionados
- Documentação atualizada com todas as melhorias

### Mudanças Técnicas

- DDL adicional: `sql/ddl/gold_baselines_ddl.sql`
- Queries adicionais: `sql/queries/baseline_queries.sql`
- Integração de módulos de custo e baseline

---

## [1.0.0] - 2025-01-24

### Adicionado

- Framework completo de FinOps para Databricks
- Coleta de métricas (Compute, Storage, Billing)
- Processamento Bronze/Silver/Gold
- Cálculo de maturity scores
- Geração de recomendações
- Revalidação contínua
- Suporte multi-cloud (Azure, AWS, GCP)
- Suporte multi-metastore (Unity Catalog, Hive)
- Documentação completa
- HOW TO detalhado
- Licença Apache 2.0
- Roadmap público
- Professional Services
