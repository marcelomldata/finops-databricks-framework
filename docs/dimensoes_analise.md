# Dimensões de Análise FinOps

## A. Compute (Clusters & Jobs)

### Métricas Coletadas

#### Clusters
- Estado (RUNNING, TERMINATED, etc.)
- Configuração (workers, memória, CPU)
- Uptime e idle time
- Autoscaling configurado
- Tags e metadados

#### Jobs
- Configuração e schedule
- Histórico de execuções
- Taxa de sucesso/falha
- Duração média/máxima/mínima
- Uso de clusters existentes vs novos

### Análises Realizadas

#### Clusters Ociosos
- Identificação de clusters idle > 4 horas
- Cálculo de horas ociosas
- Estimativa de custo desperdiçado

#### Overprovisioning
- Clusters com muitos workers e baixa utilização
- Memória/CPU subutilizados
- Recomendações de resize

#### Autoscaling
- Verificação de configuração de autoscaling
- Identificação de clusters sem autoscaling que se beneficiariam

#### Jobs Ineficientes
- Jobs com alta taxa de falha
- Jobs com duração anormal
- Jobs sem schedule (execução manual)

### Saídas

- Ranking de clusters mais caros
- Ranking de jobs menos eficientes
- Recomendações de resize, autoscaling ou redesign

## B. Storage (Delta Lake)

### Métricas Coletadas

- Tamanho total e por tabela
- Número de arquivos
- Tamanho médio de arquivo
- Última modificação e acesso
- Particionamento
- Tipo de tabela (Delta, Parquet, etc.)

### Análises Realizadas

#### Dados Frios (Cold Data)
- Tabelas sem acesso há > 90 dias
- Classificação hot/warm/cold
- Estimativa de economia com tiering

#### Tabelas Abandonadas
- Sem acesso há > 180 dias
- Candidatas a arquivamento ou exclusão

#### Small Files
- Arquivos < 128 MB
- Impacto em performance
- Necessidade de OPTIMIZE

#### Particionamento
- Tabelas grandes sem particionamento
- Particionamento inadequado
- Necessidade de Z-ORDER

### Saídas

- Lista de tabelas candidatas a arquivamento
- Lista de tabelas candidatas a exclusão
- Estimativa de economia financeira
- Recomendações de otimização

## C. Data Governance & Qualidade

### Métricas Coletadas

- Tipo de metastore (Unity Catalog vs Hive)
- Ownership de tabelas
- Tags e metadados
- Políticas de retenção

### Análises Realizadas

#### Unity Catalog
- Verificação de uso de Unity Catalog
- Benefícios de migração

#### Ownership
- Tabelas sem owner
- Responsabilidade de dados

#### Tags
- Presença de tags de custo
- Tags de domínio/time
- Classificação de dados

### Saídas

- Score de governança
- Recomendações de melhoria
- Roadmap de migração

## D. Pipelines & Orquestração

### Métricas Coletadas

- Jobs agendados vs manuais
- Taxa de sucesso de pipelines
- Duração e frequência
- Dependências entre jobs

### Análises Realizadas

#### Pipelines Redundantes
- Jobs duplicados
- Full loads desnecessários
- Incremental mal implementado

#### Orquestração
- Jobs sem schedule
- Execuções fora de horário ideal
- Falhas frequentes

### Saídas

- Score de pipelines
- Recomendações de otimização
- Identificação de redundâncias

## E. Custos & Billing

### Métricas Coletadas

- Custos diários por workspace
- Custos por recurso (cluster, job)
- Custos por serviço
- Tendências de custo

### Análises Realizadas

#### Tendências
- Aumento/redução de custos
- Sazonalidade
- Projeções

#### Alocação
- Custo por workspace
- Custo por time/domínio
- Custo por produto de dados

### Saídas

- Dashboards de custo
- Alertas de anomalias
- Projeções futuras

## F. Observabilidade

### Métricas Coletadas

- Tags em clusters e jobs
- Metadados disponíveis
- Logs e monitoramento

### Análises Realizadas

#### Tagging
- Cobertura de tags
- Qualidade de tags
- Uso para cost allocation

### Saídas

- Score de observabilidade
- Recomendações de tagging
- Melhorias de monitoramento
