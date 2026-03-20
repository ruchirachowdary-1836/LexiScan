"""
LexiScan — CUAD Risk Categories
Based on the Contract Understanding Atticus Dataset (41 clause categories)
Each category has a base risk weight and risk level.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RiskCategory:
    name: str
    label: str          # short display label
    base_weight: float  # 0.0 – 1.0, multiplied into risk score
    risk_level: str     # low | medium | high | critical
    description: str
    cuad_question: str  # Original CUAD question


# ── 41 CUAD Categories ────────────────────────────────────────

CUAD_CATEGORIES: Dict[str, RiskCategory] = {
    "document_name": RiskCategory(
        name="document_name",
        label="Document Name",
        base_weight=0.1,
        risk_level="low",
        description="The name of the contract",
        cuad_question="What is the name of the contract?",
    ),
    "parties": RiskCategory(
        name="parties",
        label="Parties",
        base_weight=0.2,
        risk_level="low",
        description="The parties who signed the agreement",
        cuad_question="Who are the parties to the agreement?",
    ),
    "agreement_date": RiskCategory(
        name="agreement_date",
        label="Agreement Date",
        base_weight=0.1,
        risk_level="low",
        description="The date of the contract",
        cuad_question="What is the date of the contract?",
    ),
    "effective_date": RiskCategory(
        name="effective_date",
        label="Effective Date",
        base_weight=0.2,
        risk_level="low",
        description="The date when the contract is effective",
        cuad_question="What is the effective date of the contract?",
    ),
    "expiration_date": RiskCategory(
        name="expiration_date",
        label="Expiration Date",
        base_weight=0.3,
        risk_level="medium",
        description="The date when the contract expires",
        cuad_question="On what date will the contract's term expire?",
    ),
    "renewal_term": RiskCategory(
        name="renewal_term",
        label="Renewal Term",
        base_weight=0.5,
        risk_level="medium",
        description="Automatic renewal provisions",
        cuad_question="What is the term after renewal?",
    ),
    "notice_period_to_terminate_renewal": RiskCategory(
        name="notice_period_to_terminate_renewal",
        label="Auto-Renewal Notice",
        base_weight=0.7,
        risk_level="high",
        description="Notice required to prevent automatic renewal",
        cuad_question="What is the notice period required to terminate renewal?",
    ),
    "governing_law": RiskCategory(
        name="governing_law",
        label="Governing Law",
        base_weight=0.4,
        risk_level="medium",
        description="Which jurisdiction's law governs the contract",
        cuad_question="Which state/country's law governs the contract?",
    ),
    "dispute_resolution": RiskCategory(
        name="dispute_resolution",
        label="Dispute Resolution",
        base_weight=0.5,
        risk_level="medium",
        description="How disputes are resolved (arbitration, litigation)",
        cuad_question="What is the dispute resolution mechanism?",
    ),
    "anti_assignment": RiskCategory(
        name="anti_assignment",
        label="Anti-Assignment",
        base_weight=0.6,
        risk_level="high",
        description="Restrictions on assigning the contract to another party",
        cuad_question="Is consent or notice required for the contract to be assigned?",
    ),
    "revenue_profit_sharing": RiskCategory(
        name="revenue_profit_sharing",
        label="Revenue / Profit Sharing",
        base_weight=0.6,
        risk_level="high",
        description="Revenue or profit sharing provisions",
        cuad_question="Is there a revenue/profit sharing arrangement?",
    ),
    "price_restrictions": RiskCategory(
        name="price_restrictions",
        label="Price Restrictions",
        base_weight=0.6,
        risk_level="high",
        description="Restrictions on pricing or minimum/maximum price",
        cuad_question="Are there restrictions on pricing?",
    ),
    "minimum_commitment": RiskCategory(
        name="minimum_commitment",
        label="Minimum Commitment",
        base_weight=0.7,
        risk_level="high",
        description="Minimum purchase or volume commitments",
        cuad_question="Is there a minimum order size or minimum commitment?",
    ),
    "volume_restriction": RiskCategory(
        name="volume_restriction",
        label="Volume Restriction",
        base_weight=0.5,
        risk_level="medium",
        description="Restrictions on volume of goods/services",
        cuad_question="Are there restrictions on volume of goods/services?",
    ),
    "ip_ownership": RiskCategory(
        name="ip_ownership",
        label="IP Ownership",
        base_weight=0.8,
        risk_level="high",
        description="Who owns intellectual property created under the agreement",
        cuad_question="Does one party own/acquire IP rights?",
    ),
    "joint_ip_ownership": RiskCategory(
        name="joint_ip_ownership",
        label="Joint IP Ownership",
        base_weight=0.7,
        risk_level="high",
        description="Joint ownership of intellectual property",
        cuad_question="Is there joint ownership of IP?",
    ),
    "license_grant": RiskCategory(
        name="license_grant",
        label="License Grant",
        base_weight=0.5,
        risk_level="medium",
        description="License grants between the parties",
        cuad_question="Does the contract include a license grant?",
    ),
    "non_transferable_license": RiskCategory(
        name="non_transferable_license",
        label="Non-Transferable License",
        base_weight=0.5,
        risk_level="medium",
        description="License cannot be transferred",
        cuad_question="Is the license non-transferable?",
    ),
    "affiliate_license_licensor": RiskCategory(
        name="affiliate_license_licensor",
        label="Affiliate License (Licensor)",
        base_weight=0.4,
        risk_level="medium",
        description="License extended to licensor's affiliates",
        cuad_question="Can affiliates of the licensor exercise the license?",
    ),
    "affiliate_license_licensee": RiskCategory(
        name="affiliate_license_licensee",
        label="Affiliate License (Licensee)",
        base_weight=0.4,
        risk_level="medium",
        description="License extended to licensee's affiliates",
        cuad_question="Can affiliates of the licensee exercise the license?",
    ),
    "unlimited_license": RiskCategory(
        name="unlimited_license",
        label="Unlimited License",
        base_weight=0.7,
        risk_level="high",
        description="Unlimited license grant",
        cuad_question="Does the contract grant an unlimited license?",
    ),
    "exclusivity": RiskCategory(
        name="exclusivity",
        label="Exclusivity",
        base_weight=0.8,
        risk_level="high",
        description="Exclusive arrangements restricting either party",
        cuad_question="Is there an exclusivity arrangement?",
    ),
    "non_compete": RiskCategory(
        name="non_compete",
        label="Non-Compete",
        base_weight=0.9,
        risk_level="critical",
        description="Non-compete restrictions on parties",
        cuad_question="Do parties have non-compete obligations?",
    ),
    "non_solicitation": RiskCategory(
        name="non_solicitation",
        label="Non-Solicitation",
        base_weight=0.7,
        risk_level="high",
        description="Restrictions on soliciting employees or customers",
        cuad_question="Do parties have non-solicitation obligations?",
    ),
    "confidentiality": RiskCategory(
        name="confidentiality",
        label="Confidentiality",
        base_weight=0.4,
        risk_level="medium",
        description="Confidentiality and non-disclosure obligations",
        cuad_question="Do parties have confidentiality obligations?",
    ),
    "audit_rights": RiskCategory(
        name="audit_rights",
        label="Audit Rights",
        base_weight=0.5,
        risk_level="medium",
        description="Right to audit the other party's books and records",
        cuad_question="Do parties have audit rights?",
    ),
    "uncapped_liability": RiskCategory(
        name="uncapped_liability",
        label="Uncapped Liability",
        base_weight=1.0,
        risk_level="critical",
        description="Liability without a cap or limitation",
        cuad_question="Is there uncapped liability?",
    ),
    "cap_on_liability": RiskCategory(
        name="cap_on_liability",
        label="Liability Cap",
        base_weight=0.3,
        risk_level="low",
        description="Cap or limitation on liability",
        cuad_question="Is there a cap on liability?",
    ),
    "liquidated_damages": RiskCategory(
        name="liquidated_damages",
        label="Liquidated Damages",
        base_weight=0.8,
        risk_level="high",
        description="Pre-set damages for breach",
        cuad_question="Does the contract include liquidated damages?",
    ),
    "warranty_duration": RiskCategory(
        name="warranty_duration",
        label="Warranty Duration",
        base_weight=0.4,
        risk_level="medium",
        description="Duration of warranties provided",
        cuad_question="What is the duration of warranties?",
    ),
    "insurance": RiskCategory(
        name="insurance",
        label="Insurance",
        base_weight=0.5,
        risk_level="medium",
        description="Insurance requirements",
        cuad_question="Do parties have insurance obligations?",
    ),
    "covenant_not_to_sue": RiskCategory(
        name="covenant_not_to_sue",
        label="Covenant Not to Sue",
        base_weight=0.7,
        risk_level="high",
        description="Agreement not to sue the other party",
        cuad_question="Is there a covenant not to sue?",
    ),
    "third_party_beneficiary": RiskCategory(
        name="third_party_beneficiary",
        label="Third Party Beneficiary",
        base_weight=0.6,
        risk_level="high",
        description="Third parties who benefit from the contract",
        cuad_question="Are there third party beneficiaries?",
    ),
    "termination_for_convenience": RiskCategory(
        name="termination_for_convenience",
        label="Termination for Convenience",
        base_weight=0.8,
        risk_level="high",
        description="Right to terminate without cause",
        cuad_question="Can a party terminate the contract for convenience?",
    ),
    "rofr_rofo_rofn": RiskCategory(
        name="rofr_rofo_rofn",
        label="ROFR / ROFO / ROFN",
        base_weight=0.7,
        risk_level="high",
        description="Right of first refusal, offer, or negotiation",
        cuad_question="Is there a right of first refusal/offer/negotiation?",
    ),
    "change_of_control": RiskCategory(
        name="change_of_control",
        label="Change of Control",
        base_weight=0.8,
        risk_level="high",
        description="Provisions triggered by change of control",
        cuad_question="Is there a change of control provision?",
    ),
    "anti_assignment_clause": RiskCategory(
        name="anti_assignment_clause",
        label="Anti-Assignment Clause",
        base_weight=0.6,
        risk_level="high",
        description="Restrictions on assigning the agreement",
        cuad_question="Is assignment restricted?",
    ),
    "clauses_on_most_favored_nation": RiskCategory(
        name="clauses_on_most_favored_nation",
        label="Most Favored Nation",
        base_weight=0.7,
        risk_level="high",
        description="Most favored nation pricing provisions",
        cuad_question="Is there a most favored nation clause?",
    ),
    "competitive_restriction_exception": RiskCategory(
        name="competitive_restriction_exception",
        label="Competitive Restriction Exception",
        base_weight=0.5,
        risk_level="medium",
        description="Exceptions to competitive restrictions",
        cuad_question="Are there exceptions to competitive restrictions?",
    ),
    "indemnification": RiskCategory(
        name="indemnification",
        label="Indemnification",
        base_weight=0.8,
        risk_level="high",
        description="Indemnification obligations between parties",
        cuad_question="Is there an indemnification clause?",
    ),
    "force_majeure": RiskCategory(
        name="force_majeure",
        label="Force Majeure",
        base_weight=0.3,
        risk_level="low",
        description="Force majeure provisions",
        cuad_question="Is there a force majeure clause?",
    ),
}

# ── Risk Level Thresholds ────────────────────────────────────

RISK_THRESHOLDS = {
    "low": (0.0, 3.0),
    "medium": (3.0, 6.0),
    "high": (6.0, 8.5),
    "critical": (8.5, 10.0),
}

RISK_COLORS = {
    "low": "#22c55e",       # green
    "medium": "#f59e0b",    # amber
    "high": "#f97316",      # orange
    "critical": "#ef4444",  # red
}

RISK_EMOJIS = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
}


def score_to_level(score: float) -> str:
    """Convert numeric risk score (0–10) to risk level string."""
    if score >= RISK_THRESHOLDS["critical"][0]:
        return "critical"
    elif score >= RISK_THRESHOLDS["high"][0]:
        return "high"
    elif score >= RISK_THRESHOLDS["medium"][0]:
        return "medium"
    else:
        return "low"


def get_high_risk_categories() -> List[str]:
    """Return category names with high/critical base weight."""
    return [
        name for name, cat in CUAD_CATEGORIES.items()
        if cat.risk_level in ("high", "critical")
    ]
