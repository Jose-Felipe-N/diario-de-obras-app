> [🇧🇷 Português](README.md) | 🇺🇸 English

# 🏗️ Construction Site Journal

A web-based system for managing construction sites and daily field logs, featuring a control panel, financial tracking, and an AI assistant focused on civil construction.

---

## 💡 Motivation

Managing multiple construction sites simultaneously requires tracking workers, equipment, expenses, and daily weather conditions. This project was built to centralize all that information in a simple and accessible platform, replacing spreadsheets and manual notes.

---

## ✨ Features

- **Site Registration** — register construction sites with address, environment type, and status
- **Daily Field Log** — record weather, observations, workers, equipment, and expenses per day
- **Control Panel** — daily overview with total workforce, expenses, and weather alerts
- **AI Assistant** — smart assistant focused on construction; select a specific site for precise and cost-efficient queries
- **Settings** — manage categories for job roles, equipment, and expenses

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Streamlit |
| AI | Google Gemini (`google-genai`) |
| Version Control | Git + GitHub |

---

## 🚀 Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/Jose-Felipe-N/diario-de-obras.git
cd diario-de-obras
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

### 5. Seed the database with sample data (optional)
```bash
python seed.py
python seed_etapas.py
```

### 6. Start the backend
```bash
uvicorn main:app --reload
```

### 7. Start the frontend (in a separate terminal)
```bash
streamlit run frontend.py
```

Access at: `http://localhost:8501`

---

## 📁 Project Structure

```
📁 diario-de-obras/
├── main.py              # API entrypoint
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── frontend.py          # Streamlit interface
├── seed.py              # Sample construction site data
├── seed_etapas.py       # Sample stages and logs data
├── requirements.txt
├── .env.example
└── 📁 routers/
    ├── obras.py
    ├── diarios.py
    ├── registros.py     # Workers, equipment and expenses
    ├── dashboard.py
    └── ia.py            # AI assistant endpoints
```

---

## 🤖 AI Assistant

The assistant is powered by Google Gemini and responds **only to questions related to construction and civil engineering**. To optimize API credit usage, the user selects a specific site before starting the conversation — the system fetches only that site's data when building the AI context.

---

## 📄 License

This project is licensed under the MIT License.
