"""
LexiScan — LegalBERT Risk Classifier
Uses HuggingFace Transformers with nlpaueb/legal-bert-base-uncased
to classify clauses into CUAD categories and compute risk scores.

Architecture:
  - Tokenize clause text with LegalBERT tokenizer
  - Run through BERT encoder (or fine-tuned checkpoint if available)
  - For each CUAD category: binary classification head
  - Aggregate into a risk score 0–10
  - Extract token-level attribution for explainability
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from backend.utils.config import settings
from backend.utils.risk_categories import (
    CUAD_CATEGORIES,
    RiskCategory,
    score_to_level,
)


class LegalBERTClassifier:
    """
    LegalBERT-based clause risk classifier.

    In production: loads fine-tuned checkpoint.
    Without GPU / on first run: uses heuristic-weighted keyword approach
    that mirrors BERT's expected behavior for demo purposes.
    """

    def __init__(
        self,
        model_name: str = "nlpaueb/legal-bert-base-uncased",
        cache_dir: Optional[str] = None,
        use_gpu: bool = False,
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir or str(settings.model_cache_path)
        self.use_gpu = use_gpu
        self._tokenizer = None
        self._model = None
        self._loaded = False
        self._use_heuristic = False  # fallback flag

    # ── Loading ─────────────────────────────────────────────

    def load(self):
        """Load model and tokenizer. Lazy — call before first inference."""
        if self._loaded:
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch

            logger.info(f"Loading LegalBERT: {self.model_name}")
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
            )

            # Try to load fine-tuned CUAD checkpoint
            checkpoint_path = Path(self.cache_dir) / "cuad_checkpoint"
            if checkpoint_path.exists():
                logger.info("Loading fine-tuned CUAD checkpoint")
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    str(checkpoint_path),
                    num_labels=len(CUAD_CATEGORIES),
                    problem_type="multi_label_classification",
                )
            else:
                logger.info("No fine-tuned checkpoint found — using base model with heuristic heads")
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                    num_labels=len(CUAD_CATEGORIES),
                    problem_type="multi_label_classification",
                    ignore_mismatched_sizes=True,
                )

            self._device = "cuda" if (self.use_gpu and torch.cuda.is_available()) else "cpu"
            self._model = self._model.to(self._device)
            self._model.eval()
            self._loaded = True
            logger.info(f"LegalBERT loaded on device: {self._device}")

        except Exception as e:
            logger.warning(f"Could not load LegalBERT ({e}) — using heuristic classifier")
            self._use_heuristic = True
            self._loaded = True

    # ── Inference ────────────────────────────────────────────

    def classify_clause(self, clause_text: str) -> Dict:
        """
        Classify a single clause.

        Returns:
            {
              "risk_score": float (0–10),
              "risk_level": str,
              "risk_categories": [{"category": str, "confidence": float}],
              "confidence": float,
              "top_risk_tokens": [{"token": str, "score": float}],
              "explanation": str,
            }
        """
        self.load()

        if self._use_heuristic:
            return self._heuristic_classify(clause_text)

        try:
            return self._bert_classify(clause_text)
        except Exception as e:
            logger.warning(f"BERT inference failed ({e}), falling back to heuristic")
            return self._heuristic_classify(clause_text)

    def classify_batch(self, clauses: List[str]) -> List[Dict]:
        """Classify multiple clauses efficiently."""
        self.load()
        results = []
        for clause in clauses:
            results.append(self.classify_clause(clause))
        return results

    # ── BERT Inference ───────────────────────────────────────

    def _bert_classify(self, text: str) -> Dict:
        """Run actual BERT inference."""
        import torch

        # Truncate to max length
        inputs = self._tokenizer(
            text,
            max_length=settings.MAX_CLAUSE_LENGTH,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = torch.sigmoid(logits).squeeze().cpu().numpy()

        # Map probabilities to categories
        category_names = list(CUAD_CATEGORIES.keys())
        detected = []
        for i, (cat_name, prob) in enumerate(zip(category_names, probs)):
            if prob > 0.3:  # threshold
                cat = CUAD_CATEGORIES[cat_name]
                detected.append({
                    "category": cat_name,
                    "label": cat.label,
                    "confidence": float(prob),
                    "risk_level": cat.risk_level,
                })

        # Compute risk score
        risk_score = self._compute_risk_score(detected)
        risk_level = score_to_level(risk_score)

        # Token attribution (simplified gradient-based)
        top_tokens = self._get_top_tokens(inputs, text)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_categories": detected,
            "confidence": float(np.max(probs)) if len(probs) > 0 else 0.0,
            "top_risk_tokens": top_tokens,
            "explanation": self._generate_explanation(detected, risk_score),
        }

    def _get_top_tokens(self, inputs, text: str, top_k: int = 5) -> List[Dict]:
        """
        Simplified token-level attribution.
        In production, use SHAP or Integrated Gradients.
        Here: use attention weights from first layer as proxy.
        """
        import torch

        try:
            with torch.no_grad():
                outputs = self._model(**inputs, output_attentions=True)
                # Average attention across heads, first layer
                attn = outputs.attentions[0]  # (batch, heads, seq, seq)
                attn_mean = attn.squeeze(0).mean(0).mean(0).cpu().numpy()  # (seq,)

            tokens = self._tokenizer.convert_ids_to_tokens(
                inputs["input_ids"].squeeze().tolist()
            )

            # Sort by attention weight
            token_scores = list(zip(tokens, attn_mean))
            token_scores = [
                (t, float(s)) for t, s in token_scores
                if t not in ("[CLS]", "[SEP]", "[PAD]", "##")
            ]
            token_scores.sort(key=lambda x: x[1], reverse=True)

            return [
                {"token": t, "score": round(s, 4)}
                for t, s in token_scores[:top_k]
            ]
        except Exception:
            return []

    # ── Heuristic Classifier ─────────────────────────────────

    def _heuristic_classify(self, text: str) -> Dict:
        """
        Keyword-based heuristic classifier.
        Used when BERT model is unavailable.
        Mirrors expected BERT behavior for CUAD categories.
        """
        text_lower = text.lower()
        detected = []
        scored_tokens = {}

        # Keyword mappings per CUAD category
        keyword_map: Dict[str, List[Tuple[str, float]]] = {
            "uncapped_liability": [
                ("unlimited liability", 1.0), ("no cap", 0.9),
                ("unlimited damages", 0.95), ("no limitation on liability", 0.9),
            ],
            "non_compete": [
                ("non-compete", 0.95), ("noncompete", 0.9),
                ("not compete", 0.85), ("competitive activities", 0.7),
                ("competing business", 0.75),
            ],
            "termination_for_convenience": [
                ("terminate for convenience", 0.9), ("termination for convenience", 0.95),
                ("without cause", 0.8), ("without reason", 0.75),
            ],
            "ip_ownership": [
                ("intellectual property", 0.7), ("work made for hire", 0.95),
                ("assigns all right", 0.9), ("ip ownership", 0.9),
                ("proprietary rights", 0.7),
            ],
            "indemnification": [
                ("indemnify", 0.9), ("indemnification", 0.95),
                ("hold harmless", 0.85), ("defend and indemnify", 0.95),
            ],
            "notice_period_to_terminate_renewal": [
                ("auto-renew", 0.9), ("automatically renew", 0.95),
                ("renewal notice", 0.85), ("notice of non-renewal", 0.9),
            ],
            "liquidated_damages": [
                ("liquidated damages", 0.95), ("penalty clause", 0.8),
                ("pre-agreed damages", 0.85),
            ],
            "change_of_control": [
                ("change of control", 0.95), ("merger or acquisition", 0.8),
                ("acquisition", 0.6), ("takeover", 0.7),
            ],
            "governing_law": [
                ("governed by the laws", 0.9), ("governing law", 0.85),
                ("jurisdiction of", 0.8), ("choice of law", 0.85),
            ],
            "confidentiality": [
                ("confidential", 0.7), ("non-disclosure", 0.8),
                ("proprietary information", 0.7), ("trade secret", 0.85),
            ],
            "force_majeure": [
                ("force majeure", 0.95), ("act of god", 0.9),
                ("beyond reasonable control", 0.8),
            ],
            "anti_assignment": [
                ("may not assign", 0.9), ("without prior written consent", 0.75),
                ("assignment prohibited", 0.9), ("non-assignable", 0.85),
            ],
            "exclusivity": [
                ("exclusive", 0.7), ("sole and exclusive", 0.85),
                ("exclusivity", 0.9), ("exclusively", 0.65),
            ],
            "minimum_commitment": [
                ("minimum purchase", 0.9), ("minimum order", 0.85),
                ("minimum commitment", 0.9), ("purchase obligation", 0.8),
            ],
            "audit_rights": [
                ("audit rights", 0.9), ("right to audit", 0.9),
                ("books and records", 0.7), ("inspection rights", 0.75),
            ],
        }

        for cat_name, keywords in keyword_map.items():
            max_score = 0.0
            matched_tokens = []
            for keyword, weight in keywords:
                if keyword in text_lower:
                    if weight > max_score:
                        max_score = weight
                    matched_tokens.append(keyword)
                    for word in keyword.split():
                        scored_tokens[word] = max(scored_tokens.get(word, 0), weight)

            if max_score > 0.3 and cat_name in CUAD_CATEGORIES:
                cat = CUAD_CATEGORIES[cat_name]
                detected.append({
                    "category": cat_name,
                    "label": cat.label,
                    "confidence": max_score,
                    "risk_level": cat.risk_level,
                })

        # Risk score
        risk_score = self._compute_risk_score(detected)
        risk_level = score_to_level(risk_score)

        # Top tokens
        top_tokens = [
            {"token": t, "score": round(s, 4)}
            for t, s in sorted(scored_tokens.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        max_conf = max((d["confidence"] for d in detected), default=0.0)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_categories": detected,
            "confidence": max_conf,
            "top_risk_tokens": top_tokens,
            "explanation": self._generate_explanation(detected, risk_score),
        }

    # ── Scoring ──────────────────────────────────────────────

    def _compute_risk_score(self, detected: List[Dict]) -> float:
        """
        Aggregate detected categories into a 0–10 risk score.
        Uses base_weight from RiskCategory + confidence.
        """
        if not detected:
            return 0.0

        total_weight = 0.0
        weight_sum = 0.0

        for d in detected:
            cat = CUAD_CATEGORIES.get(d["category"])
            if not cat:
                continue
            w = cat.base_weight * d["confidence"]
            total_weight += w
            weight_sum += cat.base_weight

        if weight_sum == 0:
            return 0.0

        # Normalize to 0–10
        raw = total_weight / max(weight_sum, 0.1)
        score = min(raw * 10, 10.0)
        return round(score, 2)

    def _generate_explanation(self, detected: List[Dict], risk_score: float) -> str:
        """Generate human-readable explanation."""
        if not detected:
            return "No significant risk indicators detected in this clause."

        # Sort by confidence
        top = sorted(detected, key=lambda x: x["confidence"], reverse=True)[:3]
        top_labels = ", ".join(f'"{d["label"]}"' for d in top)
        level = score_to_level(risk_score)

        level_text = {
            "low": "low risk",
            "medium": "moderate risk",
            "high": "high risk — review carefully",
            "critical": "CRITICAL risk — legal review required",
        }.get(level, "unknown risk")

        return (
            f"This clause is classified as {level_text} (score: {risk_score}/10). "
            f"Key risk indicators: {top_labels}. "
            f"{'Immediate legal review is strongly recommended.' if level == 'critical' else ''}"
        )


# ── Singleton ────────────────────────────────────────────────

_classifier: Optional[LegalBERTClassifier] = None


def get_classifier() -> LegalBERTClassifier:
    global _classifier
    if _classifier is None:
        _classifier = LegalBERTClassifier(
            model_name=settings.LEGALBERT_MODEL,
            cache_dir=str(settings.model_cache_path),
        )
    return _classifier
