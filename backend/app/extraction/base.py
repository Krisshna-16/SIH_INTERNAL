from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ExtractedEntityDTO:
    """Data Transfer Object representing an extracted entity prior to database storage."""
    type: str
    value: str
    normalized_value: Optional[str]
    confidence: float
    source_page: int
    source_report: str
    extraction_method: str


class BaseExtractor(ABC):
    """Abstract interface for entity extraction engines."""

    @abstractmethod
    def extract(self, page_text: str, page_number: int, report_id: str) -> List[ExtractedEntityDTO]:
        """
        Extracts structured entities from a single text page.
        
        :param page_text: Raw text of the parsed report page
        :param page_number: Provenance page index (1-based)
        :param report_id: Provenance report identifier/filename
        :return: List of ExtractedEntityDTO objects
        """
        pass
