import os
import sys
import json
import logging
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.session import Base
from app.models.user import User
from app.models.report import Report, ReportPage
from app.models.entity import Entity
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.models.audit_log import AuditLog
from app.models.pseudonym_mapping import PseudonymMapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_sqlite_to_postgres")


def parse_json_if_needed(val: Any) -> Any:
    """Helper to ensure Python objects (dicts/lists) are passed for JSON columns."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def migrate_data(sqlite_url: str = "sqlite:///./ufdr.db", target_pg_url: str = None):
    pg_url = target_pg_url or settings.DATABASE_URL
    if not pg_url.startswith("postgresql"):
        logger.error(f"Target DATABASE_URL '{pg_url}' is not a PostgreSQL connection string. Aborting migration.")
        return

    logger.info("=" * 80)
    logger.info("STARTING SQLITE TO POSTGRESQL DATA MIGRATION")
    logger.info(f"  Source SQLite: {sqlite_url}")
    logger.info(f"  Target Postgres: {pg_url}")
    logger.info("=" * 80)

    # 1. Connect Engines
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    pg_engine = create_engine(pg_url, pool_pre_ping=True)

    # 2. Ensure target tables exist
    Base.metadata.create_all(bind=pg_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    s_db = SqliteSession()
    p_db = PgSession()

    try:
        # Table 1: Users
        users = s_db.query(User).all()
        u_count = 0
        for u in users:
            existing = p_db.query(User).filter(User.username == u.username).first()
            if not existing:
                new_u = User(
                    id=u.id,
                    username=u.username,
                    hashed_password=u.hashed_password,
                    role=u.role,
                    created_at=u.created_at,
                )
                p_db.add(new_u)
                u_count += 1
        p_db.commit()
        logger.info(f"Migrated {u_count}/{len(users)} Users to Postgres.")

        # Table 2: Reports
        reports = s_db.query(Report).all()
        rep_count = 0
        for r in reports:
            existing = p_db.query(Report).filter(Report.id == r.id).first()
            if not existing:
                new_r = Report(
                    id=r.id,
                    filename=r.filename,
                    status=r.status,
                    page_count=r.page_count,
                    created_at=r.created_at,
                )
                p_db.add(new_r)
                rep_count += 1
        p_db.commit()
        logger.info(f"Migrated {rep_count}/{len(reports)} Reports to Postgres.")

        # Table 3: Report Pages
        pages = s_db.query(ReportPage).all()
        p_count = 0
        for p in pages:
            existing = p_db.query(ReportPage).filter(ReportPage.id == p.id).first()
            if not existing:
                new_p = ReportPage(
                    id=p.id,
                    report_id=p.report_id,
                    page_number=p.page_number,
                    text_content=p.text_content,
                    tables_json=parse_json_if_needed(p.tables_json),
                )
                p_db.add(new_p)
                p_count += 1
        p_db.commit()
        logger.info(f"Migrated {p_count}/{len(pages)} ReportPages to Postgres.")

        # Table 4: Entities
        entities = s_db.query(Entity).all()
        ent_count = 0
        for e in entities:
            existing = p_db.query(Entity).filter(Entity.id == e.id).first()
            if not existing:
                new_e = Entity(
                    id=e.id,
                    report_id=e.report_id,
                    type=e.type,
                    value=e.value,
                    normalized_value=e.normalized_value,
                    confidence=e.confidence,
                    source_page=e.source_page,
                    source_report=e.source_report,
                    extraction_method=e.extraction_method,
                    created_at=e.created_at,
                )
                p_db.add(new_e)
                ent_count += 1
        p_db.commit()
        logger.info(f"Migrated {ent_count}/{len(entities)} Entities to Postgres.")

        # Table 5: Evidence
        evidence_items = s_db.query(Evidence).all()
        ev_count = 0
        for ev in evidence_items:
            existing = p_db.query(Evidence).filter(Evidence.evidence_id == ev.evidence_id).first()
            if not existing:
                new_ev = Evidence(
                    evidence_id=ev.evidence_id,
                    report_id=ev.report_id,
                    evidence_type=ev.evidence_type,
                    value=ev.value,
                    normalized_value=ev.normalized_value,
                    timestamp=ev.timestamp,
                    confidence=ev.confidence,
                    source_page=ev.source_page,
                    source_report=ev.source_report,
                    provenance_detail=parse_json_if_needed(ev.provenance_detail),
                    derived_from_entity_id=ev.derived_from_entity_id,
                    created_at=ev.created_at,
                )
                p_db.add(new_ev)
                ev_count += 1
        p_db.commit()
        logger.info(f"Migrated {ev_count}/{len(evidence_items)} Evidence records to Postgres.")

        # Table 6: Relationships
        relationships = s_db.query(Relationship).all()
        rel_count = 0
        for rel in relationships:
            existing = p_db.query(Relationship).filter(Relationship.id == rel.id).first()
            if not existing:
                new_rel = Relationship(
                    id=rel.id,
                    report_id=rel.report_id,
                    source_evidence_id=rel.source_evidence_id,
                    target_evidence_id=rel.target_evidence_id,
                    relationship_type=rel.relationship_type,
                    classification=rel.classification,
                    rule_id=rel.rule_id,
                    explanation=rel.explanation,
                    confidence=rel.confidence,
                    created_at=rel.created_at,
                )
                p_db.add(new_rel)
                rel_count += 1
        p_db.commit()
        logger.info(f"Migrated {rel_count}/{len(relationships)} Relationships to Postgres.")

        # Table 7: Findings
        findings = s_db.query(Finding).all()
        fnd_count = 0
        for f in findings:
            existing = p_db.query(Finding).filter(Finding.id == f.id).first()
            if not existing:
                new_f = Finding(
                    id=f.id,
                    report_id=f.report_id,
                    finding_type=f.finding_type,
                    classification=f.classification,
                    rule_id=f.rule_id,
                    rule_name=f.rule_name,
                    explanation=f.explanation,
                    related_evidence_ids=parse_json_if_needed(f.related_evidence_ids),
                    related_relationship_ids=parse_json_if_needed(f.related_relationship_ids),
                    parameters_used=parse_json_if_needed(f.parameters_used),
                    severity=f.severity,
                    created_at=f.created_at,
                )
                p_db.add(new_f)
                fnd_count += 1
        p_db.commit()
        logger.info(f"Migrated {fnd_count}/{len(findings)} Findings to Postgres.")

        # Table 8: Audit Logs
        audits = s_db.query(AuditLog).all()
        a_count = 0
        for a in audits:
            existing = p_db.query(AuditLog).filter(AuditLog.id == a.id).first()
            if not existing:
                new_a = AuditLog(
                    id=a.id,
                    actor=a.actor,
                    action=a.action,
                    evidence_id=a.evidence_id,
                    report_id=a.report_id,
                    details=parse_json_if_needed(a.details),
                    timestamp=a.timestamp,
                )
                p_db.add(new_a)
                a_count += 1
        p_db.commit()
        logger.info(f"Migrated {a_count}/{len(audits)} Audit Logs to Postgres.")

        # Table 9: Pseudonym Mappings
        mappings = s_db.query(PseudonymMapping).all()
        m_count = 0
        for m in mappings:
            existing = p_db.query(PseudonymMapping).filter(PseudonymMapping.id == m.id).first()
            if not existing:
                new_m = PseudonymMapping(
                    id=m.id,
                    report_id=m.report_id,
                    real_value=m.real_value,
                    pseudonym=m.pseudonym,
                    entity_type=m.entity_type,
                    first_seen_evidence_id=m.first_seen_evidence_id,
                    created_at=m.created_at,
                )
                p_db.add(new_m)
                m_count += 1
        p_db.commit()
        logger.info(f"Migrated {m_count}/{len(mappings)} Pseudonym Mappings to Postgres.")

        logger.info("=" * 80)
        logger.info("DATA MIGRATION TO POSTGRESQL COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

    except Exception as e:
        p_db.rollback()
        logger.error(f"Data migration failed: {e}")
        raise
    finally:
        s_db.close()
        p_db.close()


if __name__ == "__main__":
    migrate_data()
