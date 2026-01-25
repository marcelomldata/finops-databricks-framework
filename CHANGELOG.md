# Changelog - FinOps Databricks Framework

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
