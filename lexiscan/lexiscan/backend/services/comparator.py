"""
LexiScan — Contract Comparison Service
Compares two contract versions: diffs clauses, tracks risk score changes,
identifies added/removed/modified clauses.
"""

import difflib
from typing import Dict, List, Tuple

from loguru import logger


def compare_contracts(
    clauses_v1: List[Dict],
    clauses_v2: List[Dict],
    contract_v1_name: str = "Version 1",
    contract_v2_name: str = "Version 2",
) -> Dict:
    """
    Compare two lists of clauses (from different contract versions).

    Returns structured diff with risk deltas.
    """
    logger.info(f"Comparing '{contract_v1_name}' vs '{contract_v2_name}'")

    texts_v1 = [c["text"] for c in clauses_v1]
    texts_v2 = [c["text"] for c in clauses_v2]

    # SequenceMatcher for clause-level diff
    matcher = difflib.SequenceMatcher(None, texts_v1, texts_v2, autojunk=False)
    opcodes = matcher.get_opcodes()

    added_clauses = []
    removed_clauses = []
    modified_clauses = []
    unchanged_clauses = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for idx_v1, idx_v2 in zip(range(i1, i2), range(j1, j2)):
                unchanged_clauses.append({
                    "v1_index": idx_v1,
                    "v2_index": idx_v2,
                    "text": texts_v1[idx_v1],
                    "risk_score_v1": clauses_v1[idx_v1].get("risk_score", 0),
                    "risk_score_v2": clauses_v2[idx_v2].get("risk_score", 0),
                })

        elif tag == "insert":
            for idx_v2 in range(j1, j2):
                added_clauses.append({
                    "v2_index": idx_v2,
                    "text": texts_v2[idx_v2],
                    "risk_score": clauses_v2[idx_v2].get("risk_score", 0),
                    "risk_level": clauses_v2[idx_v2].get("risk_level", "low"),
                    "risk_categories": clauses_v2[idx_v2].get("risk_categories", []),
                    "heading": clauses_v2[idx_v2].get("heading"),
                })

        elif tag == "delete":
            for idx_v1 in range(i1, i2):
                removed_clauses.append({
                    "v1_index": idx_v1,
                    "text": texts_v1[idx_v1],
                    "risk_score": clauses_v1[idx_v1].get("risk_score", 0),
                    "risk_level": clauses_v1[idx_v1].get("risk_level", "low"),
                    "heading": clauses_v1[idx_v1].get("heading"),
                })

        elif tag == "replace":
            # Pair old/new clauses
            for idx_v1, idx_v2 in zip(range(i1, i2), range(j1, j2)):
                text_diff = _inline_diff(texts_v1[idx_v1], texts_v2[idx_v2])
                risk_v1 = clauses_v1[idx_v1].get("risk_score", 0)
                risk_v2 = clauses_v2[idx_v2].get("risk_score", 0)
                modified_clauses.append({
                    "v1_index": idx_v1,
                    "v2_index": idx_v2,
                    "text_v1": texts_v1[idx_v1],
                    "text_v2": texts_v2[idx_v2],
                    "inline_diff": text_diff,
                    "risk_score_v1": risk_v1,
                    "risk_score_v2": risk_v2,
                    "risk_delta": round(risk_v2 - risk_v1, 2),
                    "risk_level_v1": clauses_v1[idx_v1].get("risk_level", "low"),
                    "risk_level_v2": clauses_v2[idx_v2].get("risk_level", "low"),
                    "heading": clauses_v2[idx_v2].get("heading"),
                    "similarity": _similarity(texts_v1[idx_v1], texts_v2[idx_v2]),
                })

            # Handle unequal lengths in replace block
            extra_v2 = range(i1 + (i2 - i1), j2) if (j2 - j1) > (i2 - i1) else range(0)
            for idx_v2 in extra_v2:
                added_clauses.append({
                    "v2_index": idx_v2,
                    "text": texts_v2[idx_v2],
                    "risk_score": clauses_v2[idx_v2].get("risk_score", 0),
                    "risk_level": clauses_v2[idx_v2].get("risk_level", "low"),
                    "risk_categories": clauses_v2[idx_v2].get("risk_categories", []),
                    "heading": clauses_v2[idx_v2].get("heading"),
                })

    # Compute aggregate risk delta
    avg_risk_v1 = (
        sum(c.get("risk_score", 0) for c in clauses_v1) / max(len(clauses_v1), 1)
    )
    avg_risk_v2 = (
        sum(c.get("risk_score", 0) for c in clauses_v2) / max(len(clauses_v2), 1)
    )
    risk_delta = round(avg_risk_v2 - avg_risk_v1, 2)

    # New high-risk additions
    new_high_risk = [
        c for c in added_clauses
        if c.get("risk_level") in ("high", "critical")
    ]

    # Risk-increasing modifications
    risk_increasing_mods = [
        c for c in modified_clauses
        if c.get("risk_delta", 0) > 1.0
    ]

    summary = _generate_comparison_summary(
        added_clauses, removed_clauses, modified_clauses,
        risk_delta, new_high_risk, risk_increasing_mods,
        contract_v1_name, contract_v2_name,
    )

    return {
        "contract_v1": contract_v1_name,
        "contract_v2": contract_v2_name,
        "added_clauses": added_clauses,
        "removed_clauses": removed_clauses,
        "modified_clauses": modified_clauses,
        "unchanged_clauses": unchanged_clauses,
        "stats": {
            "total_clauses_v1": len(clauses_v1),
            "total_clauses_v2": len(clauses_v2),
            "added_count": len(added_clauses),
            "removed_count": len(removed_clauses),
            "modified_count": len(modified_clauses),
            "unchanged_count": len(unchanged_clauses),
            "avg_risk_v1": round(avg_risk_v1, 2),
            "avg_risk_v2": round(avg_risk_v2, 2),
            "risk_delta": risk_delta,
            "new_high_risk_clauses": len(new_high_risk),
            "risk_increasing_modifications": len(risk_increasing_mods),
        },
        "new_high_risk_clauses": new_high_risk,
        "risk_increasing_modifications": risk_increasing_mods,
        "summary": summary,
    }


