import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, Base, engine
from app.models.report import Report, ReportPage
from app.extraction.pipeline import ExtractionPipeline
from app.evidence.consolidator import consolidate_report_evidence
from app.symbolic.engine import SymbolicEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_data")

DEMO_REPORT_ID = "REP-MHA-DEMO-2024"
DEMO_FILENAME = "UFDR_Case_MHA_2024_DEMO.xml"

SYNTHETIC_PAGES = [
    {
        "page_number": 1,
        "text_content": (
            "FORENSIC EXTRACTION REPORT - CASE MHA-2024-08.\n"
            "Target Device: Samsung Galaxy S23 (IMEI: 864209041234567).\n"
            "Primary Subject: Inspector Vikram Malhotra (+91 9876543210, vikram.m@forensics.gov.in).\n"
            "Key Associate: Rahul Sharma (+91 9123456789, rahul.s@techcorp.in).\n"
            "Initial contact recorded on 12 March 2024 at 10:15 AM near Connaught Place, New Delhi."
        ),
    },
    {
        "page_number": 2,
        "text_content": (
            "WHATSAPP CHAT EXPORT & CALL LOGS:\n"
            "12 March 2024 10:30 AM - Call from Inspector Vikram Malhotra (+91 9876543210) to Rahul Sharma (+91 9123456789). Duration: 240s.\n"
            "12 March 2024 10:35 AM - Message: 'Meeting confirmed at Cyber Hub Gurgaon. Bring files.'\n"
            "12 March 2024 10:36 AM - Message from Rahul Sharma (+91 9123456789): 'Understood, forwarding details to Ankit Verma (+91 9988776655).'\n"
            "12 March 2024 10:38 AM - Message: 'Check document portal http://evidence-portal.gov.in.'\n"
            "12 March 2024 10:40 AM - Call from Rahul Sharma (+91 9123456789) to Inspector Vikram Malhotra (+91 9876543210). Duration: 180s."
        ),
    },
    {
        "page_number": 3,
        "text_content": (
            "NETWORK & SYSTEM LOGS:\n"
            "IP Address 192.168.1.50 accessed portal http://evidence-portal.gov.in at 10:42 AM.\n"
            "Email sent to Priya Patel (priya.p@mha-demo.gov.in) from vikram.m@forensics.gov.in regarding Bengaluru operations.\n"
            "Secondary contact Suresh Nair (+91 9811223344) logged at Mumbai terminal."
        ),
    },
]


def seed_demo_data():
    """
    Seeds rich synthetic demo report and runs full extraction + consolidation + symbolic rules.
    100% FICTIONAL SYNTHETIC DATA FOR HACKATHON DEMONSTRATION ONLY.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Report).filter(Report.id == DEMO_REPORT_ID).first()
        if existing:
            logger.info(f"Demo report '{DEMO_REPORT_ID}' already exists in database.")
            return

        demo_report = Report(
            id=DEMO_REPORT_ID,
            filename=DEMO_FILENAME,
            status="ingested",
            page_count=len(SYNTHETIC_PAGES),
        )
        db.add(demo_report)
        db.flush()

        for page in SYNTHETIC_PAGES:
            r_page = ReportPage(
                report_id=DEMO_REPORT_ID,
                page_number=page["page_number"],
                text_content=page["text_content"],
            )
            db.add(r_page)

        db.commit()
        logger.info(f"Ingested synthetic demo report '{DEMO_REPORT_ID}' with {len(SYNTHETIC_PAGES)} pages.")

        # 1. Neural Extraction (Phase 2)
        pipeline = ExtractionPipeline()
        ext_res = pipeline.process_report(report_id=DEMO_REPORT_ID, db=db)
        logger.info(f"Extracted {ext_res['total_entities']} neural entities.")

        # 2. Evidence Consolidation (Phase 3)
        cons_res = consolidate_report_evidence(report_id=DEMO_REPORT_ID, db=db)
        logger.info(f"Consolidated {cons_res['total_evidence']} evidence records.")

        # 3. Symbolic Analysis Rules (Phase 4)
        sym_engine = SymbolicEngine()
        sym_res = sym_engine.process_report(report_id=DEMO_REPORT_ID, db=db)
        logger.info(f"Symbolic Engine generated {sym_res['total_relationships']} relationships and {sym_res['total_findings']} findings.")

        logger.info("Successfully seeded complete synthetic demo dataset.")
    except Exception as e:
        logger.error(f"Failed to seed demo dataset: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
