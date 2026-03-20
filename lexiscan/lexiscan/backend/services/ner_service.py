"""
LexiScan — Named Entity Recognition Service
Extracts parties, dates, monetary values, obligations, and jurisdictions
from contract text using spaCy + rule-based patterns.
"""

import re
from typing import Dict, List, Optional, Tuple

from loguru import logger


# ── Entity Types ─────────────────────────────────────────────

ENTITY_TYPES = {
    "PARTY": "Contracting party (company/person)",
    "DATE": "Date or time reference",
    "MONEY": "Monetary value or amount",
    "ORG": "Organization mentioned",
    "GPE": "Geopolitical entity (country/state/city)",
    "LAW": "Law, regulation, or legal document",
    "OBLIGATION": "Obligation or duty",
    "JURISDICTION": "Legal jurisdiction",
    "DURATION": "Time period or duration",
    "PERCENT": "Percentage value",
}


class NERService:
    """Named entity recognition for legal contracts."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp = None
        self._loaded = False

    def _load(self):
        """Lazy-load spaCy model."""
        if self._loaded:
            return
        try:
            import spacy
            self._nlp = spacy.load(self.model_name)
            self._nlp.max_length = 2_000_000
            self._loaded = True
            logger.info(f"spaCy model '{self.model_name}' loaded")
        except OSError:
            logger.warning(f"spaCy model '{self.model_name}' not found — using rule-based fallback")
            self._nlp = None
            self._loaded = True

    def extract_entities(self, text: str, clause_index: Optional[int] = None) -> List[Dict]:
        """
        Extract named entities from text.
        Returns list of entity dicts.
        """
        self._load()
        entities = []

        # spaCy-based extraction
        if self._nlp:
            entities.extend(self._spacy_extract(text, clause_index))

        # Rule-based extraction (supplements or replaces spaCy)
        entities.extend(self._rule_based_extract(text, clause_index))

        # Deduplicate
        entities = self._deduplicate(entities)

        return entities

    def extract_parties(self, full_text: str) -> List[str]:
        """
        Identify parties from the first section of the contract
        (recitals/preamble typically name the parties).
        """
        # Check first 2000 chars
        preamble = full_text[:2000]
        parties = []

        # Pattern: "Company Name, a [state] [corporation/LLC/Inc]"
        corp_pattern = re.compile(
            r'([A-Z][A-Za-z\s,\.]+(?:Inc\.?|LLC|Corp\.?|Ltd\.?|Limited|GmbH|S\.A\.|BV|PLC))',
            re.MULTILINE
        )
        for m in corp_pattern.finditer(preamble):
            name = m.group(1).strip().rstrip(",")
            if 3 < len(name) < 100:
                parties.append(name)

        # Pattern: "referred to as 'X'" or "hereinafter 'X'"
        referred_pattern = re.compile(
            r'(?:referred to as|hereinafter|herein called)\s+["\']([^"\']{2,50})["\']',
            re.IGNORECASE
        )
        for m in referred_pattern.finditer(preamble):
            parties.append(m.group(1).strip())

        # Deduplicate preserving order
        seen = set()
        unique_parties = []
        for p in parties:
            if p not in seen:
                seen.add(p)
                unique_parties.append(p)

        return unique_parties[:10]  # cap at 10

    def _spacy_extract(self, text: str, clause_index: Optional[int]) -> List[Dict]:
        """spaCy NER extraction."""
        entities = []
        # Limit text length for performance
        doc = self._nlp(text[:10000])

        label_map = {
            "ORG": "ORG",
            "PERSON": "PARTY",
            "DATE": "DATE",
            "MONEY": "MONEY",
            "GPE": "GPE",
            "LAW": "LAW",
            "PERCENT": "PERCENT",
            "TIME": "DURATION",
        }

        for ent in doc.ents:
            mapped = label_map.get(ent.label_)
            if not mapped:
                continue
            entities.append({
                "entity_type": mapped,
                "text": ent.text.strip(),
                "normalized": _normalize_entity(ent.text, mapped),
                "clause_index": clause_index,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
                "confidence": 0.85,
            })

        return entities

    def _rule_based_extract(self, text: str, clause_index: Optional[int]) -> List[Dict]:
        """Rule-based extraction for legal-specific patterns."""
        entities = []

        # Dates: "January 1, 2024", "01/01/2024", "2024-01-01"
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
        ]
        for pat in date_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                entities.append({
                    "entity_type": "DATE",
                    "text": m.group(0),
                    "normalized": m.group(0),
                    "clause_index": clause_index,
                    "start_char": m.start(),
                    "end_char": m.end(),
                    "confidence": 0.95,
                })

        # Money: "$1,000,000", "USD 500,000", "1.5 million dollars"
        money_patterns = [
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?',
            r'USD\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand))?',
            r'[\d,]+(?:\.\d+)?\s*(?:dollars?|USD)',
        ]
        for pat in money_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                entities.append({
                    "entity_type": "MONEY",
                    "text": m.group(0),
                    "normalized": m.group(0),
                    "clause_index": clause_index,
                    "start_char": m.start(),
                    "end_char": m.end(),
                    "confidence": 0.92,
                })

        # Obligations: "shall", "must", "agrees to", "is required to"
        obligation_pattern = re.compile(
            r'(?:(?:shall|must|agrees? to|is required to|undertakes? to|covenants? to)\s+)([^.]{10,100})',
            re.IGNORECASE
        )
        for m in obligation_pattern.finditer(text):
            obligation_text = m.group(0)[:150]
            entities.append({
                "entity_type": "OBLIGATION",
                "text": obligation_text,
                "normalized": obligation_text.lower(),
                "clause_index": clause_index,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 0.75,
            })

        # Jurisdictions: "State of California", "laws of Delaware"
        juris_pattern = re.compile(
            r'(?:State of|laws of|jurisdiction of|courts of)\s+([A-Z][a-zA-Z\s]+)',
            re.IGNORECASE
        )
        for m in juris_pattern.finditer(text):
            entities.append({
                "entity_type": "JURISDICTION",
                "text": m.group(0),
                "normalized": m.group(1).strip(),
                "clause_index": clause_index,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 0.88,
            })

        # Duration: "30 days", "12 months", "3 years"
        duration_pattern = re.compile(
            r'\b(\d+)\s*(business\s+)?(days?|weeks?|months?|years?)\b',
            re.IGNORECASE
        )
        for m in duration_pattern.finditer(text):
            entities.append({
                "entity_type": "DURATION",
                "text": m.group(0),
                "normalized": m.group(0).lower(),
                "clause_index": clause_index,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 0.90,
            })

        # Percentages
        pct_pattern = re.compile(r'\b\d+(?:\.\d+)?%')
        for m in pct_pattern.finditer(text):
            entities.append({
                "entity_type": "PERCENT",
                "text": m.group(0),
                "normalized": m.group(0),
                "clause_index": clause_index,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 0.95,
            })

        return entities

    def _deduplicate(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities (same type + text)."""
        seen = set()
        unique = []
        for e in entities:
            key = (e["entity_type"], e["text"].lower()[:50])
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique


def _normalize_entity(text: str, entity_type: str) -> str:
    """Basic normalization for entities."""
    text = text.strip()
    if entity_type == "DATE":
        return text  # Could parse to ISO date
    if entity_type == "MONEY":
        return re.sub(r"[,$]", "", text).strip()
    return text


# Singleton
_ner_service: Optional[NERService] = None


def get_ner_service() -> NERService:
    global _ner_service
    if _ner_service is None:
        _ner_service = NERService()
    return _ner_service
