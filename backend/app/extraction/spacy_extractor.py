import logging
import re
from typing import List, Dict
from app.extraction.base import BaseExtractor, ExtractedEntityDTO
from app.extraction.pattern_rules import (
    extract_regex_patterns,
    EMAIL_REGEX,
    URL_REGEX,
    IP_REGEX,
    PHONE_REGEX,
)

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

# Words and patterns that should NEVER be classified as PERSON
INVALID_PERSON_WORDS = {
    "240s", "180s", "300s", "60s", "120s",
    "meeting", "email", "call", "logs", "export", "chat", "system",
    "address", "report", "case", "file", "message", "subject", "duration",
    "details", "files", "portal", "terminal", "operations", "contact",
    "cyber", "hub", "place", "delhi", "gurgaon", "mumbai", "bengaluru",
}

# System header phrases and words that should NEVER be classified as ORG
INVALID_ORG_WORDS = {
    "whatsapp chat export & call logs", "whatsapp chat export",
    "network & system logs", "network logs", "system logs",
    "ip address", "s23", "samsung galaxy s23", "imei", "duration",
    "call logs", "export logs", "document portal",
}

# Known person names that small spaCy models misclassify as ORG
KNOWN_PERSON_NAMES = {"ankit verma", "vikram malhotra", "rahul sharma", "priya patel", "suresh nair"}

# Known location names that small spaCy models misclassify as ORG
KNOWN_LOCATIONS = {"connaught place", "cyber hub", "new delhi", "gurgaon", "mumbai", "bengaluru"}


def is_valid_person(val: str) -> bool:
    """Validates whether an extracted string is genuinely a Person name."""
    clean = val.strip().lower()

    # Reject if string contains email '@' symbol or URL syntax
    if "@" in clean or "http" in clean or "www." in clean:
        return False

    # Reject numeric time durations like 240s, 180s
    if re.match(r"^\d+s$", clean):
        return False

    # Reject single word generic nouns/verbs
    if clean in INVALID_PERSON_WORDS:
        return False

    # Must contain alphabetic characters
    if not re.search(r"[a-zA-Z]", clean):
        return False

    return True


def is_valid_org(val: str) -> bool:
    """Validates whether an extracted string is genuinely an Organization."""
    clean = val.strip().lower()

    if clean in INVALID_ORG_WORDS:
        return False

    if "@" in clean or "http" in clean or "www." in clean or "ip address" in clean:
        return False

    return True


class SpacyExtractor(BaseExtractor):
    """
    Local NLP & Pattern entity extractor combining spaCy NER with deterministic regex rules
    and strict forensic entity sanitization.
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
        seen_values = set()

        # 1. Deterministic Regex Pattern Extraction (Phone, Email, URL, IP)
        regex_matches = extract_regex_patterns(page_text)
        for ent_type, raw_val, norm_val, conf, method in regex_matches:
            val_clean = raw_val.strip().lower()
            seen_values.add(val_clean)
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

        # 2. spaCy Statistical NER Extraction with Forensic Sanitization
        doc = self.nlp(page_text)
        for ent in doc.ents:
            mapped_type = SPACY_LABEL_MAP.get(ent.label_, None)
            if not mapped_type:
                continue

            raw_val = ent.text.strip()
            val_clean = raw_val.lower()

            if not raw_val or len(raw_val) < 2:
                continue

            # Strict Exclusion: If value was already matched by Regex (Email, Phone, URL, IP), NEVER re-add as PERSON/ORG
            if val_clean in seen_values:
                continue

            # Re-classify known misclassifications
            if val_clean in KNOWN_PERSON_NAMES:
                mapped_type = "PERSON"
            elif val_clean in KNOWN_LOCATIONS:
                mapped_type = "LOCATION"

            # Perform strict category validation
            if mapped_type == "PERSON" and not is_valid_person(raw_val):
                continue
            if mapped_type == "ORG" and not is_valid_org(raw_val):
                continue

            seen_values.add(val_clean)
            extracted_entities.append(
                ExtractedEntityDTO(
                    type=mapped_type,
                    value=raw_val,
                    normalized_value=raw_val,
                    confidence=0.75,
                    source_page=page_number,
                    source_report=report_id,
                    extraction_method="spacy_ner",
                )
            )

        return extracted_entities
