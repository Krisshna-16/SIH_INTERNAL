# UFDR Analysis Platform - Backend Service

FastAPI-based backend service providing REST APIs, database management, and forensic processing pipelines.

## Setup & Local Execution

### Prerequisites
- Python 3.10+ installed
- Docker & Docker Compose (optional for local PostgreSQL instance)

### Database Configuration (PostgreSQL & SQLite Fallback)

The platform supports both **PostgreSQL** (Production / Docker) and **SQLite** (Local Fallback):

1. **Copy Environment File**:
   ```bash
   cp .env.example .env
   ```

2. **Option A: PostgreSQL via Docker Compose (Recommended)**:
   ```bash
   # Start local PostgreSQL container in background
   docker-compose up -d

   # Set DATABASE_URL in .env:
   # DATABASE_URL=postgresql://ufdr_user:ufdr_pass@localhost:5432/ufdr_db
   ```

3. **Option B: SQLite Local Fallback**:
   ```bash
   # Set DATABASE_URL in .env:
   # DATABASE_URL=sqlite:///./ufdr.db
   ```

### Database Schema Migrations (Alembic)

```bash
# Run database migrations to bring target schema up to date
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "description_of_changes"
```

### Data Migration (SQLite to PostgreSQL)

To transfer existing SQLite demo datasets to PostgreSQL:
```bash
python scripts/migrate_sqlite_to_postgres.py
```

---

## Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Redoc documentation: `http://localhost:8000/redoc`
- Health check endpoint: `http://localhost:8000/api/v1/health`

---

## LLM Provider Configuration & Air-Gapped Mode

- **Default Mode (`llm_provider: "external"`)**: Fast hosted Groq inference (`openai/gpt-oss-20b`). Prompts are 100% pseudonymized and minimized by the Phase 9 Privacy Gateway before transmission.
- **Auto-Fallback Mode (`llm_provider: "auto"`)**: Tries Groq first; if Groq is unavailable, automatically falls back to local Ollama / local synthesis engine with `fallback_used: true`.
- **Air-Gapped Local Mode (`llm_provider: "local"`)**: Forces 100% offline local inference via local Ollama (`ollama/llama3.1:8b`) with zero cloud data transmission.

---

## Running Tests

Execute the automated test suite using `pytest`:

```bash
# Make sure virtual environment is active
pytest -v
```
