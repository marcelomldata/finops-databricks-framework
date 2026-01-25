# FinOps Databricks Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5%2B-orange.svg)](https://spark.apache.org/)

Framework open source completo de FinOps para assessment contínuo de workspaces Databricks multi-cloud.

## 🎯 Visão

Ser o framework open source de referência para assessment contínuo e otimização de custos em ambientes Databricks multi-cloud, capacitando organizações a alcançarem maturidade FinOps através de práticas comprovadas e automação inteligente.

## ✨ Características

- ✅ **100% Open Source** - Arquitetura, modelo de dados e scripts completamente abertos
- ✅ **Multi-Cloud** - Azure, AWS e GCP Databricks
- ✅ **Multi-Metastore** - Unity Catalog e Hive Metastore
- ✅ **Arquitetura Medalhão** - Bronze/Silver/Gold bem definido
- ✅ **Revalidação Contínua** - Auditoria periódica automática
- ✅ **Maturity Scoring** - 6 dimensões de análise
- ✅ **Recomendações Priorizadas** - Ações acionáveis com ROI estimado
- ✅ **Custos DBU Reais** - Estimativa baseada em uptime e taxas DBU (v2.0)
- ✅ **Baseline Versionado** - Comparação entre múltiplos períodos (v2.0)
- ✅ **Cost Allocation** - Alocação por domínio e tags (v2.0)

## Arquitetura

### Camadas de Dados
- **Bronze**: Métricas brutas coletadas via APIs
- **Silver**: Métricas normalizadas e enriquecidas
- **Gold**: KPIs, scores e rankings FinOps

### Dimensões de Análise
- Compute (Clusters & Jobs)
- Storage (Delta Lake)
- Data Governance & Qualidade
- Pipelines & Orquestração
- Custos & Billing

### Suporte Multi-Cloud
- Azure Databricks
- AWS Databricks
- GCP Databricks

### Suporte Multi-Metastore
- Unity Catalog
- Hive Metastore (legado)

## Estrutura do Projeto

```
finops-databricks/
├── notebooks/
│   ├── 01_collect/
│   ├── 02_process/
│   ├── 03_analyze/
│   └── 04_revalidate/
├── src/
│   ├── collectors/
│   ├── processors/
│   ├── analyzers/
│   ├── auditors/
│   └── utils/
├── sql/
│   ├── ddl/
│   └── queries/
├── config/
└── docs/
```

## Instalação

1. Instalar dependências: `pip install -r requirements.txt`
2. Copiar `env.example` para `.env` e configurar credenciais
3. Executar DDLs em `sql/ddl/` para criar tabelas
4. Configurar `config/config.yaml` com workspaces
5. Executar notebooks de coleta
6. Processar camadas Bronze/Silver/Gold
7. Executar análise FinOps

## 🚀 Quick Start

```bash
# 1. Clone o repositório
git clone https://github.com/[seu-repo]/finops-databricks-framework.git
cd finops-databricks-framework

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure variáveis de ambiente
cp env.example .env
# Edite .env com suas credenciais

# 4. Execute DDLs no Databricks (em ordem)
# - sql/ddl/bronze_ddl.sql
# - sql/ddl/silver_ddl.sql
# - sql/ddl/gold_ddl.sql
# - sql/ddl/gold_baselines_ddl.sql (v2.0)

# 5. Execute coleta
# Execute notebooks em notebooks/01_collect/

# 6. Processe dados
# Execute notebooks em notebooks/02_process/

# 7. Analise e crie baseline
# Execute notebooks em notebooks/03_analyze/
```

**📖 Para instruções detalhadas:**
- [Quick Start](docs/QUICK_START.md) - Comece em 15 minutos
- [HOW TO Completo](docs/HOW_TO.md) - Guia detalhado passo a passo

## 📚 Documentação

### Guias Técnicos
- [HOW TO Completo](docs/HOW_TO.md) - Guia passo a passo
- [Arquitetura](docs/arquitetura.md) - Visão técnica detalhada
- [Implementação](docs/implementacao.md) - Guia de implementação
- [Revalidação](docs/revalidacao.md) - Processo de auditoria contínua
- [Modelo de Dados](docs/MODELO_DADOS.md) - Documentação completa do modelo
- [Segurança](docs/SEGURANCA.md) - Proteção de credenciais e boas práticas

### Comercial
- [Exemplos Concretos](docs/EXEMPLOS_CONCRETOS.md) - Casos de uso reais
- [Embalagem Comercial](docs/EMBALAGEM_COMERCIAL.md) - Pacotes de serviços
- [Open vs Premium](docs/OPEN_VS_PREMIUM.md) - O que está aberto e fechado
- [Professional Services](docs/PROFESSIONAL_SERVICES.md) - Serviços premium

### Estratégico
- [Branding](docs/BRANDING.md) - Visão, missão e escopo
- [Roadmap](ROADMAP.md) - Roadmap público

