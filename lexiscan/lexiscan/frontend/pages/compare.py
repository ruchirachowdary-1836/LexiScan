"""
LexiScan — Compare Contracts Page
Side-by-side contract version comparison with diff and risk delta.
"""

import streamlit as st
import plotly.graph_objects as go

from frontend.components.widgets import render_inline_diff, risk_badge
from frontend.utils.api_client import get_client
from backend.utils.risk_categories import RISK_COLORS


def render():
    st.title("🔄 Compare Contracts")
    st.markdown(
        "Compare two contract versions to identify added/removed/modified clauses "
        "and track risk score changes."
    )

    client = get_client()

    try:
        contracts = client.list_contracts()
    except Exception as e:
        st.error(f"Cannot load contracts: {e}")
        return

    if len(contracts) < 2:
        st.warning("You need at least 2 analyzed contracts to compare.")
        st.info("Upload another version of your contract on the **Upload & Analyze** page.")
        return

    options = {f"{c['name']} (risk: {c['overall_risk_score']:.1f})": c["id"] for c in contracts}
    labels = list(options.keys())

    col1, col2 = st.columns(2)
    with col1:
        v1_label = st.selectbox("📄 Contract Version 1 (Baseline)", labels, index=0)
    with col2:
        v2_label = st.selectbox("📄 Contract Version 2 (New)", labels, index=min(1, len(labels)-1))

    v1_id = options[v1_label]
    v2_id = options[v2_label]

    if v1_id == v2_id:
        st.warning("Please select two different contracts to compare.")
        return

    if st.button("🔍 Compare Contracts", type="primary", use_container_width=True):
        with st.spinner("Comparing contracts..."):
            try:
                result = client.compare_contracts(v1_id, v2_id)
                st.session_state.compare_result = result
            except Exception as e:
                st.error(f"Comparison failed: {e}")
                return

    if "compare_result" not in st.session_state:
        return

    result = st.session_state.compare_result
    _render_comparison(result)


def _render_comparison(result: dict):
    """Render comparison results."""
    stats = result.get("stats", {})
    summary = result.get("summary", "")

    # ── Summary banner ────────────────────────────────────────
    risk_delta = stats.get("risk_delta", 0)
    delta_color = RISK_COLORS["high"] if risk_delta > 0 else RISK_COLORS["low"]
    arrow = "▲" if risk_delta > 0 else "▼"
    delta_sign = "+" if risk_delta > 0 else ""

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);
                    color:white;border-radius:12px;padding:20px;margin-bottom:16px;">
            <h3 style="margin:0 0 8px;color:white;">📊 Comparison Summary</h3>
            <p style="margin:0 0 12px;opacity:0.85;">{summary}</p>
            <span style="background:{delta_color};color:white;padding:4px 16px;
                         border-radius:99px;font-weight:700;font-size:18px;">
                {arrow} Risk {delta_sign}{risk_delta:.1f} pts
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Stats row ─────────────────────────────────────────────
    s = st.columns(6)
    s[0].metric("V1 Clauses", stats.get("total_clauses_v1", 0))
    s[1].metric("V2 Clauses", stats.get("total_clauses_v2", 0))
    s[2].metric("➕ Added", stats.get("added_count", 0))
    s[3].metric("➖ Removed", stats.get("removed_count", 0))
    s[4].metric("✏️ Modified", stats.get("modified_count", 0))
    s[5].metric("⚠️ New High-Risk", stats.get("new_high_risk_clauses", 0))

    # ── Risk comparison chart ─────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Version 1",
        x=["Avg Risk Score"],
        y=[stats.get("avg_risk_v1", 0)],
        marker_color="#6366f1",
        text=[f"{stats.get('avg_risk_v1', 0):.2f}"],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Version 2",
        x=["Avg Risk Score"],
        y=[stats.get("avg_risk_v2", 0)],
        marker_color=delta_color,
        text=[f"{stats.get('avg_risk_v2', 0):.2f}"],
        textposition="outside",
    ))
    fig.update_layout(
        barmode="group", height=200,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis={"range": [0, 10], "gridcolor": "#f1f5f9"},
    )
    st.plotly_chart(fig, use_container_width=True, key="risk_compare_bar")

    st.divider()

    # ── Tab view ──────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        f"➕ Added ({stats.get('added_count', 0)})",
        f"✏️ Modified ({stats.get('modified_count', 0)})",
        f"➖ Removed ({stats.get('removed_count', 0)})",
    ])

    with tab1:
        added = result.get("added_clauses", [])
        if not added:
            st.success("No new clauses added.")
        for c in added:
            level = c.get("risk_level", "low")
            heading = c.get("heading") or f"New Clause #{c.get('v2_index',0)+1}"
            with st.expander(f"➕ {heading} — Risk: {c.get('risk_score', 0):.1f}/10"):
                st.markdown(risk_badge(level), unsafe_allow_html=True)
                st.markdown(f"> {c['text'][:500]}")

    with tab2:
        modified = result.get("modified_clauses", [])
        if not modified:
            st.success("No clauses modified.")
        for c in modified:
            heading = c.get("heading") or f"Clause #{c.get('v1_index',0)+1}"
            delta = c.get("risk_delta", 0)
            delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
            delta_color_cls = "🔴" if delta > 1 else "🟢" if delta < -1 else "🟡"
            with st.expander(
                f"✏️ {heading} — Risk delta: {delta_color_cls} {delta_str}"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**V1 Risk:** `{c.get('risk_score_v1', 0):.1f}/10`")
                with col_b:
                    st.markdown(f"**V2 Risk:** `{c.get('risk_score_v2', 0):.1f}/10`")

                diff_parts = c.get("inline_diff", [])
                if diff_parts:
                    render_inline_diff(diff_parts)
                else:
                    st.text_area("V1 Text", c.get("text_v1", "")[:300], height=80)
                    st.text_area("V2 Text", c.get("text_v2", "")[:300], height=80)

    with tab3:
        removed = result.get("removed_clauses", [])
        if not removed:
            st.success("No clauses removed.")
        for c in removed:
            level = c.get("risk_level", "low")
            heading = c.get("heading") or f"Clause #{c.get('v1_index',0)+1}"
            with st.expander(f"➖ {heading}"):
                st.markdown(risk_badge(level), unsafe_allow_html=True)
                st.markdown(f"> {c['text'][:400]}")

    # ── New high-risk warning ─────────────────────────────────
    new_high = result.get("new_high_risk_clauses", [])
    if new_high:
        st.divider()
        st.error(f"⚠️ {len(new_high)} NEW HIGH/CRITICAL RISK CLAUSE(S) DETECTED in Version 2")
        for c in new_high:
            st.markdown(f"• **{c.get('heading', 'Unnamed')}** — Risk: {c.get('risk_score',0):.1f}/10")
