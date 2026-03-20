"""
LexiScan — Streamlit Frontend Entry Point
Multi-page app with sidebar navigation.
"""

import streamlit as st

# ── Page Config (must be first Streamlit call) ────────────────
st.set_page_config(
    page_title="LexiScan — Legal Risk Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
/* Main theme */
:root {
    --risk-critical: #ef4444;
    --risk-high: #f97316;
    --risk-medium: #f59e0b;
    --risk-low: #22c55e;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Risk badges */
.badge-critical { background:#ef4444; color:white; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
.badge-high     { background:#f97316; color:white; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
.badge-medium   { background:#f59e0b; color:white; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
.badge-low      { background:#22c55e; color:white; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }

/* Risk score gauge */
.risk-score-big { font-size:56px; font-weight:800; line-height:1; }

/* Clause card */
.clause-card {
    border-left: 4px solid #334155;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
    background: #f8fafc;
}
.clause-card.critical { border-left-color: #ef4444; }
.clause-card.high     { border-left-color: #f97316; }
.clause-card.medium   { border-left-color: #f59e0b; }
.clause-card.low      { border-left-color: #22c55e; }

/* Token highlight */
.token-risk {
    background: #fef3c7;
    border-bottom: 2px solid #f59e0b;
    padding: 0 2px;
    border-radius: 2px;
}

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.metric-card .value { font-size:36px; font-weight:800; }
.metric-card .label { font-size:13px; color:#64748b; margin-top:4px; }
</style>
""", unsafe_allow_html=True)


# ── Navigation ────────────────────────────────────────────────

def sidebar_nav():
    with st.sidebar:
        st.markdown("## ⚖️ LexiScan")
        st.markdown("*Legal Document Risk Analyzer*")
        st.divider()

        page = st.radio(
            "Navigation",
            options=[
                "📤 Upload & Analyze",
                "📊 Dashboard",
                "🔍 Clause Explorer",
                "🔄 Compare Contracts",
                "📋 Contract History",
                "ℹ️ About",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.markdown("**Quick Stats**")
        # These would normally come from the API
        if "analysis_result" in st.session_state:
            result = st.session_state.analysis_result
            stats = result.get("stats", {})
            st.metric("Clauses Analyzed", stats.get("total_clauses", 0))
            st.metric("Flagged", stats.get("flagged_clauses", 0))
            score = result.get("overall_risk_score", 0)
            st.metric("Overall Risk", f"{score:.1f}/10")

        st.divider()
        st.caption("v1.0.0 | Powered by LegalBERT + CUAD")

    return page


def main():
    page = sidebar_nav()

    if page == "📤 Upload & Analyze":
        from frontend.pages import upload
        upload.render()
    elif page == "📊 Dashboard":
        from frontend.pages import dashboard
        dashboard.render()
    elif page == "🔍 Clause Explorer":
        from frontend.pages import clause_explorer
        clause_explorer.render()
    elif page == "🔄 Compare Contracts":
        from frontend.pages import compare
        compare.render()
    elif page == "📋 Contract History":
        from frontend.pages import history
        history.render()
    elif page == "ℹ️ About":
        from frontend.pages import about
        about.render()


if __name__ == "__main__":
    main()
