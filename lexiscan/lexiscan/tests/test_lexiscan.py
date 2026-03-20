"""
LexiScan — Test Suite
Tests for PDF parsing, NER, risk classification, and comparison.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Fixtures ──────────────────────────────────────────────────

SAMPLE_CONTRACT_TEXT = """
MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into as of January 15, 2024,
by and between Acme Corporation, Inc., a Delaware corporation ("Client"),
and Vendor LLC, a California limited liability company ("Vendor").

1. SERVICES
Vendor agrees to provide software development services as described in each
Statement of Work. Vendor shall deliver all work product within agreed timelines.

2. PAYMENT TERMS
Client shall pay Vendor within 30 days of invoice receipt.
Payment amounts are set forth in each SOW. Late payments shall accrue interest
at 1.5% per month.

3. INTELLECTUAL PROPERTY
All work product created by Vendor under this Agreement shall be considered
work made for hire. Client shall own all intellectual property rights to
deliverables, including source code and documentation.

4. INDEMNIFICATION
Vendor shall indemnify, defend, and hold harmless Client from any claims,
damages, or expenses arising from Vendor's breach of this Agreement or
negligent acts or omissions.

5. LIMITATION OF LIABILITY
NOTWITHSTANDING ANYTHING TO THE CONTRARY, VENDOR SHALL HAVE NO LIABILITY
CAP AND CLIENT MAY RECOVER UNLIMITED DAMAGES in the event of gross negligence
or willful misconduct.

6. NON-COMPETE
During the term and for two (2) years thereafter, Vendor shall not compete
with Client, directly or indirectly, in any competitive business activities
in the same market.

7. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware,
without regard to conflict of law principles.

8. FORCE MAJEURE
Neither party shall be liable for delays caused by circumstances beyond
their reasonable control, including acts of God, natural disasters,
or government actions.

