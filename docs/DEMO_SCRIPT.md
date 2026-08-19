# UFDR Analysis Platform — Hackathon Demonstration Script

**Target Audience**: Ministry of Home Affairs (India) Evaluation Committee  
**Total Duration**: 7–10 Minutes  
**Demonstrator Role**: Senior Digital Forensics Investigator  

---

## Stage 1: Platform Ingestion & Authentication (1 Min)
1. **Launch App**: Open browser to `http://localhost:5173`.
2. **Login**: Log in with demo investigator credentials:
   - **Username**: `investigator`
   - **Password**: `demo123`
3. **Landing Page**: Point out the report list and upload card. Click **"Open →"** on `UFDR_Case_MHA_2024_DEMO.xml`.

---

## Stage 2: Executive Dashboard & Guided Pipeline (2 Mins)
1. **Dashboard Overview**: Explain report summary metadata (3 pages, processing status `extracted`).
2. **Run Full Pipeline**: Click **"▶ Extract → Consolidate → Analyze"**. Show step-by-step progress tracking:
   - ✓ Phase 2: Neural Entity Extraction (spaCy NLP)
   - ✓ Phase 3: Evidence Consolidation
   - ✓ Phase 4: Symbolic AI Rule Analysis
3. **Category Breakdown**: Highlight category breakdown (Persons, Phone Numbers, Emails, Locations, IP Addresses).

---

## Stage 3: Explainable Rule Findings & Relationships (2 Mins)
1. **Navigate to Findings**: Click **"Phase 4: Findings"** in sidebar.
2. **Inspect Flagged Anomaly**:
   - Point out **HIGH SEVERITY** finding: `Burst Communication Pattern`.
   - Explain rule logic: Multiple calls/messages between *Vikram Malhotra* and *Rahul Sharma* within a tight 15-minute window.
   - Click **"▼ View Linked Evidence"** to demonstrate ground-truth provenance tracing down to specific page numbers and confidence scores.
3. **Navigate to Relationships**: Show **FACT** vs **INFERENCE** classification tags (e.g. `(Vikram Malhotra) --[CONTACTED]--> (Rahul Sharma)`).

---

## Stage 4: Timeline & Knowledge Graph Visualizations (2 Mins)
1. **Timeline Analysis**: Click **"Phase 5: Timeline"**. Filter by date `12 March 2024` to observe chronological event progression.
2. **Knowledge Graph**: Click **"Phase 6: Knowledge Graph"**. Show interactive node-edge network. Click on node `Rahul Sharma` to highlight connected 1-hop neighborhood.

---

## Stage 5: Grounded AI Assistant & Privacy Controls (2 Mins)
1. **Investigator AI Chat**: Click **"Phase 8: Investigator AI Assistant"**.
2. **Ask Question**: Submit sample prompt: *"Who did Inspector Vikram contact?"*.
3. **Inline Citation Verification**: Show natural language response with inline badges `[EVT-001]`. Click a badge to open **Provenance Inspector Modal**.
4. **Privacy Gateway Demonstration**: Point out `🔒 Pseudonymized Prompt` badge. Explain that real names (`Rahul Sharma`) are replaced with pseudonyms (`PERSON_001`) before prompting LLMs.
5. **No-Evidence Hard Fallback**: Ask unverified question: *"Tell me about Agent Zero"*. Show deterministic template fallback response without calling LLM.
6. **Privacy Audit Log**: Click **"Phase 9: Privacy Audit Log"** to show immutable audit trail of queries and pseudonymization checks.
