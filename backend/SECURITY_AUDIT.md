# UFDR Analysis Platform — Security & Privacy Audit Report

**Target Platform**: Ministry of Home Affairs (India) UFDR Analysis Tool  
**Audit Scope**: Backend & Frontend Codebase (Phases 0–11)  
**Audit Date**: August 2026  

---

## Executive Summary
A comprehensive security and privacy audit was conducted across the monorepo prior to hackathon demonstration. The platform enforces a strict **local-by-default architecture** with ground-truth evidence isolation, mandatory identity pseudonymization, JWT authentication, and auditable logging.

---

## 1. Secret Scanning & Credential Hardening
- **Hardcoded Secrets**: Verified zero hardcoded API keys, JWT secrets, or database passwords in source code.
- **Config Management**: All sensitive parameters (`JWT_SECRET_KEY`, `EXTERNAL_LLM_API_KEY`, `OLLAMA_HOST`, `DATABASE_URL`) are read via environment variables (`app/core/config.py`).
- **Demo Credentials**: Demo credentials (`investigator` / `demo123`) are restricted to development seeding scripts (`scripts/seed_demo_user.py`) and clearly marked as non-production credentials.

---

## 2. Authentication & Session Security
- **Authentication**: JWT token verification (`pyjwt`) enforced via `get_current_user` FastAPI dependency across all forensic endpoints (`/reports`, `/evidence`, `/relationships`, `/findings`, `/timeline`, `/graph`, `/query`, `/answer`, `/privacy`).
- **Password Protection**: Passwords hashed using bcrypt with salt rounds (`passlib[bcrypt]`). Plaintext passwords are never logged or stored.
- **Token Expiry**: Default access token duration set to 8 hours (standard working shift).
- **Session Storage**: Frontend token stored in `sessionStorage` (cleared upon browser tab closure) rather than persistent unencrypted `localStorage`.

---

## 3. Data Isolation & Privacy Gateway Safeguards
- **Pseudonym Mapping Table**: The `PseudonymMapping` table exists exclusively in local database storage and is **structurally prohibited** from public API serialization.
- **Mandatory Pseudonymization**: All prompts sent to local Ollama and external LLMs are deep-copied and pseudonymized (`PERSON_001`, `PHONE_001`). Real identities are restored ONLY when rendering final UI responses to authenticated investigators.
- **Type-Enforced External Client**: `ExternalLLMClient` strictly accepts minimized payloads (`privacy_level="MINIMIZED_PSEUDONYMIZED"`). Passing a raw `RetrievalResult` instance raises an immediate runtime `TypeError`.
- **No Silent Fallback**: Unconfigured external LLM requests return an explicit HTTP 503 error without silently exposing data to fallback paths.

---

## 4. Network & CORS Configuration
- **CORS Scoping**: Configured via `ALLOWED_ORIGINS` setting (`http://localhost:5173`, `http://localhost:3000`). Wildcard `*` origins are disabled in production configurations.
- **Public Endpoints**: Restricted to system health check (`/api/v1/health`), root (`/`), and login (`/api/v1/auth/login`).

---

## 5. Audit Logging & Non-Repudiation
- **Audit Logging**: `AuditLog` table immutably logs evidence views, investigator queries, and LLM dispatches.
- **User Accountability**: Audit logs record the authenticated investigator's `username` for complete accountability.
- **Non-Deletable Log**: No API endpoint allows deletion or alteration of audit log records.

---

## 6. Dependency Vulnerability Review
- **Installed Packages**: `fastapi`, `sqlalchemy`, `pydantic`, `pyjwt`, `passlib[bcrypt]`, `spacy`, `requests`, `networkx`.
- **Pre-Production Recommendation**: Run `pip-audit` or `safety check` prior to government on-premise deployment to patch minor transitive dependency updates.
