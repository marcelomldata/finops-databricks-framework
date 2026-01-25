# Guia de Contribuição

Obrigado por considerar contribuir para o FinOps Databricks Framework! Este documento fornece diretrizes para contribuições.

## Como Contribuir

### Reportar Bugs

1. Verifique se o bug já não foi reportado nas [Issues](https://github.com/[seu-repo]/issues)
2. Se não existir, crie uma nova issue com:
   - Título descritivo
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Ambiente (cloud, versão Databricks, etc.)

### Sugerir Funcionalidades

1. Verifique se a funcionalidade já não foi sugerida
2. Crie uma issue com tag `enhancement`
3. Descreva:
   - O problema que resolve
   - Como funcionaria
   - Benefícios para a comunidade

### Contribuir com Código

1. **Fork o repositório**
2. **Crie uma branch** para sua feature/fix:
   ```bash
   git checkout -b feature/minha-feature
   ```
3. **Siga os padrões de código**:
   - PEP 8 para Python
   - Sem comentários excessivos (código autoexplicativo)
   - Funções pequenas e determinísticas
   - Testes quando aplicável
4. **Commit suas mudanças**:
   ```bash
   git commit -m "feat: adiciona funcionalidade X"
   ```
5. **Push para sua branch**:
   ```bash
   git push origin feature/minha-feature
   ```
6. **Abra um Pull Request**

### Convenções de Commit

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Mudanças na documentação
- `style:` Formatação, sem mudança de código
- `refactor:` Refatoração de código
- `test:` Adição de testes
- `chore:` Tarefas de manutenção

### Padrões de Código

- **Python**: PEP 8
- **Sem comentários**: Código deve ser autoexplicativo
- **Funções pequenas**: Máximo 50 linhas quando possível
- **Nomes descritivos**: Variáveis e funções com nomes claros
- **Type hints**: Quando aplicável
- **Docstrings**: Apenas para funções públicas complexas

### Estrutura do Projeto

```
finops-databricks/
├── src/              # Código fonte
├── notebooks/        # Notebooks de execução
├── sql/              # DDLs e queries
├── config/           # Configurações
├── docs/             # Documentação
└── tests/            # Testes (futuro)
```

### Testes

- Testes unitários para funções críticas
- Testes de integração para fluxos completos
- Manter cobertura acima de 70%

### Documentação

- Atualizar documentação quando necessário
- Adicionar exemplos quando apropriado
- Manter HOW TO atualizado

## Processo de Review

1. Pull requests serão revisados por mantenedores
2. Feedback será fornecido via comentários
3. Mudanças podem ser solicitadas
4. Após aprovação, o PR será mergeado

## Código de Conduta

- Seja respeitoso
- Aceite críticas construtivas
- Foque no que é melhor para o projeto
- Mostre empatia com outros membros da comunidade

## Perguntas?

Abra uma issue com tag `question` ou entre em contato com os mantenedores.

Obrigado por contribuir! 🚀
