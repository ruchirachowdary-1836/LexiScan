"""
LexiScan — Upload & Analyze Page
"""

import time
import streamlit as st

from frontend.components.widgets import (
    render_risk_gauge,
    render_summary_card,
    render_risk_distribution,
    render_category_chart,
    risk_badge,
)
from frontend.utils.api_client import get_client
from backend.utils.risk_categories import RISK_COLORS, RISK_EMOJIS


def render():
    st.title("📤 Upload & Analyze Contract")
    st.markdown("Upload a PDF contract for instant AI-powered risk analysis.")

    # ── Check backend connectivity ────────────────────────────
    client = get_client()
    try:
        client.health_check()
        st.success("✅ Backend connected", icon="🔗")
    except ConnectionError:
        st.error(
            "⚠️ Cannot connect to LexiScan backend. "
            "Start the API with: `uvicorn backend.api.main:app --reload --port 8000`"
        )
        _demo_mode()
        return

    # ── Upload Form ───────────────────────────────────────────
    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Choose a PDF contract",
            type=["pdf"],
            help="Max file size: 50MB. Best results with text-based PDFs (not scanned).",
        )

    with col2:
        contract_name = st.text_input(
            "Contract Name (optional)",
            placeholder="e.g. Vendor Agreement 2024",
        )
        analyze_btn = st.button(
            "🚀 Analyze Contract",
            type="primary",
            disabled=uploaded_file is None,
            use_container_width=True,
        )

    if uploaded_file and analyze_btn:
        _run_analysis(client, uploaded_file, contract_name or uploaded_file.name)

    # ── Show previous result if exists ───────────────────────
    if "analysis_result" in st.session_state and not analyze_btn:
        _render_results(st.session_state.analysis_result, st.session_state.get("analysis_detail"))


def _run_analysis(client, uploaded_file, contract_name: str):
    """Run analysis with progress bar."""
    progress_bar = st.progress(0, text="Reading PDF...")
    status = st.empty()

    try:
        file_bytes = uploaded_file.read()

        progress_bar.progress(20, text="Uploading to analyzer...")
        time.sleep(0.3)

        progress_bar.progress(40, text="Segmenting clauses...")
        result = client.analyze_contract(
            file_bytes=file_bytes,
            filename=uploaded_file.name,
            contract_name=contract_name,
        )
        progress_bar.progress(70, text="Classifying risk...")
        time.sleep(0.3)

        # Fetch full analysis
        contract_id = result["contract_id"]
        detail = client.get_analysis(contract_id)
        progress_bar.progress(90, text="Generating summary...")
        time.sleep(0.2)
        progress_bar.progress(100, text="Done!")
        time.sleep(0.3)
        progress_bar.empty()
        status.empty()

        # Store in session
        st.session_state.analysis_result = result
        st.session_state.analysis_detail = detail
        st.session_state.current_contract_id = contract_id

        st.success(f"✅ Analysis complete! Contract ID: `{contract_id}`")
        _render_results(result, detail)

    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ Analysis failed: {e}")


def _render_results(result: dict, detail: dict):
    """Render full analysis results."""
    st.divider()
    st.subheader("📊 Analysis Results")

    # ── Top row metrics ───────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    score = result.get("overall_risk_score", 0.0)
    stats = result.get("stats", {})
    dist = stats.get("risk_distribution", {})

    col1.metric("Overall Risk", f"{score:.1f}/10")
    col2.metric("Total Clauses", stats.get("total_clauses", "—"))
    col3.metric("🔴 Critical", dist.get("critical", 0))
    col4.metric("🟠 High Risk", dist.get("high", 0))
    col5.metric("⚑ Flagged", stats.get("flagged_clauses", 0))

    st.divider()

    # ── Summary ───────────────────────────────────────────────
    summary = result.get("summary", "")
    if summary:
        render_summary_card(summary, score)

    st.markdown("")

    # ── Charts ────────────────────────────────────────────────
    chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 1])

    with chart_col1:
        fig = render_risk_gauge(score)
        st.plotly_chart(fig, use_container_width=True, key="gauge_upload")

    with chart_col2:
        if dist:
            fig2 = render_risk_distribution(dist)
            st.plotly_chart(fig2, use_container_width=True, key="dist_upload")

    with chart_col3:
        top_cats = stats.get("top_risk_categories", [])
        if top_cats:
            fig3 = render_category_chart(top_cats[:6])
            if fig3:
                st.plotly_chart(fig3, use_container_width=True, key="cats_upload")

    # ── Parties ───────────────────────────────────────────────
    parties = result.get("parties", [])
    if parties:
        st.markdown("**👤 Identified Parties:**")
        for p in parties[:5]:
            st.markdown(f"• {p}")

    # ── Navigation hint ───────────────────────────────────────
    st.info(
        "📌 Go to **Clause Explorer** to browse all clauses with risk details, "
        "or **Dashboard** for full analytics."
    )


def _demo_mode():
    """Show demo results when backend is unavailable."""
    st.info("📎 Running in Demo Mode — showing sample analysis results")

    demo_result = {
        "overall_risk_score": 7.2,
        "summary": (
            "⚠️ This contract contains high risk provisions. Risk score: 7.2/10. "
            "Parties: Acme Corp, Vendor LLC. "
            "Analyzed 42 clauses: 3 critical, 8 high, 14 total flagged."
        ),
        "stats": {
            "total_clauses": 42,
            "flagged_clauses": 14,
            "avg_risk_score": 4.8,
            "risk_distribution": {"low": 18, "medium": 13, "high": 8, "critical": 3},
            "top_risk_categories": [
                {"category": "Uncapped Liability", "count": 3},
                {"category": "Non-Compete", "count": 2},
                {"category": "Indemnification", "count": 4},
                {"category": "IP Ownership", "count": 2},
                {"category": "Termination for Convenience", "count": 3},
            ],
        },
        "parties": ["Acme Corporation, Inc.", "Vendor LLC"],
    }

    _render_results(demo_result, None)
