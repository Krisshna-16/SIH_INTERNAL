# UFDR Analysis Platform — Architecture Summary & Design Principles

**Project**: Ministry of Home Affairs (India) AI-Based UFDR Forensic Analysis Tool  
**Target Deployment**: On-Premise Government Infrastructure  

---

## 1. Core Architectural Vision
The UFDR Analysis Platform converts heterogeneous Universal Forensic Extraction Reports (UFDR XML/JSON) into explainable, auditable intelligence. 

The system operates on a fundamental principle:
> **The LLM is a communication layer, NEVER the source of truth.**
> All facts, relationships, and findings are established by local neural extraction and deterministic symbolic rules *before* natural language synthesis.

```
[ UFDR Report ] ──> [ 1. Neural Extraction (spaCy) ] ──> [ 2. Evidence Consolidation ]
                                                                   │
[ Grounded UI ] <── [ 5. Privacy Gateway (Pseudonyms) ] <── [ 3. Symbolic Engine (Rules) ]
        │                                                          │
        └─── [ 6. Local LLM (Ollama) + Citation Verifier ] <───────┴──> [ 4. Timeline & Graph ]
```

---

## 2. Three Distinct AI Components
1. **Neural Extraction Layer (spaCy NLP)**: Local Named Entity Recognition parsing persons, phone numbers, emails, locations, IPs, and dates with character-offset provenance.
2. **Symbolic AI Rule Engine**: Deterministic Python rule engine establishing `FACT` vs `INFERENCE` relationship triplets and flagging anomaly patterns (communication bursts, location overlaps) without LLM hallucinations.
3. **Communication Layer (Local Ollama LLM)**: Grounded natural-language answer generator operating strictly downstream of pre-retrieved evidence, featuring post-hoc regex citation verification and deterministic no-evidence fallbacks.

---

## 3. Privacy Gateway & Security Architecture
- **Local-by-Default Execution**: 100% of forensic parsing, evidence storage, rule evaluation, and local LLM inference occurs on-premise without cloud connectivity.
- **Identity Pseudonymization**: Real identities (`Rahul Sharma` -> `PERSON_001`, `+91 9876543210` -> `PHONE_001`) are mapped per report before prompt construction. Pseudonyms are reversed ONLY in the authenticated investigator's browser interface.
- **Gated External AI Access**: External LLM dispatch is OFF by default, requires per-query opt-in, sends minimized pseudonymized payloads, and is fully audit-logged.

---

## 4. Known Limitations & Future Work
1. **Multi-Report Cross Analysis**: Current MVP focuses on single-report analysis; cross-case entity resolution across multiple devices is planned for Phase 12.
2. **Advanced Graph DB**: Network graph rendering currently utilizes NetworkX in-memory graphs; migration to Neo4j/Memgraph is planned for enterprise multi-terabyte scale.
3. **Role-Based Access Control (RBAC)**: Current authentication supports single `INVESTIGATOR` role; multi-tier permission matrix (Investigator, Supervisor, Auditor) is structured in schema for future deployment.
4. **Multilingual OCR Support**: Direct processing of regional Indian language extractions via IndicNLP.
