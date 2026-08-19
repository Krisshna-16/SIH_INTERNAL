# UFDR Analysis Platform - Frontend UI

React + TypeScript + Vite web UI for investigator workflows and platform monitoring.

## Local Setup & Execution

### Prerequisites
- Node.js 18+ and npm 9+ installed

### Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

### Installation
```bash
npm install
```

### Running Development Server
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Manual Verification Steps

1. Start the backend server (`uvicorn app.main:app --reload` inside `../backend`).
2. Run `npm run dev` in this directory and open `http://localhost:5173`.
3. Verify that the **StatusBadge** displays **"Connected"** (green badge).
4. Verify that the **Live Response Data** card displays valid JSON returned from `/api/v1/health` (app name, environment, timestamp).
5. Stop the backend server (Ctrl+C).
6. Click **"Refresh Health Status"** on the frontend page and verify that the badge gracefully transitions to **"Disconnected"** (red badge) and displays an error message without crashing.
