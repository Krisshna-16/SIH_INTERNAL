import os
import sys
import sqlite3

# Ensure python path includes backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import engine, SessionLocal
from app.models.report import Report
from app.models.entity import Entity
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.extraction.pipeline import ExtractionPipeline
from app.evidence.consolidator import consolidate_report_evidence
from app.symbolic.engine import SymbolicEngine


def deduplicate_database():
    db = SessionLocal()
    try:
        reports = db.query(Report).all()
        print("\n" + "=" * 80)
        print("DATABASE DEDUPLICATION & CLEANUP MIGRATION")
        print("=" * 80)

        for rep in reports:
            report_id = rep.id
            print(f"\nProcessing Report ID: '{report_id}'")

            # 1. Before Counts
            ent_before = db.query(Entity).filter(Entity.report_id == report_id).count()
            ev_before = db.query(Evidence).filter(Evidence.report_id == report_id).count()
            rel_before = db.query(Relationship).filter(Relationship.report_id == report_id).count()
            fnd_before = db.query(Finding).filter(Finding.report_id == report_id).count()

            print(f"  BEFORE CLEANUP -> Entities: {ent_before} | Evidence: {ev_before} | Relationships: {rel_before} | Findings: {fnd_before}")

            # 2. Re-run Extraction, Consolidation, and Symbolic Analysis cleanly
            # Extraction
            ext_pipeline = ExtractionPipeline()
            ext_res = ext_pipeline.process_report(report_id, db)

            # Evidence Consolidation
            cons_res = consolidate_report_evidence(report_id, db)

            # Symbolic AI Engine Analysis
            sym_engine = SymbolicEngine()
            sym_res = sym_engine.process_report(report_id, db)

            # 3. After Counts
            ent_after = db.query(Entity).filter(Entity.report_id == report_id).count()
            ev_after = db.query(Evidence).filter(Evidence.report_id == report_id).count()
            rel_after = db.query(Relationship).filter(Relationship.report_id == report_id).count()
            fnd_after = db.query(Finding).filter(Finding.report_id == report_id).count()

            print(f"  AFTER CLEANUP  -> Entities: {ent_after} | Evidence: {ev_after} | Relationships: {rel_after} | Findings: {fnd_after}")

        print("\n" + "=" * 80)
        print("DATABASE DEDUPLICATION COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    deduplicate_database()
