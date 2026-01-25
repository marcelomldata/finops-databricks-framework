# Roadmap Público - FinOps Databricks Framework

## Visão Geral

Este roadmap reflete nossa visão de evolução do framework, priorizando funcionalidades que agregam valor à comunidade open source e mantendo transparência sobre o desenvolvimento futuro.

## Versão Atual: v2.0.0

### ✅ Funcionalidades Implementadas (v1.0.0)

- [x] Coleta de métricas (Compute, Storage, Billing)
- [x] Processamento Bronze/Silver/Gold
- [x] Cálculo de maturity scores
- [x] Geração de recomendações
- [x] Revalidação contínua
- [x] Suporte multi-cloud (Azure, AWS, GCP)
- [x] Suporte multi-metastore (Unity Catalog, Hive)
- [x] Documentação completa
- [x] HOW TO detalhado

### ✅ Melhorias Críticas (v2.0.0)

- [x] Integração real com custos DBU (open source)
- [x] Baseline técnico versionado
- [x] Cost allocation por domínio
- [x] Tabela de estimativas DBU
- [x] Comparação entre baselines
- [x] Alocação por cost_center/business_unit/data_domain

Veja [Melhorias V2](docs/MELHORIAS_V2.md) para detalhes completos.

## Q1 2025

### v2.1.0 - CLI e Testes

**Objetivo**: CLI standalone e testes automatizados

- [ ] CLI Python standalone (fora do Databricks)
- [ ] Testes unitários de regras de score
- [ ] Testes de regressão de maturity score
- [ ] Testes de recomendações
- [ ] Modelo operacional FinOps documentado

**Prazo**: Março 2025

### v2.2.0 - Integração System Tables

**Objetivo**: Integração com system tables e melhorias de precisão

- [ ] Integração com system.billing.usage (quando disponível)
- [ ] Ajuste automático de taxas DBU baseado em histórico
- [ ] Validação de hierarquia de tags
- [ ] Templates de tagging corporativo
- [ ] Storytelling executivo

**Prazo**: Junho 2025

## Q2 2025

### v2.0.0 - API e Integrações

**Objetivo**: Facilitar integração com outras ferramentas

- [ ] REST API para consulta de métricas
- [ ] Webhooks para alertas
- [ ] Integração com Slack (open source básico)
- [ ] Integração com Teams (open source básico)
- [ ] Export de dados (CSV, JSON, Parquet)

**Prazo**: Setembro 2025

### v2.1.0 - Visualizações Básicas

**Objetivo**: Fornecer visualizações simples para análise

- [ ] Dashboard básico (HTML estático)
- [ ] Gráficos de evolução de scores
- [ ] Visualização de recomendações
- [ ] Export de relatórios (PDF básico)

**Prazo**: Dezembro 2025

## Q3 2025

### v3.0.0 - Machine Learning para Otimização

**Objetivo**: Usar ML para prever e otimizar custos

- [ ] Modelo de predição de custos
- [ ] Recomendações baseadas em ML
- [ ] Detecção de anomalias
- [ ] Otimização automática de clusters (sugestões)

**Prazo**: Março 2026

## Funcionalidades Premium (Não no Roadmap Open Source)

As seguintes funcionalidades estão disponíveis apenas através de Professional Services:

### Automação Completa
- Orquestração multi-workspace
- Jobs recorrentes automatizados
- Alertas contínuos integrados
- Integração completa com Slack/Teams

### Integração com Billing Cloud
- Azure Cost Management API
- AWS Cost Explorer API
- GCP Billing Export
- Alocação precisa de custos

### Cálculo Avançado de ROI
- Modelos calibrados por workload
- Cenários conservador vs agressivo
- Margem de erro precisa
- Projeções de longo prazo

### Playbooks de Correção
- Reescrita de pipelines
- Refatoração de joins
- Estratégia de particionamento
- Desenho de clusters ideais

### Dashboards Executivos
- Dashboard final implementado
- Storytelling executivo
- Métricas comparativas
- Integração com Power BI/Tableau

### Templates Corporativos
- Naming corporativo
- Ownership obrigatório
- Retenção por domínio
- SLA técnico

## Como Contribuir

Quer ajudar a acelerar o roadmap? Veja [CONTRIBUTING.md](CONTRIBUTING.md).

## Solicitar Funcionalidades

Tem uma ideia? Abra uma issue no GitHub com a tag `enhancement`.

## Política de Versões

- **Major (X.0.0)**: Mudanças incompatíveis com versões anteriores
- **Minor (0.X.0)**: Novas funcionalidades compatíveis
- **Patch (0.0.X)**: Correções de bugs compatíveis

## Atualizações

Este roadmap é atualizado trimestralmente. Última atualização: Janeiro 2025.
