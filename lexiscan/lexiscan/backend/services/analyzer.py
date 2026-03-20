"""
LexiScan — Contract Analyzer Service
Orchestrates: PDF parsing → clause segmentation → risk classification → NER
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from backend.models.risk_classifier import get_classifier
from backend.services.ner_service import get_ner_service
from backend.services.pdf_parser import extract_text_from_pdf, segment_into_clauses
from backend.utils.config import settings
from backend.utils.risk_categories import score_to_level


class ContractAnalyzer:
    """End-to-end contract analysis pipeline."""

    def __init__(self):
        self.classifier = get_classifier()
        self.ner = get_ner_service()

    def analyze(
        self,
        pdf_path: str,
        contract_name: str,
    ) -> Dict:
        """
        Full analysis pipeline.

        Returns analysis result dict compatible with DB models.
        """
        logger.info(f"Starting analysis: {contract_name}")
        start = datetime.utcnow()

        # 1. Extract text from PDF
        try:
            full_text, page_count, pages = extract_text_from_pdf(pdf_path)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")

        if not full_text.strip():
            raise ValueError("PDF appears to be empty or image-only (no extractable text)")

        # 2. Segment into clauses
        raw_clauses = segment_into_clauses(full_text, pages)
        logger.info(f"Segmented into {len(raw_clauses)} clauses")

        # 3. Classify each clause
        clause_texts = [c["text"] for c in raw_clauses]
        classifications = self.classifier.classify_batch(clause_texts)

        # 4. Extract named entities per clause
        all_entities = []
        for i, clause in enumerate(raw_clauses):
            entities = self.ner.extract_entities(clause["text"], clause_index=i)
            all_entities.extend(entities)

        # 5. Extract parties from preamble
        parties = self.ner.extract_parties(full_text)

        # 6. Assemble clause results
        clauses_out = []
        for clause, classification in zip(raw_clauses, classifications):
            clauses_out.append({
                "clause_index": clause["clause_index"],
                "heading": clause.get("heading"),
                "text": clause["text"],
                "page_number": clause.get("page_number"),
                "risk_score": classification["risk_score"],
                "risk_level": classification["risk_level"],
                "risk_categories": classification["risk_categories"],
                "confidence": classification["confidence"],
                "top_risk_tokens": classification["top_risk_tokens"],
                "explanation": classification["explanation"],
                "is_flagged": classification["risk_score"] >= 6.0,
                "flag_reason": (
                    classification["explanation"]
                    if classification["risk_score"] >= 6.0
                    else None
                ),
            })

        # 7. Compute overall risk score (weighted average, penalizing critical clauses)
        overall_risk = self._compute_overall_risk(clauses_out)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(f"Analysis complete in {elapsed:.1f}s | Overall risk: {overall_risk:.1f}/10")

        return {
            "contract": {
                "name": contract_name,
                "file_path": pdf_path,
                "file_size": os.path.getsize(pdf_path),
                "page_count": page_count,
                "raw_text": full_text[:50000],  # store first 50k chars
                "overall_risk_score": overall_risk,
                "status": "done",
                "analyzed_at": datetime.utcnow().isoformat(),
            },
            "clauses": clauses_out,
            "entities": all_entities,
            "parties": parties,
            "summary": self._generate_summary(clauses_out, overall_risk, parties),
            "stats": self._compute_stats(clauses_out),
            "elapsed_seconds": elapsed,
        }

    def _compute_overall_risk(self, clauses: List[Dict]) -> float:
        """
        Weighted overall risk:
        - Mean of all clause scores
        - 2x weight for critical/high clauses
        """
        if not clauses:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for c in clauses:
            score = c["risk_score"]
            weight = 2.0 if c["risk_level"] in ("critical", "high") else 1.0
            weighted_sum += score * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    def _compute_stats(self, clauses: List[Dict]) -> Dict:
        """Compute aggregate statistics."""
        levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        categories_seen = {}

        for c in clauses:
            level = c.get("risk_level", "low")
            levels[level] = levels.get(level, 0) + 1

            for cat in c.get("risk_categories", []):
                cat_label = cat.get("label", cat.get("category", "unknown"))
                categories_seen[cat_label] = categories_seen.get(cat_label, 0) + 1

        top_categories = sorted(
            categories_seen.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_clauses": len(clauses),
            "flagged_clauses": sum(1 for c in clauses if c.get("is_flagged")),
            "risk_distribution": levels,
            "top_risk_categories": [
                {"category": cat, "count": cnt} for cat, cnt in top_categories
            ],
            "avg_risk_score": round(
                sum(c["risk_score"] for c in clauses) / max(len(clauses), 1), 2
            ),
        }

    def _generate_summary(
        self, clauses: List[Dict], overall_risk: float, parties: List[str]
    ) -> str:
        """Generate executive summary."""
        level = score_to_level(overall_risk)
        critical_count = sum(1 for c in clauses if c["risk_level"] == "critical")
        high_count = sum(1 for c in clauses if c["risk_level"] == "high")
        flagged = sum(1 for c in clauses if c.get("is_flagged"))

        party_str = (
            f"Parties identified: {', '.join(parties[:3])}. "
            if parties else ""
        )

        risk_desc = {
            "low": "This contract presents a low overall risk profile.",
            "medium": "This contract contains moderate risk provisions requiring review.",
            "high": "This contract contains significant risk provisions requiring careful legal review.",
            "critical": "⚠️ This contract contains critical risk provisions. Immediate legal review is strongly recommended.",
        }.get(level, "")

        return (
            f"{risk_desc} "
            f"Overall risk score: {overall_risk:.1f}/10. "
            f"{party_str}"
            f"Analyzed {len(clauses)} clauses: "
            f"{critical_count} critical, {high_count} high, {flagged} total flagged."
        )


# Singleton
_analyzer: Optional[ContractAnalyzer] = None


def get_analyzer() -> ContractAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ContractAnalyzer()
    return _analyzer
