# UFDR Analysis Platform - System Architecture & Roadmap

## Core Principles
1. **Evidence-Grounded & Explainable**: Every insight, entity, or event extracted must trace back directly to specific source items within the UFDR extraction (chats, call logs, media metadata, system logs) with cryptographic/byte-level provenance.
2. **Privacy-First & Air-Gapped**: Sensitive forensic data and investigation intelligence must remain strictly local. No external API calls, tracking, or cloud telemetry.
3. **Modular Architecture**: Components are strictly decoupled via interfaces so backends (e.g., SQLite → PostgreSQL, NetworkX → Neo4j / Memgraph) and models (e.g., local LLM backends) can be swapped seamlessly without breaking dependent layers.

---

## High-Level Data & Processing Pipeline

```
+-----------------------------------------------------------------------------------+
|                            UFDR Ingestion Layer                                   |
|       (ZIP / XML / SQLite / JSON / Media Extractions from Cellebrite UFDR)       |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                             Neural AI Engine                                      |
|    (NER, Event Extraction, Multimodal Processing, Relationship Parsing)           |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                       Evidence Database (with Provenance)                         |
|     (Structured SQL + Vector Embeddings + Provenance Pointers & Hash Checks)      |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                        Symbolic AI & Knowledge Graph                              |
|     (Rule Engine, Network Topology, Co-occurrence Analysis, Graph Queries)        |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                   Timeline & Cross-Artifact Correlation Engine                    |
|      (Temporal Clustering, Geo-Spatial Mapping, Multi-Device Linkage)             |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                         Privacy & Governance Gateway                              |
|       (Redaction Filters, Role-Based Access Control, Audit Log Signing)           |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                        Local LLM & Reasoning Engine                               |
|        (Air-gapped Quantized LLM, RAG over Evidence DB, Structured Answers)       |
+--------------------------------------------------+--------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------+
|                   Investigator Natural Language UI / Workspace                    |
|      (Interactive Timeline, Graph Explorer, Query Chat, Report Generator)         |
+-----------------------------------------------------------------------------------+
```

---

## Project Phase Roadmap

- **Phase 0: Project Foundation (Current Phase)**
  - Clean monorepo structure with strict separation of backend (FastAPI) and frontend (Vite/React/TS).
  - Pydantic settings management, structured logging, SQLAlchemy plumbing, CORS config, health check endpoint, and frontend status integration.

- **Phase 1: Ingestion Engine & Schema Standardization**
  - Parsing of raw UFDR extractions (ZIP archives, XML reports, SQLite databases, JSON exports).
  - Normalization into a unified forensic evidence schema (Contacts, Calls, Messages, Media, Location Data, Apps, Web History).

- **Phase 2: Neural AI & Multimodal Entity Extraction**
  - Local NER models for extracting PII, phone numbers, crypto addresses, names, locations, financial identifiers.
  - Computer Vision / OCR pipeline for image text extraction and media classification.

- **Phase 3: Evidence Database & Provenance Tracking**
  - Persistent storage schema (SQLAlchemy + Vector Store) with hash verification and exact line/file provenance tracking for courtroom admissibility.

- **Phase 4: Symbolic AI & Knowledge Graph Construction**
  - Graph representation of entities, communications, and co-occurrences.
  - Rule-based reasoning engine for fraud patterns, suspicious temporal clusters, and risk scoring.

- **Phase 5: Timeline & Cross-Artifact Correlation**
  - Unified interactive timeline generation and geo-spatial mapping across multiple extracted devices.

- **Phase 6: Privacy Gateway & Local LLM Natural Language Interface**
  - Local air-gapped LLM integration (via Ollama / llama.cpp) with strict retrieval-augmented generation (RAG) tied exclusively to Evidence DB contexts.

- **Phase 7: Investigator Workspace & Visualization**
  - High-performance UI dashboard: interactive network graph explorer, multi-filter timeline slider, NL query interface, and court-ready PDF/HTML report exporter.

- **Phase 8: Security Hardening & Audit Compliance**
  - Role-based access control (RBAC), immutable audit logging, memory-safe data wiping, and government security compliance validation.
