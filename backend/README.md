# UFDR Analysis Platform - Backend Service

FastAPI-based backend service providing REST APIs, database management, and forensic processing pipelines.

## Setup & Local Execution

### Prerequisites
- Python 3.10+ installed

### Environment Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Adjust environment variables in `.env`:
   - Set `EXTERNAL_LLM_API_KEY` (Groq API key from https://console.groq.com) for fast default cloud LLM Q&A inference.
   - `GROQ_MODEL` defaults to `llama-3.3-70b-versatile`.

### Virtual Environment Setup
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

- **Default Mode (`llm_provider: "external"`)**: Fast hosted Groq inference (`llama-3.3-70b-versatile`). Prompts are 100% pseudonymized and minimized by the Phase 9 Privacy Gateway before transmission.
- **Auto-Fallback Mode (`llm_provider: "auto"`)**: Tries Groq first; if Groq is unavailable, automatically falls back to local Ollama / local synthesis engine with `fallback_used: true`.
- **Air-Gapped Local Mode (`llm_provider: "local"`)**: Forces 100% offline local inference via local Ollama (`ollama/llama3.1:8b`) with zero cloud data transmission.

---

## Running Tests

Execute the automated test suite using `pytest`:

```bash
# Make sure virtual environment is active
pytest -v
```
