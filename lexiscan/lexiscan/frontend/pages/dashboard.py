"""
LexiScan — Dashboard Page
Full analytics view for an analyzed contract.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from frontend.components.widgets import (
    render_risk_gauge,
    render_risk_distribution,
    render_category_chart,
    render_entity_table,
    render_summary_card,
    risk_badge,
)
from frontend.utils.api_client import get_client
from backend.utils.risk_categories import RISK_COLORS


def render():
    st.title("📊 Contract Risk Dashboard")

    client = get_client()

    # ── Contract selection ────────────────────────────────────
    contract_id = st.session_state.get("current_contract_id")

    try:
        contracts = client.list_contracts()
    except Exception as e:
        st.error(f"Cannot load contracts: {e}")
        return

    if not contracts:
        st.info("No contracts analyzed yet. Go to **Upload & Analyze** to get started.")
        return

    options = {f"{c['name']} (score: {c['overall_risk_score']:.1f})": c["id"] for c in contracts}
    default_idx = 0
    if contract_id:
        ids = list(options.values())
        if contract_id in ids:
            default_idx = ids.index(contract_id)

    selected_label = st.selectbox("Select Contract", list(options.keys()), index=default_idx)
    selected_id = options[selected_label]
    st.session_state.current_contract_id = selected_id

    # ── Load analysis ─────────────────────────────────────────
    try:
        with st.spinner("Loading analysis..."):
            detail = client.get_analysis(selected_id)
    except Exception as e:
        st.error(f"Could not load analysis: {e}")
        return

    contract = detail["contract"]
    clauses = detail["clauses"]
    entities = detail["entities"]
    score = contract["overall_risk_score"]

    # ── Header ────────────────────────────────────────────────
    st.markdown(f"### {contract['name']}")
    col_meta = st.columns(4)
    col_meta[0].metric("Pages", contract.get("page_count", "—"))
    col_meta[1].metric("Clauses", detail["total_clauses"])
    col_meta[2].metric("Flagged", detail["flagged_clauses"])
    col_meta[3].metric(
        "File Size",
        f"{(contract.get('file_size',0)/1024):.0f} KB" if contract.get("file_size") else "—",
    )

    st.divider()

    # ── Summary ───────────────────────────────────────────────
    if clauses:
        dist = _compute_distribution(clauses)
        avg = sum(c["risk_score"] for c in clauses) / len(clauses)

        render_summary_card(
            f"Overall risk score {score:.1f}/10 | "
            f"{dist.get('critical',0)} critical, {dist.get('high',0)} high, "
            f"{dist.get('medium',0)} medium, {dist.get('low',0)} low risk clauses.",
            score,
        )
        st.markdown("")

    # ── Main charts ───────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        st.plotly_chart(render_risk_gauge(score), use_container_width=True, key="dash_gauge")

    with c2:
        if clauses:
            dist = _compute_distribution(clauses)
            st.plotly_chart(render_risk_distribution(dist), use_container_width=True, key="dash_dist")

    with c3:
        top_cats = _get_top_categories(clauses)
        if top_cats:
            fig = render_category_chart(top_cats[:8])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="dash_cats")

    st.divider()

    # ── Risk score scatter per clause ─────────────────────────
    if clauses:
        st.subheader("Risk Score by Clause")
        df = pd.DataFrame([
            {
                "Clause": f"#{c['clause_index']+1} {(c.get('heading') or '')[:30]}",
                "Risk Score": c["risk_score"],
                "Level": c["risk_level"],
                "Flagged": "⚑ Yes" if c.get("is_flagged") else "No",
            }
            for c in clauses
        ])

        color_map = {
            "critical": RISK_COLORS["critical"],
            "high": RISK_COLORS["high"],
            "medium": RISK_COLORS["medium"],
            "low": RISK_COLORS["low"],
        }

        fig_scatter = px.bar(
            df, x="Clause", y="Risk Score",
            color="Level", color_discrete_map=color_map,
            hover_data=["Flagged"],
            height=300,
        )
        fig_scatter.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis={"tickangle": -45, "tickfont": {"size": 10}},
            margin=dict(l=20, r=20, t=20, b=80),
            showlegend=True,
        )
        fig_scatter.add_hline(y=6.0, line_dash="dash", line_color=RISK_COLORS["high"],
                              annotation_text="High Risk Threshold")
        fig_scatter.add_hline(y=8.5, line_dash="dash", line_color=RISK_COLORS["critical"],
                              annotation_text="Critical Threshold")
        st.plotly_chart(fig_scatter, use_container_width=True, key="clause_bar")

    st.divider()

    # ── Entities ──────────────────────────────────────────────
    st.subheader("🏷️ Extracted Entities")

    if entities:
        # Filter controls
        entity_types = list(set(e["entity_type"] for e in entities))
        selected_types = st.multiselect(
            "Filter by entity type",
            entity_types,
            default=entity_types[:5],
        )
        filtered = [e for e in entities if e["entity_type"] in selected_types]
        render_entity_table(filtered)
    else:
        st.info("No entities extracted.")

    st.divider()

    # ── Flagged clauses table ─────────────────────────────────
    st.subheader("⚑ Flagged Clauses")
    flagged = [c for c in clauses if c.get("is_flagged")]

    if flagged:
        for c in flagged:
            level = c["risk_level"]
            heading = c.get("heading") or f"Clause {c['clause_index']+1}"
            with st.expander(
                f"{['🔴','🟠','🟡','🟢'][['critical','high','medium','low'].index(level)]} "
                f"**{heading}** — {c['risk_score']:.1f}/10"
            ):
                st.markdown(f"> {c['text'][:400]}{'...' if len(c['text'])>400 else ''}")
                st.caption(c.get("explanation",""))
    else:
        st.success("✅ No high-risk clauses flagged.")


def _compute_distribution(clauses):
    dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for c in clauses:
        dist[c.get("risk_level", "low")] = dist.get(c.get("risk_level","low"), 0) + 1
    return dist


def _get_top_categories(clauses):
    cat_count = {}
    for c in clauses:
        for cat in c.get("risk_categories", []):
            label = cat.get("label", cat.get("category", "?"))
            cat_count[label] = cat_count.get(label, 0) + 1
    return [
        {"category": k, "count": v}
        for k, v in sorted(cat_count.items(), key=lambda x: x[1], reverse=True)
    ]
