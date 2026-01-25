# Documentação FinOps Databricks

## Índice

### Visão Geral
- [Visão Executiva](visao_executiva.md) - Resumo executivo do projeto
- [Branding](BRANDING.md) - Nome, visão, missão e escopo
- [Open vs Premium](OPEN_VS_PREMIUM.md) - O que está aberto e fechado

### Arquitetura e Dados
- [Arquitetura](arquitetura.md) - Arquitetura técnica e componentes
- [Modelo de Dados](MODELO_DADOS.md) - Documentação completa do modelo de dados
- [Implementação](implementacao.md) - Guia de implementação passo a passo

### Análise
- [Dimensões de Análise](dimensoes_analise.md) - Detalhamento das dimensões analisadas
- [Maturity Score](maturity_score.md) - Cálculo e interpretação do score
- [Recomendações](recomendacoes.md) - Sistema de recomendações

### Operação
- [Quick Start](QUICK_START.md) - Comece em 15 minutos ⚡
- [HOW TO Completo](HOW_TO.md) - Guia completo de uso
- [Revalidação Contínua](revalidacao.md) - Processo de auditoria contínua
- [Modelo Operacional](MODELO_OPERACIONAL.md) - RACI, rituais e KPIs
- [Checklist de Assessment](checklist_assessment.md) - Checklist para diagnóstico
- [Segurança](SEGURANCA.md) - Proteção de credenciais e boas práticas
- [Melhorias V2](MELHORIAS_V2.md) - Melhorias críticas v2.0.0
- [Lacunas e Evolução](LACUNAS_EVOLUCAO.md) - Lacunas identificadas e melhorias v2.1.0
- [Roadmap](roadmap.md) - Roadmap de evolução
- [Jobs Exemplo](jobs_exemplo.json) - Exemplo de configuração de jobs

### Exemplos e Casos
- [Exemplos Concretos](EXEMPLOS_CONCRETOS.md) - Casos de uso reais com dados
- [Embalagem Comercial](EMBALAGEM_COMERCIAL.md) - Pacotes de serviços e vendas

### Serviços
- [Professional Services](PROFESSIONAL_SERVICES.md) - Serviços premium disponíveis

## Estrutura do Projeto

```
finops-databricks/
├── notebooks/          # Notebooks de coleta, processamento e análise
├── src/                # Código fonte Python
│   ├── collectors/     # Coletores de métricas
│   ├── processors/    # Processadores Bronze/Silver/Gold
│   ├── analyzers/      # Analisadores FinOps
│   └── utils/          # Utilitários
├── sql/                # DDLs e queries SQL
│   ├── ddl/           # Definições de tabelas
│   └── queries/        # Queries de KPIs
├── config/             # Configurações
└── docs/               # Documentação
```

## Fluxo de Trabalho

1. **Coleta** → Notebooks coletam métricas via APIs
2. **Bronze** → Dados brutos armazenados
3. **Silver** → Normalização e enriquecimento
4. **Gold** → Agregações e KPIs
5. **Análise** → Cálculo de scores e recomendações

## Início Rápido

### Para Começar Agora (15 minutos)
1. [Quick Start](QUICK_START.md) - Guia rápido de 15 minutos

### Para Entender o Framework
1. Ler [Visão Executiva](visao_executiva.md)
2. Revisar [Arquitetura](arquitetura.md)
3. Entender [Modelo de Dados](MODELO_DADOS.md)

### Para Implementar
1. Seguir [Guia de Implementação](implementacao.md)
2. Usar [HOW TO Completo](HOW_TO.md)
3. Consultar [Checklist](checklist_assessment.md) para diagnóstico

## Suporte

Para dúvidas ou problemas, consultar a documentação específica de cada componente.
