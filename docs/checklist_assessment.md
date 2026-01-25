# Checklist de Assessment FinOps

## Compute

### Clusters
- [ ] Identificar clusters sempre ligados
- [ ] Verificar clusters ociosos (> 4 horas)
- [ ] Avaliar overprovisioning (CPU, memória, workers)
- [ ] Verificar configuração de autoscaling
- [ ] Analisar uso de all-purpose vs job clusters
- [ ] Verificar uso de instâncias spot/preemptivas
- [ ] Identificar clusters sem tags de custo

### Jobs
- [ ] Identificar jobs com alta taxa de falha (> 20%)
- [ ] Verificar jobs longos ou ineficientes
- [ ] Analisar jobs sem schedule
- [ ] Verificar concentração excessiva em poucos clusters
- [ ] Identificar jobs reexecutados em loop
- [ ] Avaliar uso de job clusters vs all-purpose

## Storage

### Tabelas
- [ ] Identificar tabelas sem leitura há > 90 dias
- [ ] Verificar dados antigos sem acesso
- [ ] Analisar crescimento anormal de tabelas
- [ ] Verificar falta de Z-Ordering
- [ ] Avaliar particionamento adequado
- [ ] Identificar small files (< 128 MB)
- [ ] Verificar tabelas abandonadas (> 180 dias)
- [ ] Analisar uso excessivo de versões Delta
- [ ] Verificar falta de VACUUM e OPTIMIZE
- [ ] Identificar storage duplicado entre workspaces

## Data Governance

### Unity Catalog
- [ ] Verificar uso de Unity Catalog
- [ ] Avaliar necessidade de migração do Hive

### Ownership
- [ ] Verificar ownership de tabelas
- [ ] Identificar tabelas sem owner

### Tags
- [ ] Verificar presença de tags de custo
- [ ] Avaliar tags de domínio/time
- [ ] Verificar classificação de dados

### Políticas
- [ ] Verificar políticas de retenção
- [ ] Avaliar exposição de dados sensíveis
- [ ] Verificar lineage e auditoria

## Pipelines

### Eficiência
- [ ] Identificar pipelines redundantes
- [ ] Verificar full loads desnecessários
- [ ] Avaliar incremental mal implementado
- [ ] Analisar reprocessamentos frequentes

### Orquestração
- [ ] Verificar orquestração ineficiente
- [ ] Analisar pipelines executando fora de horário ideal
- [ ] Verificar dependências entre jobs

## Custos

### Alocação
- [ ] Verificar custos por workspace
- [ ] Analisar custos por cluster
- [ ] Verificar custos por job
- [ ] Avaliar custos por time/domínio
- [ ] Verificar custos por produto de dados

### Métricas
- [ ] Calcular custo por TB processado
- [ ] Calcular custo por tabela
- [ ] Calcular custo por pipeline
- [ ] Calcular custo por SLA

### Tendências
- [ ] Analisar tendências de custo
- [ ] Identificar anomalias
- [ ] Verificar sazonalidade

## Observabilidade

### Monitoramento
- [ ] Verificar cobertura de tags
- [ ] Avaliar qualidade de metadados
- [ ] Verificar logs e monitoramento
- [ ] Analisar dashboards disponíveis

## Ações Prioritárias

### Quick Wins
- [ ] Desligar clusters ociosos
- [ ] Arquivar tabelas abandonadas
- [ ] Executar OPTIMIZE em tabelas com small files
- [ ] Adicionar tags de custo

### Médio Prazo
- [ ] Implementar autoscaling
- [ ] Otimizar particionamento
- [ ] Corrigir jobs com alta taxa de falha
- [ ] Implementar políticas de retenção

### Longo Prazo
- [ ] Migrar para Unity Catalog
- [ ] Implementar governança completa
- [ ] Estabelecer processos contínuos
- [ ] Automatizar otimizações
