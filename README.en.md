> [🇧🇷 Português](README.md) | 🇺🇸 English

# 🏗️ Construction Site Journal

A web-based system for managing construction sites and daily field logs, featuring a control panel, financial tracking, and an AI assistant focused on civil construction.

---

## 💡 Motivation

Managing multiple construction sites simultaneously requires tracking workers, equipment, expenses, and daily weather conditions. This project was built to centralize all that information in a simple and accessible platform, replacing spreadsheets and manual notes.

---

## ✨ Features

- **Site Registration** — register construction sites with address, environment (open, enclosed or mixed), status and schedule stages
- **Stages and physical progress** — each stage has a weight and an estimated duration; the panel shows the site's progress
- **Daily Field Log** — record weather, work location (indoor or outdoor), observations, workers, equipment, and expenses per day
- **Budgets** — material and labor costs with profit as a markup on cost; an approved budget can become a site
- **Control Panel** — daily overview with total workforce, expenses, and weather alerts for outdoor work
- **AI Assistant** — assistant focused on construction; select a specific site for precise and cost-efficient queries
- **Settings** — manage categories for job roles, equipment, and expenses

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Database | SQLite (PostgreSQL is on the roadmap) |
| Frontend | Streamlit |
| AI | Google Gemini (`google-genai`): function calling and schema-validated output |
| Topic search (RAG) | `gemini-embedding-2` + ChromaDB |
| Tests | pytest |
| Version Control | Git + GitHub |

---

## 🚀 Running Locally

Requires Python 3.10 or newer.

### 1. Clone the repository
```bash
git clone https://github.com/Jose-Felipe-N/diario-de-obras-app.git
cd diario-de-obras-app
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your Gemini API key:
```
GEMINI_API_KEY=your_key_here
```
The other variables in `.env.example` are optional (Gemini model, database file, API address, and quota counter file). A variable set in the terminal takes precedence over `.env`.

### 5. Seed the database with sample data (optional)
```bash
python seed.py
```
Loads the evaluation data from the `dados/` folder: 3 sites, 189 daily logs and 6 budgets, dated June to October 2026. ⚠️ The seed **drops and recreates** the database; if it already has sites, it asks for confirmation first (use `--sim` to skip the question). To load into another file without touching your database, set `DIARIO_DB_PATH`.

### 6. Start the backend
```bash
uvicorn main:app --reload
```

### 7. Start the frontend (in a separate terminal)
```bash
streamlit run frontend.py
```

Access at: `http://localhost:8501`

### 8. Run the tests
```bash
pytest
```
The tests use an in-memory database and a temporary quota counter: they don't change your database or call the Gemini API.

---

## 📁 Project Structure

```
📁 diario-de-obras-app/
├── main.py              # API entrypoint
├── config.py            # Settings read from .env and environment variables
├── database.py          # Database connection
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas (API validation)
├── gemini.py            # Single entry point for Gemini calls
├── cota.py              # Gemini daily quota counter
├── frontend.py          # Streamlit interface
├── opcoes_tela.py       # Rules for the editable lists in the UI
├── seed.py              # Loads the sample data into the database
├── requirements.txt
├── .env.example
├── 📁 routers/
│   ├── obras.py
│   ├── diarios.py
│   ├── registros.py     # Workers, equipment and expenses
│   ├── orcamentos.py    # Budgets
│   ├── dashboard.py
│   └── ia.py            # AI assistant endpoints
├── 📁 analista/        # Assistant: tools (SQL), RAG and model loop
├── 📁 dados/            # Shared catalog and assistant evaluation data
├── 📁 avaliacao/        # Evaluation data validation
├── 📁 scripts/          # Development database migrations
├── 📁 tests/
└── 📁 docs/
    └── experimentos.md  # Assistant evaluation method and results (Portuguese)
```

---

## 🤖 AI Assistant

The assistant is powered by Google Gemini and responds **only to questions related to construction and civil engineering**. To optimize API usage, the user selects a specific site before starting the conversation, and the system fetches only that site's data when building the AI context.

The assistant doesn't receive the full logs in the prompt: it queries the data through **tools** (function calling) that run SQL on the server, such as expenses by category, logs for a period, schedule and budget. With a site selected, the server restricts every tool to it. For questions about events ("any water problem?"), a **semantic search** tool (RAG) finds similar observations, even when written with different words.

**About ChromaDB:** with 142 observations, an exact in-memory search would be enough. I used ChromaDB to learn hands-on a vector database used in production (collections, metadata, filters and re-indexing); the trade-off is documented in [docs/experimentos.md](docs/experimentos.md).

Answer quality is being measured with a question set and answer key; the method and results are in [docs/experimentos.md](docs/experimentos.md).

### Gemini daily quota

On the free tier, each model has a requests-per-day limit shared by the whole project, and the day ends at midnight Pacific time. Every call goes through a local counter first; when the quota runs out, the assistant says so instead of failing.

```bash
python cota.py situacao                  # today's usage
python cota.py reservar 2026-10-14       # reserve the day for a measurement run
python cota.py ajustar 2026-10-14 gemini-3.8-flash 12 --motivo "Playground usage"
```

The counter can't see calls made by other means in the same project (the AI Studio Playground, for example); use `ajustar` to match the AI Studio dashboard.

### Data usage

On the Gemini API free tier, submitted content may be used by Google to improve its products. The data in this repository is fictitious. **To use the system with a construction company's real data, use the paid tier**, where content is not used for that purpose.

---

## ⚠️ Known Limitations

- **The API has no authentication.** Don't expose it to the internet (for example, through a tunnel such as ngrok): anyone could read the data and consume the Gemini quota.
- **Lists edited in Settings live only in the browser session**: they are lost when the app restarts, and each browser has its own list.
- **A daily log is saved in several requests** (the log, then each worker, equipment and expense entry); if one fails midway, the log is left incomplete.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file.
