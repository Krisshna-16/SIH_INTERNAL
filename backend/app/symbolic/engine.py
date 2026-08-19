import json
import logging
import uuid
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


class SymbolicEngine:
    """
    100% Deterministic Rule Engine executing Symbolic AI reasoning over Evidence ground-truth.
    """

    def process_report(self, report_id: str, db: Session) -> Dict[str, Any]:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report '{report_id}' not found.")

        evidence_items = db.query(Evidence).filter(Evidence.report_id == report_id).all()
        
        if not evidence_items:
            logger.info(f"Report '{report_id}' has 0 evidence items. Skipping symbolic analysis.")
            # Clear existing relationships/findings for idempotency
            db.query(Relationship).filter(Relationship.report_id == report_id).delete()
            db.query(Finding).filter(Finding.report_id == report_id).delete()
            
            db.add(AuditLog(
                actor="system",
                action="SYMBOLIC_ANALYSIS_EXECUTED",
                report_id=report_id,
                details=json.dumps({"relationships_created": 0, "findings_created": 0}),
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

        # 3. Persist Relationships in High-Performance Batches
        rel_db_items = []
        rel_type_counts: Dict[str, int] = {}
        for r_dict in derived_rels:
            rel_id = f"REL-{uuid.uuid4().hex[:8].upper()}"
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

        # 4. Persist Findings
        fnd_db_items = []
        fnd_type_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        for f_dict in derived_findings:
            fnd_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
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
            # Batch save relationships
            batch_size = 1000
            for i in range(0, len(rel_db_items), batch_size):
                db.bulk_save_objects(rel_db_items[i:i + batch_size])

            # Save findings
            db.bulk_save_objects(fnd_db_items)

            # Audit log entry
            db.add(AuditLog(
                actor="system",
                action="SYMBOLIC_ANALYSIS_EXECUTED",
                report_id=report_id,
                details=json.dumps({
                    "total_relationships": len(rel_db_items),
                    "total_findings": len(fnd_db_items),
                }),
            ))

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
