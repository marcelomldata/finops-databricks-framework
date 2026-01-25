# Sistema de Recomendações

## Visão Geral

O sistema de recomendações gera ações acionáveis priorizadas para otimização de custos e performance.

## Categorias

### Compute
- Clusters ociosos
- Overprovisioning
- Falta de autoscaling
- Jobs ineficientes

### Storage
- Tabelas abandonadas
- Dados frios
- Small files
- Falta de particionamento

### Pipelines
- Jobs com alta taxa de falha
- Jobs sem schedule
- Pipelines redundantes

## Estrutura

Cada recomendação contém:

- **workspace_name**: Workspace afetado
- **category**: Categoria (compute, storage, pipelines)
- **priority**: Alta, Média, Baixa
- **title**: Título descritivo
- **description**: Descrição detalhada
- **impact**: Alto, Médio, Baixo
- **complexity**: Alta, Média, Baixa
- **action**: Ação recomendada
- **estimated_savings**: Estimativa de economia

## Priorização

### Alta Prioridade
- Clusters ociosos há > 4 horas
- Tabelas abandonadas > 100 GB
- Jobs com > 20% de falha
- Impacto financeiro alto

### Média Prioridade
- Tabelas com small files > 100 GB
- Clusters sem autoscaling
- Dados frios > 50 GB
- Impacto financeiro médio

### Baixa Prioridade
- Otimizações menores
- Melhorias incrementais
- Impacto financeiro baixo

## Exemplos

### Cluster Ocioso
```
Category: compute
Priority: high
Title: Cluster X está ocioso
Description: Cluster cluster_123 está ocioso há 8.5 horas
Impact: Alto
Complexity: Baixa
Action: Considerar desligar ou reduzir tamanho do cluster
Estimated Savings: Variável
```

### Tabela Abandonada
```
Category: storage
Priority: high
Title: Tabela Y abandonada
Description: Tabela catalog.schema.table não é acessada há 200 dias
Impact: Alto
Complexity: Média
Action: Arquivar ou excluir tabela
Estimated Savings: 500.00 GB
```

### Small Files
```
Category: storage
Priority: medium
Title: Tabela Z com muitos arquivos pequenos
Description: Tabela catalog.schema.table tem 10000 arquivos com média de 50 MB
Impact: Médio
Complexity: Baixa
Action: Executar OPTIMIZE e Z-ORDER
Estimated Savings: Melhoria de performance
```

## Uso

Recomendações são geradas automaticamente e armazenadas em `finops_gold.recommendations`.

Consultas:
- Por prioridade
- Por categoria
- Por workspace
- Por impacto estimado

## Implementação

1. Revisar recomendações de alta prioridade
2. Validar impacto e complexidade
3. Implementar ações
4. Monitorar resultados
5. Atualizar recomendações

## Validação

Após implementação:
- Re-executar coleta
- Verificar métricas atualizadas
- Confirmar melhoria no maturity score
- Documentar resultados
