"""
LexiScan — Clause Explorer Page
Browse, filter, and inspect individual clauses.
"""

import streamlit as st

from frontend.components.widgets import render_clause_card, risk_badge
from frontend.utils.api_client import get_client


def render():
    st.title("🔍 Clause Explorer")
    st.markdown("Browse all clauses with risk scores, category labels, and explainability.")

    client = get_client()

    # ── Contract selection ────────────────────────────────────
    try:
        contracts = client.list_contracts()
    except Exception as e:
        st.error(f"Cannot load contracts: {e}")
        return

    if not contracts:
        st.info("No contracts analyzed yet.")
        return

    options = {f"{c['name']} — Risk: {c['overall_risk_score']:.1f}/10": c["id"] for c in contracts}
    contract_id = st.session_state.get("current_contract_id")
    ids = list(options.values())
    default_idx = ids.index(contract_id) if contract_id in ids else 0

    selected_label = st.selectbox("Select Contract", list(options.keys()), index=default_idx)
    selected_id = options[selected_label]
    st.session_state.current_contract_id = selected_id

    # ── Filters ───────────────────────────────────────────────
    st.divider()
    fcol1, fcol2, fcol3, fcol4 = st.columns([2, 2, 2, 2])

    with fcol1:
        risk_filter = st.selectbox(
            "Filter by Risk Level",
            ["All", "critical", "high", "medium", "low"],
        )
    with fcol2:
        flagged_only = st.checkbox("Flagged Clauses Only", value=False)
    with fcol3:
        search_text = st.text_input("Search in Clause Text", placeholder="e.g. indemnify")
    with fcol4:
        sort_by = st.selectbox("Sort by", ["Clause Order", "Risk Score (High→Low)", "Risk Score (Low→High)"])

    # ── Load clauses ──────────────────────────────────────────
    try:
        risk_level = risk_filter if risk_filter != "All" else None
        clauses = client.get_clauses(
            selected_id,
            risk_level=risk_level,
            flagged_only=flagged_only,
        )
    except Exception as e:
        st.error(f"Could not load clauses: {e}")
        return

    # Search filter
    if search_text:
        clauses = [c for c in clauses if search_text.lower() in c.get("text", "").lower()]

    # Sort
    if sort_by == "Risk Score (High→Low)":
        clauses.sort(key=lambda c: c.get("risk_score", 0), reverse=True)
    elif sort_by == "Risk Score (Low→High)":
        clauses.sort(key=lambda c: c.get("risk_score", 0))

    # ── Stats bar ─────────────────────────────────────────────
    st.markdown(f"**Showing {len(clauses)} clause(s)**")

    if clauses:
        avg_score = sum(c.get("risk_score", 0) for c in clauses) / len(clauses)
        flagged_count = sum(1 for c in clauses if c.get("is_flagged"))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Shown", len(clauses))
        m2.metric("Avg Risk", f"{avg_score:.1f}/10")
        m3.metric("Flagged", flagged_count)
        m4.metric(
            "Critical",
            sum(1 for c in clauses if c.get("risk_level") == "critical"),
        )

    st.divider()

    # ── Clause list ───────────────────────────────────────────
    if not clauses:
        st.info("No clauses match the current filters.")
        return

    # Batch expand controls
    expand_col1, expand_col2 = st.columns([1, 3])
    with expand_col1:
        auto_expand_flagged = st.checkbox("Auto-expand flagged", value=False)

    for clause in clauses:
        is_critical = clause.get("risk_level") in ("critical", "high")
        expand = auto_expand_flagged and clause.get("is_flagged", False)
        render_clause_card(clause, expanded=expand)
