"""
LexiScan — Reusable Streamlit UI Components
"""

from typing import Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

from backend.utils.risk_categories import RISK_COLORS, RISK_EMOJIS


# ── Risk Badge ────────────────────────────────────────────────

def risk_badge(level: str) -> str:
    """Return HTML risk badge."""
    emoji = RISK_EMOJIS.get(level, "⚪")
    return f'<span class="badge-{level}">{emoji} {level.upper()}</span>'


def render_risk_gauge(score: float, title: str = "Overall Risk Score") -> go.Figure:
    """Plotly gauge chart for risk score."""
    color = (
        RISK_COLORS["critical"] if score >= 8.5
        else RISK_COLORS["high"] if score >= 6.0
        else RISK_COLORS["medium"] if score >= 3.0
        else RISK_COLORS["low"]
    )

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 16}},
        number={"suffix": "/10", "font": {"size": 32, "color": color}},
        gauge={
            "axis": {"range": [0, 10], "tickwidth": 1, "tickcolor": "#64748b"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#e2e8f0",
            "steps": [
                {"range": [0, 3], "color": "#dcfce7"},
                {"range": [3, 6], "color": "#fef9c3"},
                {"range": [6, 8.5], "color": "#ffedd5"},
                {"range": [8.5, 10], "color": "#fee2e2"},
            ],
            "threshold": {
                "line": {"color": color, "width": 4},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


# ── Risk Distribution Chart ───────────────────────────────────

def render_risk_distribution(distribution: Dict[str, int]) -> go.Figure:
    """Horizontal bar chart of clause risk distribution."""
    levels = ["critical", "high", "medium", "low"]
    counts = [distribution.get(l, 0) for l in levels]
    colors = [RISK_COLORS[l] for l in levels]
    labels = [f"{RISK_EMOJIS[l]} {l.capitalize()}" for l in levels]

    fig = go.Figure(go.Bar(
        x=counts,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=counts,
        textposition="outside",
        hovertemplate="%{y}: %{x} clauses<extra></extra>",
    ))
    fig.update_layout(
        title="Risk Distribution by Clause",
        height=220,
        margin=dict(l=20, r=40, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"gridcolor": "#f1f5f9", "title": "Number of Clauses"},
        yaxis={"gridcolor": "#f1f5f9"},
        font={"family": "Inter, sans-serif", "size": 13},
    )
    return fig


# ── Category Breakdown ────────────────────────────────────────

def render_category_chart(top_categories: List[Dict]) -> go.Figure:
    """Horizontal bar of top risk categories."""
    if not top_categories:
        return None

    cats = [c["category"] for c in top_categories]
    counts = [c["count"] for c in top_categories]

    fig = go.Figure(go.Bar(
        x=counts,
        y=cats,
        orientation="h",
        marker_color="#6366f1",
        text=counts,
        textposition="outside",
    ))
    fig.update_layout(
        title="Top Risk Categories Detected",
        height=max(200, len(cats) * 30 + 80),
        margin=dict(l=20, r=40, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"gridcolor": "#f1f5f9", "title": "Occurrences"},
        yaxis={"gridcolor": "#f1f5f9", "autorange": "reversed"},
        font={"family": "Inter, sans-serif", "size": 12},
    )
    return fig


# ── Clause Card ───────────────────────────────────────────────

def render_clause_card(clause: Dict, expanded: bool = False):
    """Render a single clause with risk info."""
    level = clause.get("risk_level", "low")
    score = clause.get("risk_score", 0.0)
    heading = clause.get("heading") or f"Clause {clause.get('clause_index', 0) + 1}"
    color = RISK_COLORS[level]
    emoji = RISK_EMOJIS[level]

    with st.expander(
        f"{emoji} **{heading}** — Risk Score: {score:.1f}/10",
        expanded=expanded,
    ):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Clause Text:**")
            # Highlight risk tokens if available
            text = clause.get("text", "")
            top_tokens = [t["token"] for t in clause.get("top_risk_tokens", [])]
            if top_tokens:
                highlighted = _highlight_tokens(text, top_tokens)
                st.markdown(highlighted, unsafe_allow_html=True)
            else:
                st.markdown(f"> {text[:800]}{'...' if len(text) > 800 else ''}")

        with col2:
            st.markdown(f"**Risk Level:**")
            st.markdown(risk_badge(level), unsafe_allow_html=True)
            st.markdown(f"**Score:** `{score:.1f}/10`")
            st.markdown(f"**Confidence:** `{clause.get('confidence', 0):.0%}`")

            if clause.get("page_number"):
                st.markdown(f"**Page:** {clause['page_number']}")

        # Risk categories
        cats = clause.get("risk_categories", [])
        if cats:
            st.markdown("**Detected Risk Categories:**")
            cat_html = " ".join(
                f'<span style="background:#f1f5f9;border-radius:4px;padding:2px 8px;'
                f'font-size:12px;margin:2px;">{c.get("label", c.get("category","?"))}</span>'
                for c in cats[:6]
            )
            st.markdown(cat_html, unsafe_allow_html=True)

        # Explanation
        if clause.get("explanation"):
            st.info(f"💡 {clause['explanation']}")

        # Token attribution
        top_tokens_full = clause.get("top_risk_tokens", [])
        if top_tokens_full:
            st.markdown("**Key Risk Tokens:**")
            token_cols = st.columns(min(len(top_tokens_full), 5))
            for i, tok in enumerate(top_tokens_full[:5]):
                with token_cols[i]:
                    score_pct = int(tok.get("score", 0) * 100)
                    st.markdown(
                        f'<div style="text-align:center;padding:4px 8px;background:#fef3c7;'
                        f'border-radius:6px;font-size:13px;">'
                        f'<strong>{tok["token"]}</strong><br>'
                        f'<small style="color:#92400e">{score_pct}%</small></div>',
                        unsafe_allow_html=True,
                    )


def _highlight_tokens(text: str, tokens: List[str]) -> str:
    """Highlight risk tokens in text."""
    import re
    result = text[:800]
    if len(text) > 800:
        result += "..."

    for token in tokens:
        if len(token) < 3:
            continue
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        result = pattern.sub(
            f'<mark style="background:#fef3c7;border-bottom:2px solid #f59e0b;'
            f'padding:0 2px;border-radius:2px;">{token}</mark>',
            result,
        )

    return f"<div style='font-size:14px;line-height:1.7;'>{result}</div>"


# ── Entity Table ──────────────────────────────────────────────

def render_entity_table(entities: List[Dict]):
    """Display entities as a styled table."""
    import pandas as pd

    if not entities:
        st.info("No entities extracted.")
        return

    # Group by type
    type_icons = {
        "PARTY": "👤",
        "DATE": "📅",
        "MONEY": "💰",
        "ORG": "🏢",
        "GPE": "🌍",
        "LAW": "📜",
        "OBLIGATION": "✅",
        "JURISDICTION": "⚖️",
        "DURATION": "⏱️",
        "PERCENT": "%",
    }

    rows = []
    for e in entities[:100]:  # cap at 100
        rows.append({
            "Type": f"{type_icons.get(e['entity_type'], '❓')} {e['entity_type']}",
            "Value": e["text"][:80],
            "Normalized": (e.get("normalized") or "")[:60],
            "Confidence": f"{e.get('confidence', 1.0):.0%}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Summary Card ──────────────────────────────────────────────

def render_summary_card(summary: str, overall_score: float):
    """Render analysis summary."""
    level = (
        "critical" if overall_score >= 8.5
        else "high" if overall_score >= 6.0
        else "medium" if overall_score >= 3.0
        else "low"
    )
    color = RISK_COLORS[level]
    emoji = RISK_EMOJIS[level]

    st.markdown(
        f"""
        <div style="border:2px solid {color};border-radius:12px;padding:20px;
                    background:linear-gradient(135deg,#f8fafc,white);">
            <h3 style="color:{color};margin:0 0 8px;">{emoji} Executive Summary</h3>
            <p style="margin:0;font-size:15px;line-height:1.6;">{summary}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Diff Viewer ───────────────────────────────────────────────

def render_inline_diff(diff_parts: List[Dict]):
    """Render word-level inline diff."""
    html_parts = []
    for part in diff_parts:
        text = part.get("text", "")
        ptype = part.get("type", "equal")
        if ptype == "added":
            html_parts.append(
                f'<span style="background:#dcfce7;color:#166534;padding:1px 2px;'
                f'border-radius:2px;"><ins>{text}</ins></span>'
            )
        elif ptype == "removed":
            html_parts.append(
                f'<span style="background:#fee2e2;color:#991b1b;padding:1px 2px;'
                f'border-radius:2px;text-decoration:line-through;">{text}</span>'
            )
        else:
            html_parts.append(text)

    html = " ".join(html_parts)
    st.markdown(
        f'<div style="font-size:14px;line-height:1.8;padding:12px;'
        f'background:#f8fafc;border-radius:8px;">{html}</div>',
        unsafe_allow_html=True,
    )
