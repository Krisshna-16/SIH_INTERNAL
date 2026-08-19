import logging
from typing import List, Dict
from app.extraction.base import BaseExtractor, ExtractedEntityDTO
from app.extraction.pattern_rules import extract_regex_patterns

logger = logging.getLogger(__name__)

# Map spaCy NER labels to unified platform EntityType
SPACY_LABEL_MAP = {
    "PERSON": "PERSON",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "DATE": "DATE",
    "TIME": "DATE",
    "ORG": "ORG",
    "FAC": "LOCATION",
    "NORP": "OTHER",
    "PRODUCT": "OTHER",
    "EVENT": "OTHER",
}


class SpacyExtractor(BaseExtractor):
    """
    Local NLP & Pattern entity extractor combining spaCy NER with deterministic regex rules.
    
    EXPLAINABLE CONFIDENCE SCORING:
    - Regex pattern matches (phones, emails, URLs, IPs) receive high confidence (0.95 - 0.98)
      because they are based on deterministic syntax patterns.
    - spaCy statistical NER matches (PERSON, LOCATION, DATE, ORG) receive heuristic confidence (0.75)
      reflecting standard small-model statistical precision.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.nlp = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            import spacy
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Successfully loaded spaCy model '{self.model_name}'")
        except (ImportError, OSError) as e:
            error_msg = (
                f"Failed to load spaCy model '{self.model_name}'. "
                f"Please ensure spaCy is installed and run 'python -m spacy download {self.model_name}'."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg) from e

    def extract(self, page_text: str, page_number: int, report_id: str) -> List[ExtractedEntityDTO]:
        if not page_text or not page_text.strip():
            return []

        extracted_entities: List[ExtractedEntityDTO] = []
        seen_keys = set()

        # 1. Deterministic Regex Pattern Extraction (Phone, Email, URL, IP)
        regex_matches = extract_regex_patterns(page_text)
        for ent_type, raw_val, norm_val, conf, method in regex_matches:
            key = (ent_type, raw_val.lower(), page_number)
            if key not in seen_keys:
                seen_keys.add(key)
                extracted_entities.append(
                    ExtractedEntityDTO(
                        type=ent_type,
                        value=raw_val,
                        normalized_value=norm_val,
                        confidence=conf,
                        source_page=page_number,
                        source_report=report_id,
                        extraction_method=method,
                    )
                )

        # 2. spaCy Statistical NER Extraction
        doc = self.nlp(page_text)
        for ent in doc.ents:
            mapped_type = SPACY_LABEL_MAP.get(ent.label_, None)
            if not mapped_type:
                continue

            raw_val = ent.text.strip()
            if not raw_val or len(raw_val) < 2:
                continue

            # Avoid duplicating regex extracted phones/emails/URLs
            key = (mapped_type, raw_val.lower(), page_number)
            if key not in seen_keys:
                seen_keys.add(key)
                extracted_entities.append(
                    ExtractedEntityDTO(
                        type=mapped_type,
                        value=raw_val,
                        normalized_value=raw_val,
                        confidence=0.75,  # Heuristic confidence score for spaCy NER
                        source_page=page_number,
                        source_report=report_id,
                        extraction_method="spacy_ner",
                    )
                )

        return extracted_entities