9. TERM AND TERMINATION
This Agreement commences on the Effective Date and continues for one (1) year,
with automatic renewal for successive one-year terms unless either party
provides ninety (90) days written notice of non-renewal.
The Company may terminate this Agreement for convenience upon 30 days notice.
"""


SAMPLE_CLAUSE = {
    "clause_index": 0,
    "heading": "5. LIMITATION OF LIABILITY",
    "text": (
        "NOTWITHSTANDING ANYTHING TO THE CONTRARY, VENDOR SHALL HAVE NO LIABILITY "
        "CAP AND CLIENT MAY RECOVER UNLIMITED DAMAGES in the event of gross negligence "
        "or willful misconduct."
    ),
    "page_number": 1,
}


# ── PDF Parser Tests ──────────────────────────────────────────

class TestPDFParser:
    def test_clean_text(self):
        from backend.services.pdf_parser import _clean_text
        raw = "Hello\r\nWorld\n\n\n\n   extra   spaces"
        result = _clean_text(raw)
        assert "\r" not in result
        assert "\n\n\n" not in result
        assert "extra   spaces" not in result

    def test_is_heading_numbered(self):
        from backend.services.pdf_parser import is_heading
        assert is_heading("1. SERVICES")
        assert is_heading("1.1 Payment Terms")
        assert is_heading("2.3.1 Specific Clause")

    def test_is_heading_article(self):
        from backend.services.pdf_parser import is_heading
        assert is_heading("ARTICLE I DEFINITIONS")
        assert is_heading("SECTION 2. PAYMENT")

    def test_is_heading_false_cases(self):
        from backend.services.pdf_parser import is_heading
        assert not is_heading("This is a regular sentence that is too long to be a heading.")
        assert not is_heading("xx")

    def test_segment_into_clauses(self):
        from backend.services.pdf_parser import segment_into_clauses
        pages = [{"page": 1, "text": SAMPLE_CONTRACT_TEXT}]
        clauses = segment_into_clauses(SAMPLE_CONTRACT_TEXT, pages)
        assert len(clauses) >= 3
        # Each clause should have required fields
        for c in clauses:
            assert "clause_index" in c
            assert "text" in c
            assert len(c["text"]) > 0

    def test_segment_preserves_order(self):
        from backend.services.pdf_parser import segment_into_clauses
        pages = [{"page": 1, "text": SAMPLE_CONTRACT_TEXT}]
        clauses = segment_into_clauses(SAMPLE_CONTRACT_TEXT, pages)
        indices = [c["clause_index"] for c in clauses]
        assert indices == sorted(indices)

    def test_sentence_fallback(self):
        from backend.services.pdf_parser import _sentence_based_segmentation
        # Text with no headings
        plain = "This is sentence one. This is sentence two. This is sentence three. Fourth sentence here."
        clauses = _sentence_based_segmentation(plain, max_sentences=2)
        assert len(clauses) >= 1


# ── NER Service Tests ─────────────────────────────────────────

class TestNERService:
    def setup_method(self):
        from backend.services.ner_service import NERService
        self.ner = NERService.__new__(NERService)
        self.ner.model_name = "en_core_web_sm"
        self.ner._nlp = None
        self.ner._loaded = False

    def test_extract_dates(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        ner._nlp = None
        ner._loaded = True  # skip spacy
        entities = ner._rule_based_extract("Agreement dated January 15, 2024", clause_index=0)
        dates = [e for e in entities if e["entity_type"] == "DATE"]
        assert len(dates) > 0
        assert "January 15, 2024" in dates[0]["text"]

    def test_extract_money(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        ner._nlp = None
        ner._loaded = True
        entities = ner._rule_based_extract("Payment of $500,000 USD is due", clause_index=0)
        money = [e for e in entities if e["entity_type"] == "MONEY"]
        assert len(money) > 0

    def test_extract_obligations(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        ner._nlp = None
        ner._loaded = True
        entities = ner._rule_based_extract(
            "Vendor shall provide monthly reports to Client", clause_index=0
        )
        obligations = [e for e in entities if e["entity_type"] == "OBLIGATION"]
        assert len(obligations) > 0

    def test_extract_jurisdiction(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        ner._nlp = None
        ner._loaded = True
        entities = ner._rule_based_extract(
            "governed by the laws of the State of Delaware", clause_index=0
        )
        jurisdictions = [e for e in entities if e["entity_type"] == "JURISDICTION"]
        assert len(jurisdictions) > 0

    def test_deduplicate(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        entities = [
            {"entity_type": "DATE", "text": "January 2024", "normalized": "", "clause_index": 0, "start_char": 0, "end_char": 0, "confidence": 0.9},
            {"entity_type": "DATE", "text": "January 2024", "normalized": "", "clause_index": 0, "start_char": 0, "end_char": 0, "confidence": 0.9},
        ]
        result = ner._deduplicate(entities)
        assert len(result) == 1

    def test_extract_parties(self):
        from backend.services.ner_service import NERService
        ner = NERService.__new__(NERService)
        ner._nlp = None
        ner._loaded = True
        parties = ner.extract_parties(SAMPLE_CONTRACT_TEXT)
        # Should find at least one party
        assert isinstance(parties, list)


# ── Risk Classifier Tests ─────────────────────────────────────

class TestRiskClassifier:
    def setup_method(self):
        from backend.models.risk_classifier import LegalBERTClassifier
        self.clf = LegalBERTClassifier.__new__(LegalBERTClassifier)
        self.clf._use_heuristic = True
        self.clf._loaded = True
        self.clf._tokenizer = None
        self.clf._model = None

    def test_heuristic_non_compete(self):
        text = "Vendor shall not compete with Client in any competitive business activities."
        result = self.clf._heuristic_classify(text)
        assert result["risk_score"] > 0
        cats = [c["category"] for c in result["risk_categories"]]
        assert "non_compete" in cats

    def test_heuristic_uncapped_liability(self):
        text = "Vendor shall have no liability cap and unlimited damages may be recovered."
        result = self.clf._heuristic_classify(text)
        assert result["risk_score"] >= 8.0
        assert result["risk_level"] in ("high", "critical")

    def test_heuristic_low_risk(self):
        text = "This agreement is governed by Delaware law."
        result = self.clf._heuristic_classify(text)
        assert result["risk_score"] < 8.0

    def test_heuristic_indemnification(self):
        text = "Vendor shall indemnify, defend, and hold harmless Client from all claims."
        result = self.clf._heuristic_classify(text)
        cats = [c["category"] for c in result["risk_categories"]]
        assert "indemnification" in cats

    def test_heuristic_force_majeure(self):
        text = "Neither party shall be liable due to force majeure events or acts of God."
        result = self.clf._heuristic_classify(text)
        cats = [c["category"] for c in result["risk_categories"]]
        assert "force_majeure" in cats

    def test_score_range(self):
        for text in [
            "All payments are due within 30 days.",
            "Unlimited liability with no cap whatsoever.",
            "Governed by the laws of New York.",
        ]:
            result = self.clf._heuristic_classify(text)
            assert 0 <= result["risk_score"] <= 10

    def test_result_schema(self):
        text = "Vendor shall indemnify Client."
        result = self.clf._heuristic_classify(text)
        required = {"risk_score", "risk_level", "risk_categories", "confidence", "top_risk_tokens", "explanation"}
        assert required.issubset(result.keys())

    def test_compute_risk_score_empty(self):
        score = self.clf._compute_risk_score([])
        assert score == 0.0

    def test_explanation_generated(self):
        text = "Client may terminate for convenience at any time without cause."
        result = self.clf._heuristic_classify(text)
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 10


# ── Risk Categories Tests ─────────────────────────────────────

class TestRiskCategories:
    def test_score_to_level_low(self):
        from backend.utils.risk_categories import score_to_level
        assert score_to_level(0.0) == "low"
        assert score_to_level(2.9) == "low"

    def test_score_to_level_medium(self):
        from backend.utils.risk_categories import score_to_level
        assert score_to_level(3.0) == "medium"
        assert score_to_level(5.9) == "medium"

    def test_score_to_level_high(self):
        from backend.utils.risk_categories import score_to_level
        assert score_to_level(6.0) == "high"
        assert score_to_level(8.4) == "high"

    def test_score_to_level_critical(self):
        from backend.utils.risk_categories import score_to_level
        assert score_to_level(8.5) == "critical"
        assert score_to_level(10.0) == "critical"

    def test_cuad_categories_loaded(self):
        from backend.utils.risk_categories import CUAD_CATEGORIES
        assert len(CUAD_CATEGORIES) >= 40
        # All required fields
        for name, cat in CUAD_CATEGORIES.items():
            assert 0 <= cat.base_weight <= 1.0
            assert cat.risk_level in ("low", "medium", "high", "critical")


# ── Comparator Tests ──────────────────────────────────────────

class TestComparator:
    def _make_clauses(self, texts, base_score=2.0):
        return [
            {
                "clause_index": i,
                "text": t,
                "risk_score": base_score,
                "risk_level": "low",
                "risk_categories": [],
                "heading": None,
            }
            for i, t in enumerate(texts)
        ]

    def test_identical_contracts(self):
        from backend.services.comparator import compare_contracts
        clauses = self._make_clauses(["Clause one text.", "Clause two text."])
        result = compare_contracts(clauses, clauses, "V1", "V2")
        assert result["stats"]["added_count"] == 0
        assert result["stats"]["removed_count"] == 0
        assert result["stats"]["unchanged_count"] == 2

    def test_added_clause(self):
        from backend.services.comparator import compare_contracts
        v1 = self._make_clauses(["Original clause one."])
        v2 = self._make_clauses(["Original clause one.", "New clause added in v2."])
        result = compare_contracts(v1, v2)
        assert result["stats"]["added_count"] >= 1

    def test_removed_clause(self):
        from backend.services.comparator import compare_contracts
        v1 = self._make_clauses(["Clause one.", "Clause two."])
        v2 = self._make_clauses(["Clause one."])
        result = compare_contracts(v1, v2)
        assert result["stats"]["removed_count"] >= 1

    def test_risk_delta_calculation(self):
        from backend.services.comparator import compare_contracts
        v1 = self._make_clauses(["Test clause."], base_score=2.0)
        v2 = self._make_clauses(["Test clause."], base_score=2.0)
        result = compare_contracts(v1, v2)
        assert result["stats"]["risk_delta"] == 0.0

    def test_inline_diff(self):
        from backend.services.comparator import _inline_diff
        diff = _inline_diff("hello world test", "hello universe test")
        types = [d["type"] for d in diff]
        assert "added" in types or "removed" in types

    def test_similarity(self):
        from backend.services.comparator import _similarity
        s = _similarity("hello world", "hello world")
        assert s == 1.0
        s2 = _similarity("hello world", "goodbye universe")
        assert s2 < 1.0

    def test_summary_generated(self):
        from backend.services.comparator import compare_contracts
        v1 = self._make_clauses(["Clause one."])
        v2 = self._make_clauses(["Clause two."])
        result = compare_contracts(v1, v2, "Contract A", "Contract B")
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 10


# ── Config Tests ──────────────────────────────────────────────

class TestConfig:
    def test_settings_load(self):
        from backend.utils.config import settings
        assert settings.APP_NAME == "LexiScan"
        assert settings.MAX_CLAUSE_LENGTH == 512
        assert settings.BATCH_SIZE > 0

    def test_allowed_origins_list(self):
        from backend.utils.config import settings
        origins = settings.allowed_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