## 🎯 O que está Aberto (100% Open Source)

✅ **Arquitetura Completa**
- Visão Bronze/Silver/Gold
- Fluxo de assessment → revalidação
- Diagramas e padrões

✅ **Modelo de Dados FinOps**
- Tabelas de métricas
- Campos e KPIs
- Scores e dicionário de dados

✅ **Scripts de Coleta**
- Listar clusters, jobs, tabelas
- Coletar métricas básicas
- Ler system tables

✅ **Regras de Diagnóstico**
- "Cluster ligado > X horas sem job"
- "Tabela sem leitura há X dias"
- "Join sem broadcast potencial"

✅ **Checklist FinOps**
- Health check completo
- Material de referência

✅ **Documentação Completa**
- HOW TO básico
- Como rodar assessment
- Como interpretar scores

## 🔒 O que está Fechado (Premium/Consultoria)

❌ **Automação Completa End-to-End**
- Orquestração multi-workspace
- Jobs recorrentes automatizados
- Alertas contínuos integrados

❌ **Integração Real com Billing Cloud**
- Azure Cost Management API
- AWS Cost Explorer API
- GCP Billing Export

❌ **Cálculo Avançado de ROI**
- Modelos calibrados por workload
- Cenários conservador vs agressivo
- Margem de erro precisa

❌ **Playbooks de Correção Profunda**
- Reescrita de pipelines
- Refatoração de joins
- Estratégia de particionamento

❌ **Dashboards Executivos Prontos**
- Dashboard final implementado
- Storytelling executivo
- Métricas comparativas

❌ **Templates Corporativos**
- Naming corporativo
- Ownership obrigatório
- Retenção por domínio
- SLA técnico

## 💼 Professional Services

**Precisa de ajuda para implementar? Fale com a ML Data e IA.**

Oferecemos serviços profissionais para acelerar sua jornada FinOps:
- Implementação completa
- Automação end-to-end
- Integração com billing cloud
- Cálculo avançado de ROI
- Playbooks de correção
- Dashboards executivos
- Templates corporativos

[Saiba mais](docs/PROFESSIONAL_SERVICES.md)

## 🤝 Contribuindo

Contribuições são bem-vindas! Veja [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes.

## 📄 Licença

Este projeto está licenciado sob a [Apache License 2.0](LICENSE).

## 🗺️ Roadmap

Veja nosso [Roadmap Público](ROADMAP.md) para conhecer as próximas funcionalidades.

## 📋 Estrutura do Projeto

```
finops-databricks-framework/
├── src/                    # Código fonte (100% open source)
│   ├── collectors/         # Coletores de métricas
│   ├── processors/         # Processadores Bronze/Silver/Gold
│   ├── analyzers/          # Analisadores FinOps
│   ├── auditors/           # Auditores de revalidação
│   └── utils/              # Utilitários
├── notebooks/               # Notebooks de execução (100% open source)
│   ├── 01_collect/         # Coleta de métricas
│   ├── 02_process/         # Processamento
│   ├── 03_analyze/         # Análise
│   └── 04_revalidate/     # Revalidação
├── sql/                     # DDLs e queries (100% open source)
│   ├── ddl/                # Definições de tabelas
│   └── queries/            # Queries de análise
├── config/                  # Configurações (100% open source)
├── docs/                    # Documentação completa
├── LICENSE                  # Apache 2.0
├── CONTRIBUTING.md          # Guia de contribuição
└── ROADMAP.md              # Roadmap público
```

## 🎯 Status do Projeto

- ✅ **v1.0.0** - Release inicial completa
- ✅ **v2.0.0** - Melhorias críticas implementadas
  - Integração real com custos DBU (open source)
  - Baseline técnico versionado
  - Cost allocation por domínio
- 🚀 **Em desenvolvimento** - Veja [ROADMAP.md](ROADMAP.md) e [Melhorias V2](docs/MELHORIAS_V2.md)

## ⚠️ Nota Importante

Este framework é **100% open source** para assessment básico. Funcionalidades avançadas (automação completa, integração billing, dashboards executivos) estão disponíveis através de [Professional Services](docs/PROFESSIONAL_SERVICES.md).

Veja [Open vs Premium](docs/OPEN_VS_PREMIUM.md) para detalhes completos.

## 📦 Versão Atual

**v2.0.0** - Melhorias críticas implementadas:
- ✅ Integração real com custos DBU (open source)
- ✅ Baseline técnico versionado
- ✅ Cost allocation por domínio
- ✅ Modelo operacional FinOps

Veja [CHANGELOG.md](CHANGELOG.md) para histórico completo.

## 📞 Contato

- Issues: [GitHub Issues](https://github.com/[seu-repo]/issues)
- Professional Services: [ML Data e IA](docs/PROFESSIONAL_SERVICES.md)
