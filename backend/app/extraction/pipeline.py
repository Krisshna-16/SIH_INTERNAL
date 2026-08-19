import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.report import Report, ReportPage
from app.models.entity import Entity
from app.extraction.base import BaseExtractor, ExtractedEntityDTO
from app.extraction.spacy_extractor import SpacyExtractor

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """
    Orchestrates report entity extraction across parsed pages, persisting results
    to database with full provenance enforcement.
    """

    def __init__(self, extractor: BaseExtractor = None):
        self.extractor = extractor or SpacyExtractor()

    def process_report(self, report_id: str, db: Session) -> Dict[str, Any]:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report '{report_id}' not found.")

        pages = db.query(ReportPage).filter(ReportPage.report_id == report_id).order_by(ReportPage.page_number).all()
        if not pages:
            raise ValueError(f"Report '{report_id}' has no parsed pages for extraction.")

        logger.info(f"Starting extraction pipeline for report '{report_id}' ({len(pages)} pages)...")

        # Clear any existing entities for this report to allow re-extraction idempotency
        db.query(Entity).filter(Entity.report_id == report_id).delete()

        total_extracted: List[ExtractedEntityDTO] = []
        page_errors = 0

        for page in pages:
            try:
                page_entities = self.extractor.extract(
                    page_text=page.text_content,
                    page_number=page.page_number,
                    report_id=report.filename or report_id,
                )
                total_extracted.extend(page_entities)
            except Exception as e:
                page_errors += 1
                logger.error(f"Unexpected error extracting entities from page {page.page_number} of report '{report_id}': {e}")
                # Continue processing remaining pages per requirement

        db_entities = []
        entity_counts: Dict[str, int] = {}

        for idx, dto in enumerate(total_extracted, start=1):
            # Enforce provenance traceability
            if dto.source_page is None or not dto.source_report:
                raise ValueError(f"Provenance missing for extracted entity '{dto.value}'")

            entity_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"
            db_entity = Entity(
                id=entity_id,
                report_id=report_id,
                type=dto.type,
                value=dto.value,
                normalized_value=dto.normalized_value,
                confidence=dto.confidence,
                source_page=dto.source_page,
                source_report=dto.source_report,
                extraction_method=dto.extraction_method,
            )
            db_entities.append(db_entity)

            entity_counts[dto.type] = entity_counts.get(dto.type, 0) + 1

        db.add_all(db_entities)
        report.status = "extracted"
        db.commit()

        logger.info(f"Extraction completed for report '{report_id}': {len(db_entities)} entities persisted across {len(pages)} pages.")

        return {
            "report_id": report_id,
            "filename": report.filename,
            "total_entities": len(db_entities),
            "entity_counts": entity_counts,
            "pages_processed": len(pages),
            "page_errors": page_errors,
        }
