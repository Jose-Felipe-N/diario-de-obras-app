> 🇧🇷 Português | [🇺🇸 English](README.en.md)


# 🏗️ Diário de Obras

Sistema web para gerenciamento de obras e diários de campo, com painel de controle, controle financeiro e assistente de inteligência artificial focado em construção civil.

---

## 💡 Motivação

Gerenciar múltiplas obras ao mesmo tempo envolve controlar trabalhadores, equipamentos, gastos e condições climáticas diariamente. Este projeto nasceu para centralizar essas informações em uma plataforma simples e acessível, eliminando planilhas e anotações manuais.

---

## ✨ Funcionalidades

- **Cadastro de Obras** — registre obras com endereço, ambiente (aberto, fechado ou misto), status e etapas do cronograma
- **Etapas e progresso físico** — escolha as etapas do contrato (a obra inteira ou só parte dela) e a tabela se monta com pesos somando 100% e prazos sugeridos, tudo editável; o painel mostra o progresso da obra
- **Diário de Campo** — registre clima, local de trabalho (interior ou exterior), observações, trabalhadores, equipamentos e gastos por dia; copie a equipe do diário anterior com um clique, e o diário é gravado inteiro ou nada (um erro não deixa diário pela metade nem apaga o que foi digitado)
- **Orçamentos** — custos de material e mão de obra com lucro por markup sobre o custo; um orçamento aprovado pode virar obra
- **Painel de Controle** — visão geral do dia com efetivo total, gastos, alertas de clima para o trabalho feito ao ar livre e as obras que ainda não têm o diário de hoje
- **Analista IA** — assistente focado em obras; selecione uma obra específica para consultas precisas e econômicas. Cada resposta mostra o que foi consultado ("Como cheguei a essa resposta") e pode ser avaliada com 👍/👎
- **Configurações** — gerencie as categorias de funções, equipamentos e gastos

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Banco de dados | SQLite (PostgreSQL está no roadmap) |
| Frontend | Streamlit |
| IA | Google Gemini (`google-genai`): function calling e saída validada por schema |
| Busca por tema (RAG) | `gemini-embedding-2` + ChromaDB |
| Testes | pytest |
| Versionamento | Git + GitHub |

---

## 🚀 Como rodar localmente

Requer Python 3.10 ou mais recente.

### 1. Clone o repositório
```bash
git clone https://github.com/Jose-Felipe-N/diario-de-obras-app.git
cd diario-de-obras-app
```

### 2. Crie e ative o ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` e preencha sua chave da API do Gemini:
```
GEMINI_API_KEY=sua_chave_aqui
```
As demais variáveis do `.env.example` são opcionais (modelo do Gemini, arquivo do banco, endereço da API e arquivo do contador de cota). Uma variável definida no terminal tem prioridade sobre o `.env`.

### 5. Popule o banco com dados fictícios (opcional)
```bash
python seed.py
```
Carrega os dados de avaliação da pasta `dados/`: 3 obras, 189 diários e 6 orçamentos, com datas de junho a outubro de 2026. ⚠️ O seed **apaga e recria** o banco; se ele já tiver obras, pede confirmação antes (use `--sim` para não perguntar). Para carregar em outro arquivo sem tocar no seu banco, defina `DIARIO_DB_PATH`.

### 6. Inicie o backend
```bash
uvicorn main:app --reload
```

### 7. Inicie o frontend (em outro terminal)
```bash
streamlit run frontend.py
```

Acesse em: `http://localhost:8501`

### 8. Rode os testes
```bash
pytest
```
Os testes usam um banco em memória e um contador de cota temporário: não alteram o seu banco nem chamam a API do Gemini.

---

## 📁 Estrutura do projeto

```
📁 diario-de-obras-app/
├── main.py              # Entrypoint da API
├── config.py            # Configuração lida do .env e de variáveis de ambiente
├── database.py          # Conexão com o banco
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Schemas Pydantic (validação da API)
├── gemini.py            # Ponto único de chamada ao Gemini
├── cota.py              # Contador da cota diária do Gemini
├── frontend.py          # Interface Streamlit
├── opcoes_tela.py       # Regras das listas editáveis da tela
├── confirmacoes.py      # Textos das confirmações de exclusão
├── cronograma.py        # Monta o cronograma a partir das etapas do contrato
├── tela_analista.py     # Fontes consultadas e sugestões do Analista IA
├── formatos.py          # Datas no formato brasileiro
├── seed.py              # Carrega os dados fictícios no banco
├── requirements.txt
├── .env.example
├── 📁 routers/
│   ├── obras.py
│   ├── diarios.py
│   ├── registros.py     # Efetivos, equipamentos e gastos
│   ├── orcamentos.py
│   ├── dashboard.py
│   └── ia.py            # Endpoints do assistente IA
├── 📁 analista/        # Assistente: ferramentas (SQL), RAG e laço com o modelo
├── 📁 dados/            # Catálogo único e dados de avaliação do assistente
├── 📁 avaliacao/        # Validação dos dados de avaliação
├── 📁 scripts/          # Migrações do banco de desenvolvimento
├── 📁 tests/
└── 📁 docs/
    └── experimentos.md  # Método e resultados da avaliação do assistente
```

