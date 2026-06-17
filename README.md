# 🏗️ Diário de Obras

Sistema web para gerenciamento de obras e diários de campo, com painel de controle, controle financeiro e assistente de inteligência artificial focado em construção civil.

---

## 💡 Motivação

Gerenciar múltiplas obras ao mesmo tempo envolve controlar trabalhadores, equipamentos, gastos e condições climáticas diariamente. Este projeto nasceu para centralizar essas informações em uma plataforma simples e acessível, eliminando planilhas e anotações manuais.

---

## ✨ Funcionalidades

- **Cadastro de Obras** — registre obras com endereço, ambiente e status
- **Diário de Campo** — registre clima, observações, trabalhadores, equipamentos e gastos por dia
- **Painel de Controle** — visão geral do dia com efetivo total, gastos e alertas climáticos
- **Analista IA** — assistente inteligente focado em obras; selecione uma obra específica para consultas precisas e econômicas
- **Configurações** — gerencie as categorias de funções, equipamentos e gastos

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Banco de dados | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Streamlit |
| IA | Google Gemini (`google-genai`) |
| Versionamento | Git + GitHub |

---

## 🚀 Como rodar localmente

### 1. Clone o repositório
```bash
git clone https://github.com/Jose-Felipe-N/diario-de-obras.git
cd diario-de-obras
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

### 5. Popule o banco com dados fictícios (opcional)
```bash
python seed.py
python seed_etapas.py
```

### 6. Inicie o backend
```bash
uvicorn main:app --reload
```

### 7. Inicie o frontend (em outro terminal)
```bash
streamlit run frontend.py
```

Acesse em: `http://localhost:8501`

---

## 📁 Estrutura do projeto

```
📁 diario-de-obras/
├── main.py              # Entrypoint da API
├── database.py          # Configuração do banco de dados
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Schemas Pydantic
├── frontend.py          # Interface Streamlit
├── seed.py              # Dados fictícios de obras
├── seed_etapas.py       # Dados fictícios de etapas
├── requirements.txt
├── .env.example
└── 📁 routers/
    ├── obras.py
    ├── diarios.py
    ├── registros.py     # Efetivos, equipamentos e gastos
    ├── dashboard.py
    └── ia.py            # Endpoints do assistente IA
```

---

## 🤖 Assistente IA

O assistente é alimentado pelo Google Gemini e responde **apenas perguntas relacionadas a obras e construção civil**. Para otimizar o uso de créditos da API, o usuário seleciona uma obra específica antes de iniciar a conversa — o sistema busca apenas os dados daquela obra ao montar o contexto para a IA.

---

## 📄 Licença

Este projeto está sob a licença MIT.
