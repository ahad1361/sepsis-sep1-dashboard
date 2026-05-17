"""Plotly chart builders for the SEP-1 Sepsis Hospital Quality Dashboard."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── colour palette ────────────────────────────────────────────────────────────
_C = {
    "excellent": "#2ecc71",
    "moderate": "#f39c12",
    "poor": "#e74c3c",
    "no_data": "#7f8c8d",
    "ref_line": "#3498db",
    "bar": "#5b9bd5",
}

CATEGORY_COLORS: dict[str, str] = {
    "Excellent (≥80%)": _C["excellent"],
    "Moderate (50–79%)": _C["moderate"],
    "Poor (<50%)": _C["poor"],
    "No Data": _C["no_data"],
}

_TEMPLATE = "plotly_dark"
_TRANSPARENT = "rgba(0,0,0,0)"


# ── helpers ───────────────────────────────────────────────────────────────────

def _hover_text(df: pd.DataFrame) -> list[str]:
    """Build HTML hover strings for each row in *df*."""
    names = df.get("facility_name", pd.Series(["Unknown"] * len(df), index=df.index)).fillna("Unknown")
    cities = df.get("city", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)
    states = df.get("state", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)

    scores = (
        df["score"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "Not Reported")
        if "score" in df.columns
        else pd.Series(["N/A"] * len(df), index=df.index)
    )
    samples = (
        df["denominator"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
        if "denominator" in df.columns
        else pd.Series(["N/A"] * len(df), index=df.index)
    )
    approx = (
        df["coords_approximated"].apply(lambda x: " ⚠ approx location" if x else "")
        if "coords_approximated" in df.columns
        else pd.Series([""] * len(df), index=df.index)
    )

    return (
        "<b>" + names + "</b><br>"
        + cities + ", " + states + approx + "<br>"
        + "SEP-1 Score: " + scores + "<br>"
        + "Sample Size: " + samples
    ).tolist()


# ── public chart functions ────────────────────────────────────────────────────

def create_hospital_map(
    df: pd.DataFrame,
    state_df: pd.DataFrame,
    selected_states: Optional[list[str]] = None,
    min_sample: int = 0,
) -> go.Figure:
    """Scatter geo map — one dot per hospital, colour-coded by SEP-1 tier.

    Args:
        df: Hospital-level SEP_1 DataFrame with lat/lng columns.
        state_df: State-level aggregates (not currently plotted but reserved for choropleth overlay).
        selected_states: When provided, only these states are displayed.
        min_sample: Hospitals with denominator below this value are excluded.

    Returns:
        Plotly Figure.
    """
    plot_df = df.copy()
    if selected_states:
        plot_df = plot_df[plot_df["state"].isin(selected_states)]
    if min_sample > 0 and "denominator" in plot_df.columns:
        plot_df = plot_df[plot_df["denominator"].fillna(0) >= min_sample]

    scored = plot_df[plot_df["score"].notna()]
    unscored = plot_df[plot_df["score"].isna()]

    fig = go.Figure()

    # Layer 1: State choropleth background (colour = state average SEP-1 score)
    display_state_df = (
        state_df[state_df["state"].isin(selected_states)]
        if selected_states
        else state_df
    )
    if not display_state_df.empty:
        fig.add_trace(go.Choropleth(
            locations=display_state_df["state"],
            z=display_state_df["avg_score"],
            locationmode="USA-states",
            colorscale=[
                [0.00, "#7f1d1d"],
                [0.25, "#e74c3c"],
                [0.50, "#f39c12"],
                [0.75, "#2ecc71"],
                [1.00, "#065f46"],
            ],
            zmin=0,
            zmax=100,
            colorbar=dict(
                title=dict(text="State Avg<br>SEP-1 (%)", font=dict(size=11)),
                thickness=14,
                len=0.55,
                x=1.01,
                ticksuffix="%",
                bgcolor="rgba(14,17,23,0.7)",
            ),
            hovertemplate=(
                "<b>%{location}</b><br>"
                "State avg SEP-1: %{z:.1f}%<br>"
                "<i>Click to filter</i><extra></extra>"
            ),
            showlegend=False,
            name="State Average",
        ))

    # Layer 2: Hospitals with no reported score (grey dots)
    if not unscored.empty:
        fig.add_trace(go.Scattergeo(
            lat=unscored["lat"],
            lon=unscored["lng"],
            mode="markers",
            marker=dict(size=4, color=_C["no_data"], opacity=0.35),
            text=_hover_text(unscored),
            customdata=unscored["state"].values if "state" in unscored.columns else None,
            hoverinfo="text",
            name="No Data",
        ))

    # Layer 3: Scored hospitals grouped by compliance tier
    for category in ["Poor (<50%)", "Moderate (50–79%)", "Excellent (≥80%)"]:
        if "score_category" not in scored.columns:
            continue
        cat_df = scored[scored["score_category"] == category]
        if cat_df.empty:
            continue
        fig.add_trace(go.Scattergeo(
            lat=cat_df["lat"],
            lon=cat_df["lng"],
            mode="markers",
            marker=dict(
                size=8,
                color=CATEGORY_COLORS[category],
                opacity=0.85,
                line=dict(width=0.6, color="white"),
            ),
            text=_hover_text(cat_df),
            customdata=cat_df["state"].values if "state" in cat_df.columns else None,
            hoverinfo="text",
            name=category,
        ))

    fig.update_layout(
        title=dict(
            text="Hospital SEP-1 Compliance — Click a state to filter",
            font=dict(size=15),
        ),
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showland=True,
            landcolor="#1a2035",
            showlakes=True,
            lakecolor="#0d1b2a",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#2d3748",
            showsubunits=True,
            subunitcolor="#2d3748",
            bgcolor=_TRANSPARENT,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.02,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(14,17,23,0.7)",
            bordercolor="#2d3748",
            borderwidth=1,
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        template=_TEMPLATE,
        height=580,
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
    )
    return fig


def create_state_bar_chart(state_df: pd.DataFrame, national_avg: float) -> go.Figure:
    """Horizontal bar chart of state SEP-1 averages ranked against the national mean.

    Args:
        state_df: State-level DataFrame with columns state, avg_score.
        national_avg: National average score (percentage, 0–100).

    Returns:
        Plotly Figure.
    """
    df = state_df.copy().sort_values("avg_score")

    colors = [
        _C["excellent"] if s >= 80 else (_C["moderate"] if s >= 50 else _C["poor"])
        for s in df["avg_score"]
    ]

    fig = go.Figure(go.Bar(
        x=df["avg_score"],
        y=df["state"],
        orientation="h",
        marker_color=colors,
        text=df["avg_score"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Avg SEP-1: %{x:.1f}%<extra></extra>",
    ))

    fig.add_vline(x=national_avg, line_dash="dash", line_color=_C["ref_line"], line_width=1.5)
    # Annotation placed above the plot area so it never overlaps bars
    fig.add_annotation(
        x=national_avg,
        xref="x",
        y=1.0,
        yref="paper",
        text=f"▼ Natl avg: {national_avg:.1f}%",
        showarrow=False,
        font=dict(color=_C["ref_line"], size=11),
        xanchor="center",
        yanchor="bottom",
        bgcolor="rgba(14,17,23,0.88)",
        bordercolor=_C["ref_line"],
        borderwidth=1,
        borderpad=5,
    )

    chart_height = min(max(380, len(df) * 22), 1400)
    fig.update_layout(
        title=dict(text="State SEP-1 Average Compliance Rates", font=dict(size=14)),
        xaxis=dict(title="Average SEP-1 Score (%)", range=[0, 108]),
        yaxis_title=None,
        template=_TEMPLATE,
        height=chart_height,
        margin=dict(l=20, r=70, t=75, b=40),
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
        showlegend=False,
    )
    return fig


def create_score_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of SEP-1 score distribution across all hospitals.

    Args:
        df: Hospital-level DataFrame with 'score' column.

    Returns:
        Plotly Figure.
    """
    scored = df.loc[df["score"].notna(), "score"]

    fig = px.histogram(
        scored,
        nbins=30,
        color_discrete_sequence=[_C["bar"]],
        labels={"value": "SEP-1 Score (%)", "count": "Hospitals"},
        title="Distribution of Hospital SEP-1 Scores",
    )
    fig.update_traces(hovertemplate="Score: %{x:.0f}%<br>Hospitals: %{y}<extra></extra>")

    for threshold, color, label in [
        (50, _C["poor"], "50%"),
        (80, _C["excellent"], "80%"),
    ]:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color=color,
            annotation_text=label,
            annotation_position="top",
            annotation_font_color=color,
        )

    fig.update_layout(
        template=_TEMPLATE,
        height=360,
        margin=dict(l=20, r=20, t=50, b=40),
        paper_bgcolor=_TRANSPARENT,
        plot_bgcolor=_TRANSPARENT,
        showlegend=False,
        xaxis_title="SEP-1 Score (%)",
        yaxis_title="Number of Hospitals",
    )
    return fig


def create_top_bottom_table(
    df: pd.DataFrame, n: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the top-N and bottom-N hospitals by SEP-1 score.

    Args:
        df: Hospital-level DataFrame.
        n: Number of hospitals to include in each list.

    Returns:
        (top_df, bottom_df) formatted for Streamlit display.
    """
    scored = df[df["score"].notna()].copy()

    col_map = {
        "facility_name": "Hospital",
        "city": "City",
        "state": "State",
        "score": "SEP-1 Score (%)",
        "denominator": "Sample Size",
    }
    keep = [c for c in col_map if c in scored.columns]

    def _format(sub: pd.DataFrame) -> pd.DataFrame:
        out = sub[keep].rename(columns=col_map).reset_index(drop=True)
        out.index += 1
        if "SEP-1 Score (%)" in out.columns:
            out["SEP-1 Score (%)"] = out["SEP-1 Score (%)"].apply(lambda x: f"{x:.1f}%")
        if "Sample Size" in out.columns:
            out["Sample Size"] = out["Sample Size"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
            )
        return out

    return _format(scored.nlargest(n, "score")), _format(scored.nsmallest(n, "score"))