---

## 🤖 Assistente IA

O assistente é alimentado pelo Google Gemini e responde **apenas perguntas relacionadas a obras e construção civil**. Para otimizar o uso da API, o usuário seleciona uma obra específica antes de iniciar a conversa, e o sistema busca apenas os dados daquela obra ao montar o contexto para a IA.

O assistente não recebe os diários inteiros no prompt: ele consulta os dados por **ferramentas** (function calling) que rodam SQL no servidor, como gastos por categoria, diários de um período, cronograma e orçamento. Com uma obra selecionada, o servidor restringe todas as ferramentas a ela. Para perguntas sobre acontecimentos ("teve problema com água?"), uma ferramenta de **busca por significado** (RAG) encontra as observações parecidas, mesmo escritas com outras palavras.

**Sobre o ChromaDB:** com 142 observações, uma busca exata em memória seria suficiente. Usei o ChromaDB para aprender na prática um banco vetorial usado em produção (coleções, metadados, filtros e reindexação); o trade-off está documentado em [docs/experimentos.md](docs/experimentos.md).

A qualidade das respostas está sendo medida com um conjunto de perguntas e gabarito; o método e os resultados ficam em [docs/experimentos.md](docs/experimentos.md).

### Cota diária do Gemini

No nível gratuito, cada modelo tem um limite de requisições por dia que vale para o projeto inteiro, e o dia termina à meia-noite do horário do Pacífico (4h ou 5h de Brasília). Toda chamada passa por um contador local antes de sair; quando a cota acaba, o assistente avisa em vez de falhar.

```bash
python cota.py situacao                  # uso de hoje
python cota.py reservar 2026-10-14       # reserva o dia para uma medição
python cota.py ajustar 2026-10-14 gemini-3.8-flash 12 --motivo "uso no Playground"
```

O contador não enxerga chamadas feitas por outros meios no mesmo projeto (o Playground do AI Studio, por exemplo); use `ajustar` para corrigir pelo painel do AI Studio.

### Uso de dados

No nível gratuito da API do Gemini, o conteúdo enviado pode ser usado pelo Google para melhorar os seus produtos. Os dados deste repositório são fictícios. **Para usar o sistema com dados reais de uma construtora, use o nível pago**, em que o conteúdo não é usado para esse fim.

As avaliações 👍/👎 do Analista IA ficam em `feedback/avaliacoes.jsonl` (fora do git), com a pergunta, a resposta e o que foi consultado. As respostas com 👎 são candidatas a virar perguntas novas do conjunto de avaliação.

---

## 🎬 Demonstração

Para ver o assistente com os dados de avaliação (3 obras, de junho a outubro de 2026) sem mexer no seu banco, use um arquivo separado e a data de referência dos dados:

```bash
# Git Bash; no PowerShell, use $env:NOME="valor" antes de cada comando
export DIARIO_DB_PATH=demo.db DATA_REFERENCIA=2026-10-08
python seed.py --sim
uvicorn main:app --reload        # em outro terminal, com as mesmas variáveis:
streamlit run frontend.py
```

Perguntas para testar no Analista IA: "teve algum problema com água aí na casa?" (Casa Condomínio), "qual obra tá atrasada?" (visão geral), "me passa uma receita de bolo" (fora do escopo).

### Resultados preliminares da avaliação

Mesmo modelo (`gemini-3.8-flash`), mesmos dados e 10 perguntas escolhidas antes da medição, cobrindo todos os grupos. "Antes" é a tag `baseline` (todos os diários no prompt); "depois" é o assistente com ferramentas e busca por tema.

| | Antes | Depois |
|---|---|---|
| Respostas corretas | 4 de 10 | 8 de 10 |
| Tokens por pergunta (mediana) | ~19,8 mil | ~5,5 mil |
| Chamadas ao modelo por pergunta (média) | 1 | 2,6 |
| Latência (mediana) | 24 s | 67 s |

É um conjunto pequeno e com uma rodada só: diferenças de 1 ou 2 perguntas podem ser variação do modelo. Método, correção de cada resposta, falhas e limitações em [docs/experimentos.md](docs/experimentos.md).

---

## ⚠️ Limitações conhecidas

- **A API não tem autenticação.** Não a exponha na internet (por exemplo, com um túnel como o ngrok): qualquer pessoa poderia ler os dados e consumir a cota do Gemini.
- **As listas editadas em Configurações vivem só na sessão do navegador**: somem quando o app reinicia e cada navegador tem a sua lista.
- **O lançamento de um diário é feito em várias requisições** (o diário e depois cada efetivo, equipamento e gasto); se uma falhar no meio, o diário fica incompleto.

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