def _inline_diff(text_v1: str, text_v2: str) -> List[Dict]:
    """
    Word-level diff between two clause texts.
    Returns list of {text, type} where type is 'equal'|'added'|'removed'.
    """
    words_v1 = text_v1.split()
    words_v2 = text_v2.split()

    matcher = difflib.SequenceMatcher(None, words_v1, words_v2)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append({"text": " ".join(words_v1[i1:i2]), "type": "equal"})
        elif tag in ("insert", "replace"):
            if tag == "replace" and i2 > i1:
                result.append({"text": " ".join(words_v1[i1:i2]), "type": "removed"})
            result.append({"text": " ".join(words_v2[j1:j2]), "type": "added"})
        elif tag == "delete":
            result.append({"text": " ".join(words_v1[i1:i2]), "type": "removed"})

    return result


def _similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts."""
    return round(difflib.SequenceMatcher(None, text1, text2).ratio(), 3)


def _generate_comparison_summary(
    added, removed, modified, risk_delta,
    new_high_risk, risk_increasing_mods,
    v1_name, v2_name,
) -> str:
    direction = "increased" if risk_delta > 0 else "decreased"
    delta_abs = abs(risk_delta)

    parts = [
        f"Comparing '{v1_name}' → '{v2_name}': "
        f"{len(added)} clauses added, {len(removed)} removed, {len(modified)} modified. "
        f"Overall risk has {direction} by {delta_abs:.1f} points."
    ]

    if new_high_risk:
        parts.append(
            f"⚠️ {len(new_high_risk)} new high/critical risk clause(s) added."
        )

    if risk_increasing_mods:
        parts.append(
            f"🔺 {len(risk_increasing_mods)} modification(s) significantly increased risk."
        )

    return " ".join(parts)
