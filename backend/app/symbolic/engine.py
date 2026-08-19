import json
import logging
import hashlib
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.models.audit_log import AuditLog

from app.symbolic.relationship_rules import rule_same_page_cooccurrence
from app.symbolic.finding_rules import (
    rule_page_cooccurrence_cluster,
    rule_high_frequency_location,
)

logger = logging.getLogger(__name__)


def generate_deterministic_rel_id(report_id: str, src_id: str, tgt_id: str, rel_type: str, rule_id: str) -> str:
    raw_key = f"{report_id}:{src_id}:{tgt_id}:{rel_type}:{rule_id}"
    sha_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:10].upper()
    return f"REL-{sha_hash}"


def generate_deterministic_fnd_id(report_id: str, fnd_type: str, rule_id: str, related_ev_ids: List[str]) -> str:
    sorted_ev = ",".join(sorted(related_ev_ids))
    raw_key = f"{report_id}:{fnd_type}:{rule_id}:{sorted_ev}"
    sha_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:10].upper()
    return f"FND-{sha_hash}"


class SymbolicEngine:
    """
    100% Deterministic Rule Engine executing Symbolic AI reasoning over Evidence ground-truth.
    Guarantees 100% idempotency across re-runs.
    """

    def process_report(self, report_id: str, db: Session) -> Dict[str, Any]:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report '{report_id}' not found.")

        evidence_items = db.query(Evidence).filter(Evidence.report_id == report_id).all()
        
        if not evidence_items:
            logger.info(f"Report '{report_id}' has 0 evidence items. Skipping symbolic analysis.")
            db.query(Relationship).filter(Relationship.report_id == report_id).delete()
            db.query(Finding).filter(Finding.report_id == report_id).delete()
            
            db.add(AuditLog(
                actor="system",
                action="SYMBOLIC_ANALYSIS_EXECUTED",
                report_id=report_id,
                details=json.dumps({"total_relationships": 0, "total_findings": 0}),
            ))
            db.commit()
            return {
                "report_id": report_id,
                "total_relationships": 0,
                "total_findings": 0,
                "relationship_types": {},
                "finding_types": {},
                "severities": {},
            }

        logger.info(f"Starting Symbolic AI analysis for report '{report_id}' ({len(evidence_items)} evidence items)...")

        # Delete existing relationships & findings for idempotency
        db.query(Relationship).filter(Relationship.report_id == report_id).delete()
        db.query(Finding).filter(Finding.report_id == report_id).delete()

        # 1. Execute Relationship Rules
        derived_rels: List[Dict[str, Any]] = []
        try:
            derived_rels.extend(rule_same_page_cooccurrence(evidence_items))
        except Exception as e:
            logger.error(f"Error executing rule_same_page_cooccurrence on report '{report_id}': {e}")

        # 2. Execute Finding Rules
        derived_findings: List[Dict[str, Any]] = []
        try:
            derived_findings.extend(rule_page_cooccurrence_cluster(evidence_items))
        except Exception as e:
            logger.error(f"Error executing rule_page_cooccurrence_cluster on report '{report_id}': {e}")

        try:
            derived_findings.extend(rule_high_frequency_location(evidence_items))
        except Exception as e:
            logger.error(f"Error executing rule_high_frequency_location on report '{report_id}': {e}")

        # 3. Persist Relationships with Deterministic Keys & Mandatory Check-Before-Insert Query
        rel_db_items = []
        rel_type_counts: Dict[str, int] = {}
        seen_rel_keys = set()

        for r_dict in derived_rels:
            rel_key = (r_dict["source_evidence_id"], r_dict["target_evidence_id"], r_dict["relationship_type"], r_dict["rule_id"])
            if rel_key in seen_rel_keys:
                continue
            seen_rel_keys.add(rel_key)

            # Mandatory Check-Before-Insert Database Query inside the loop for every Relationship row
            existing_rel = db.query(Relationship).filter(
                Relationship.report_id == report_id,
                Relationship.source_evidence_id == r_dict["source_evidence_id"],
                Relationship.target_evidence_id == r_dict["target_evidence_id"],
                Relationship.relationship_type == r_dict["relationship_type"],
                Relationship.rule_id == r_dict["rule_id"]
            ).first()
            if existing_rel:
                continue

            rel_id = generate_deterministic_rel_id(
                report_id, r_dict["source_evidence_id"], r_dict["target_evidence_id"], r_dict["relationship_type"], r_dict["rule_id"]
            )
            rel_db = Relationship(
                id=rel_id,
                report_id=report_id,
                source_evidence_id=r_dict["source_evidence_id"],
                target_evidence_id=r_dict["target_evidence_id"],
                relationship_type=r_dict["relationship_type"],
                classification=r_dict["classification"],
                rule_id=r_dict["rule_id"],
                explanation=r_dict["explanation"],
                confidence=r_dict["confidence"],
            )
            rel_db_items.append(rel_db)
            rel_type_counts[r_dict["relationship_type"]] = rel_type_counts.get(r_dict["relationship_type"], 0) + 1

        # 4. Persist Findings with Deterministic Keys & Mandatory Check-Before-Insert Query
        fnd_db_items = []
        fnd_type_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        seen_fnd_keys = set()

        for f_dict in derived_findings:
            fnd_key = (f_dict["finding_type"], f_dict["rule_id"], tuple(sorted(f_dict["related_evidence_ids"])))
            if fnd_key in seen_fnd_keys:
                continue
            seen_fnd_keys.add(fnd_key)

            # Mandatory Check-Before-Insert Database Query inside the loop for every Finding row
            existing_fnd = db.query(Finding).filter(
                Finding.report_id == report_id,
                Finding.finding_type == f_dict["finding_type"],
                Finding.rule_id == f_dict["rule_id"],
                Finding.related_evidence_ids == json.dumps(f_dict["related_evidence_ids"])
            ).first()
            if existing_fnd:
                continue

            fnd_id = generate_deterministic_fnd_id(
                report_id, f_dict["finding_type"], f_dict["rule_id"], f_dict["related_evidence_ids"]
            )
            fnd_db = Finding(
                id=fnd_id,
                report_id=report_id,
                finding_type=f_dict["finding_type"],
                classification=f_dict["classification"],
                rule_id=f_dict["rule_id"],
                rule_name=f_dict["rule_name"],
                explanation=f_dict["explanation"],
                related_evidence_ids=json.dumps(f_dict["related_evidence_ids"]),
                related_relationship_ids=json.dumps(f_dict.get("related_relationship_ids", [])),
                parameters_used=json.dumps(f_dict["parameters_used"]),
                severity=f_dict["severity"],
            )
            fnd_db_items.append(fnd_db)
            fnd_type_counts[f_dict["finding_type"]] = fnd_type_counts.get(f_dict["finding_type"], 0) + 1
            severity_counts[f_dict["severity"]] = severity_counts.get(f_dict["severity"], 0) + 1

        try:
            batch_size = 1000
            for i in range(0, len(rel_db_items), batch_size):
                db.bulk_save_objects(rel_db_items[i:i + batch_size])

            db.bulk_save_objects(fnd_db_items)

            db.add(AuditLog(
                actor="system",
                action="SYMBOLIC_ANALYSIS_EXECUTED",
                report_id=report_id,
                details=json.dumps({
                    "total_relationships": len(rel_db_items),
                    "total_findings": len(fnd_db_items),
                }),
            ))

            report.status = "analyzed"
            db.commit()
            logger.info(f"Symbolic analysis completed for '{report_id}': {len(rel_db_items)} relationships, {len(fnd_db_items)} findings persisted.")

            return {
                "report_id": report_id,
                "total_relationships": len(rel_db_items),
                "total_findings": len(fnd_db_items),
                "relationship_types": rel_type_counts,
                "finding_types": fnd_type_counts,
                "severities": severity_counts,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Symbolic analysis transaction failed for report '{report_id}': {e}")
            raise RuntimeError(f"Symbolic analysis transaction failed: {e}") from e
