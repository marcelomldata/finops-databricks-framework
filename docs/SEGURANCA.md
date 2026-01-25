# Segurança - FinOps Databricks Framework

## Proteção de Credenciais

Este documento descreve as práticas de segurança implementadas no framework para proteger credenciais e informações sensíveis.

## Arquivos Bloqueados pelo .gitignore

O framework bloqueia automaticamente os seguintes padrões de arquivos sensíveis:

### Credenciais e Tokens
- `**/tokens/` - Qualquer pasta de tokens
- `**/secrets/` - Qualquer pasta de secrets
- `*.pem` - Certificados PEM
- `*.pfx` - Certificados PFX
- `*.key` - Chaves privadas
- `*.secret` - Arquivos de secret
- `*.token` - Arquivos de token
- `*.passwd` - Arquivos de senha
- `*.password` - Arquivos de senha

### Configurações Sensíveis
- `*databricks*.cfg` - Configurações do Databricks
- `*profile*` - Perfis de configuração
- `*credentials*.json` - Credenciais em JSON
- `*credentials*.yaml` - Credenciais em YAML
- `*credentials*.yml` - Credenciais em YAML

### Cloud Provider Credentials
- `**/azure-credentials.json` - Credenciais Azure
- `**/aws-credentials` - Credenciais AWS
- `**/gcp-credentials.json` - Credenciais GCP
- `**/gcp-service-account.json` - Service Account GCP
- `**/.aws/` - Pasta de configuração AWS
- `**/.azure/` - Pasta de configuração Azure
- `**/.gcp/` - Pasta de configuração GCP

### Infrastructure as Code
- `terraform.tfstate` - Estado do Terraform
- `terraform.tfstate.*` - Backups de estado
- `*.tfstate` - Qualquer arquivo de estado
- `.terraform/` - Pasta do Terraform
- `.terraform.lock.hcl` - Lock do Terraform

### Arquivos Locais
- `.env` - Variáveis de ambiente
- `config/local/` - Configurações locais
- `*.local.yaml` - Configs locais
- `notebooks/local/` - Notebooks locais
- `docs/local/` - Documentação local

## Boas Práticas

### 1. Uso de Arquivos .env

✅ **Correto:**
```bash
# Usar arquivo .env local (não versionado)
cp env.example .env
# Editar .env com credenciais reais
```

❌ **Incorreto:**
```bash
# NUNCA commitar .env com credenciais
git add .env  # ERRO!
```

### 2. Variáveis de Ambiente do Sistema

Para ambientes de produção, use variáveis de ambiente do sistema:

```bash
export DATABRICKS_TOKEN="dapi..."
export AZURE_CLIENT_SECRET="..."
```

### 3. Secret Managers (Produção)

Para ambientes de produção, use secret managers:

**Azure:**
- Azure Key Vault
- Managed Identity

**AWS:**
- AWS Secrets Manager
- IAM Roles

**GCP:**
- GCP Secret Manager
- Service Accounts

### 4. Rotação de Tokens

- Rotacione tokens regularmente (recomendado: a cada 90 dias)
- Revogue tokens não utilizados
- Use princípio do menor privilégio

### 5. Permissões de Tokens

Configure tokens com permissões mínimas necessárias:
- Apenas leitura para coleta de métricas
- Sem permissões de escrita desnecessárias
- Sem permissões administrativas

### 6. Auditoria

- Monitore uso de tokens
- Revise logs de acesso regularmente
- Configure alertas para uso anormal

## Verificação de Segurança

### Verificar se Credenciais Estão Versionadas

```bash
# Verificar se há arquivos sensíveis no repositório
git ls-files | grep -E '\.(pem|pfx|key|secret|token|passwd|password)$'
git ls-files | grep -E '(tokens|secrets|credentials|\.env)$'

# Verificar histórico por credenciais acidentalmente commitadas
git log --all --full-history --source -- '*credentials*'
git log --all --full-history --source -- '*.env'
```

### Limpar Credenciais do Histórico (se necessário)

Se credenciais foram acidentalmente commitadas:

```bash
# ⚠️ CUIDADO: Operação destrutiva!
# 1. Fazer backup
# 2. Usar git-filter-branch ou BFG Repo-Cleaner
# 3. Force push (após validação)
```

**Recomendação:** Use ferramentas como `git-secrets` ou `truffleHog` para prevenir commits acidentais.

## Templates de Configuração

O framework fornece templates sem credenciais:

- `env.example` - Template simplificado
- `config/example.env` - Template detalhado com instruções

**Nunca** inclua credenciais reais nestes arquivos.

## Checklist de Segurança

Antes de fazer commit:

- [ ] Verificar que `.env` não está no staging
- [ ] Verificar que não há arquivos `*.pem`, `*.key`, `*.pfx`
- [ ] Verificar que não há pastas `tokens/` ou `secrets/`
- [ ] Verificar que não há `terraform.tfstate*`
- [ ] Verificar que não há credenciais em código
- [ ] Verificar que templates não contêm credenciais reais

## Incidentes de Segurança

Se credenciais forem expostas:

1. **Imediato:**
   - Revogar credenciais expostas
   - Rotacionar todas as credenciais relacionadas

2. **Curto Prazo:**
   - Remover credenciais do histórico Git
   - Notificar equipe de segurança
   - Revisar logs de acesso

3. **Longo Prazo:**
   - Implementar secret scanning
   - Revisar processos de segurança
   - Treinar equipe

## Ferramentas Recomendadas

- **git-secrets** - Previne commits de secrets
- **truffleHog** - Scanner de secrets em repositórios
- **gitleaks** - Detector de secrets
- **pre-commit hooks** - Validação antes de commits

## Referências

- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_cryptographic_key)
- [Git Security Best Practices](https://git-scm.com/docs/gitignore)
- [Databricks Security Best Practices](https://docs.databricks.com/security/)
