# GitHub Pulse 📈

Monitor automático dos **meus repositórios públicos**. Este projeto consulta diariamente a API do GitHub e registra métricas reais (repositórios próprios, estrelas, forks e issues abertas), com um histórico consultável.

**[Abrir painel atualizado →](STATUS.md)**

### Como funciona

- O GitHub Actions executa o programa em Python diariamente às **09h17** (America/Fortaleza), com uma segunda tentativa às **18h37**.
- O programa consulta `GET /users/{username}/repos` e coleta todos os projetos públicos próprios (sem forks e sem este repositório de monitoramento).
- Cada dia fica salvo em `data/daily/AAAA-MM-DD.json`.
- `data/history.csv` e `STATUS.md` são reconstruídos automaticamente, assim como o gráfico `assets/stars.svg`.
- **No máximo uma coleta é registrada por dia**: a segunda execução não gera commits adicionais se a primeira já terminou.
- Os commits são **automáticos e não indicam trabalho manual de desenvolvimento no dia**.

### Estrutura

```text
.github/workflows/daily.yml    Agendamento GitHub Actions
scripts/collect.py             Coleta, histórico, painel e SVG
tests/test_collect.py          Testes sem depender da internet
data/daily/                    Um JSON por dia (criado automaticamente)
data/history.csv               Série histórica (criada automaticamente)
STATUS.md                      Painel (criado automaticamente)
assets/stars.svg               Gráfico (criado automaticamente)
```

### Ativar na sua conta

1. Crie um **novo repositório** pessoal, público, com a branch padrão `main` (não um fork).
2. Adicione estes arquivos preservando as pastas, principalmente `.github/workflows/daily.yml`.
3. Em **Settings → Actions → General → Workflow permissions**, verifique se as políticas do repositório permitem gravação pelo `GITHUB_TOKEN`. O workflow solicita `contents: write`.
4. Abra **Actions → GitHub Pulse - coleta diaria → Run workflow**, selecione `main` e execute uma vez.
5. Confirme a criação de `STATUS.md`, `data/history.csv`, `assets/stars.svg` e do primeiro `data/daily/AAAA-MM-DD.json`.
6. A partir daí, acompanhe a execução em **Actions**.

Não precisa gerar um Personal Access Token (PAT). O `GITHUB_TOKEN` fornecido pelo próprio GitHub Actions é suficiente.

### Execução local opcional

```bash
export PULSE_USERNAME="SEU_USUARIO"
export PULSE_IGNORE_REPO="SEU_USUARIO/github-pulse"
python -m unittest discover -s tests -v
python scripts/collect.py
```

No PowerShell, use `$env:PULSE_USERNAME="SEU_USUARIO"` e `$env:PULSE_IGNORE_REPO="SEU_USUARIO/github-pulse"`.

### Limites e observações

- A coleta monitora **somente repositórios públicos**. Repositórios privados não ficam expostos.
- O campo `open_issues_count` da API também pode incluir pull requests abertos, então é uma aproximação.
- Horários de agendamento do GitHub Actions podem sofrer atrasos ou execuções perdidas. O segundo horário ajuda, mas **não garante execução todos os dias**.
- O GitHub pode desabilitar workflows agendados em repositórios públicos sem atividade por 60 dias. Verifique o status em Actions periodicamente.
- Para que os commits apareçam no gráfico de contribuições, a autoria de e-mail deve estar associada ao usuário; o workflow utiliza o `noreply` numérico do usuário que disparou a execução. O repositório precisa ser próprio e os commits devem estar na branch padrão.
- Quando os dados permanecerem iguais, a nova observação diária continua útil para uma série temporal. Ainda assim, ela não deve ser confundida com uma nova funcionalidade de software desenvolvida naquele dia.

Este é um projeto pessoal de automação, coleta de dados e visualização. Licença MIT.
