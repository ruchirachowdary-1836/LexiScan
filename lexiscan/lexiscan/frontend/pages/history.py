"""
LexiScan — Contract History Page
"""

import streamlit as st
import pandas as pd

from frontend.utils.api_client import get_client
from backend.utils.risk_categories import RISK_COLORS, RISK_EMOJIS


def render():
    st.title("📋 Contract History")
    st.markdown("All previously analyzed contracts.")

    client = get_client()

    try:
        contracts = client.list_contracts()
    except Exception as e:
        st.error(f"Cannot load contracts: {e}")
        return

    if not contracts:
        st.info("No contracts analyzed yet. Head to **Upload & Analyze** to get started.")
        return

    # ── Summary metrics ───────────────────────────────────────
    avg_risk = sum(c["overall_risk_score"] for c in contracts) / len(contracts)
    high_risk = sum(1 for c in contracts if c["overall_risk_score"] >= 6.0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Contracts", len(contracts))
    m2.metric("Avg Risk Score", f"{avg_risk:.1f}/10")
    m3.metric("High/Critical Risk", high_risk)

    st.divider()

    # ── Table ─────────────────────────────────────────────────
    rows = []
    for c in contracts:
        score = c["overall_risk_score"]
        level = (
            "critical" if score >= 8.5
            else "high" if score >= 6.0
            else "medium" if score >= 3.0
            else "low"
        )
        rows.append({
            "Name": c["name"],
            "Risk": f"{RISK_EMOJIS[level]} {score:.1f}/10",
            "Status": c["status"],
            "Pages": c.get("page_count", "—"),
            "Uploaded": (c.get("uploaded_at") or "")[:10],
            "Analyzed": (c.get("analyzed_at") or "")[:10],
            "_id": c["id"],
            "_score": score,
            "_level": level,
        })

    df = pd.DataFrame(rows)

    # Filter
    filter_col1, filter_col2 = st.columns([2, 2])
    with filter_col1:
        risk_filter = st.selectbox("Filter by Risk", ["All", "critical", "high", "medium", "low"])
    with filter_col2:
        search = st.text_input("Search by name", placeholder="Search...")

    display_df = df.copy()
    if risk_filter != "All":
        display_df = display_df[display_df["_level"] == risk_filter]
    if search:
        display_df = display_df[display_df["Name"].str.contains(search, case=False)]

    # Show
    st.dataframe(
        display_df[["Name", "Risk", "Status", "Pages", "Uploaded", "Analyzed"]],
        use_container_width=True,
        hide_index=True,
    )

    # ── Actions ───────────────────────────────────────────────
    st.divider()
    st.subheader("Actions")

    selected_name = st.selectbox("Select contract for actions", [c["name"] for c in contracts])
    selected_contract = next((c for c in contracts if c["name"] == selected_name), None)

    if selected_contract:
        acol1, acol2, acol3 = st.columns(3)
        with acol1:
            if st.button("📊 Open in Dashboard", use_container_width=True):
                st.session_state.current_contract_id = selected_contract["id"]
                st.info("Go to Dashboard tab to view this contract.")
        with acol2:
            if st.button("🔍 Open in Clause Explorer", use_container_width=True):
                st.session_state.current_contract_id = selected_contract["id"]
                st.info("Go to Clause Explorer tab to view clauses.")
        with acol3:
            if st.button("🗑️ Delete Contract", type="secondary", use_container_width=True):
                try:
                    client.delete_contract(selected_contract["id"])
                    st.success(f"Deleted '{selected_contract['name']}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")
