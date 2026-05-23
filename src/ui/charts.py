"""Chart data preparation for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import altair as alt
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def alert_counts_by_day(alerts: pd.DataFrame) -> pd.DataFrame:
    """Return alert counts by day and type."""
    if alerts.empty:
        return pd.DataFrame(columns=["date", "alert_type", "count"])
    frame = alerts.copy()
    frame["date"] = pd.to_datetime(frame["start_time"], utc=True).dt.date
    return (
        frame.groupby(["date", "alert_type"], dropna=False)
        .size()
        .reset_index(name="count")
    )


def severity_counts(alerts: pd.DataFrame) -> pd.DataFrame:
    """Return alert counts by severity."""
    if alerts.empty:
        return pd.DataFrame(columns=["severity", "count"])
    return alerts.groupby("severity", dropna=False).size().reset_index(name="count")


def severity_bar_chart(severity_data: pd.DataFrame) -> alt.Chart:
    """Build a severity bar chart with horizontal x-axis labels."""
    return (
        alt.Chart(severity_data)
        .mark_bar(color="#00B4D8")
        .encode(
            x=alt.X(
                "severity:N",
                sort=["Low", "Medium", "High", "Critical"],
                axis=alt.Axis(labelAngle=0, title="Severity"),
            ),
            y=alt.Y("count:Q", axis=alt.Axis(title="Alerts")),
            tooltip=["severity:N", "count:Q"],
        )
        .properties(height=280)
    )


def selected_symbol_candles(candles: pd.DataFrame, symbol: str | None) -> pd.DataFrame:
    """Return timestamp-indexed candles for one selected symbol."""
    if candles.empty:
        return pd.DataFrame()
    frame = candles.copy()
    selected_symbol = _selected_or_first_symbol(frame, symbol)
    if selected_symbol and "symbol" in frame:
        frame = frame[frame["symbol"] == selected_symbol]
    if frame.empty:
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp").set_index("timestamp")


def price_volume_dual_axis_chart(
    symbol_candles: pd.DataFrame, selected_symbol: str | None = None
) -> go.Figure:
    """Build a dual-axis price and volume chart for one symbol."""
    chart_data = symbol_candles.reset_index()
    resolved_symbol = _selected_or_first_symbol(chart_data, selected_symbol)
    if resolved_symbol and "symbol" in chart_data:
        chart_data = chart_data[chart_data["symbol"] == resolved_symbol]
    chart_data = chart_data.sort_values("timestamp")
    chart_data["timestamp"] = pd.to_datetime(chart_data["timestamp"], utc=True)
    chart_data["close"] = pd.to_numeric(chart_data["close"], errors="coerce")
    chart_data["volume"] = pd.to_numeric(chart_data["volume"], errors="coerce")
    price_data = chart_data[chart_data["close"].notna() & (chart_data["close"] >= 1)]
    latest_timestamp = chart_data["timestamp"].max()
    last_3h_start = latest_timestamp - pd.Timedelta(hours=3)
    visible_volume = chart_data[
        (chart_data["timestamp"] >= last_3h_start)
        & (chart_data["timestamp"] <= latest_timestamp)
    ]["volume"]
    visible_max_volume = visible_volume.max()
    volume_axis_max = 0 if pd.isna(visible_max_volume) else float(visible_max_volume) * 2.5

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=price_data["timestamp"],
            y=price_data["close"],
            mode="lines",
            name="Price",
            line={"color": "#00B4D8", "width": 1.5},
            connectgaps=False,
            hovertemplate="%{x}<br>Price: $%{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=chart_data["timestamp"],
            y=chart_data["volume"],
            name="Volume",
            marker={"color": "#FF6B6B", "opacity": 0.8},
            width=4 * 60 * 1000,
            hovertemplate="%{x}<br>Volume: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        height=500,
        hovermode="x unified",
        uirevision=selected_symbol,
        title={"text": f"Price / Volume<br><sup>{resolved_symbol}</sup>"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"l": 48, "r": 56, "t": 48, "b": 36},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={
            "title": "Time",
            "range": [last_3h_start, latest_timestamp],
            "rangeslider": {
                "visible": True,
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
            "rangeselector": {
                "buttons": [
                    {"count": 15, "label": "15m", "step": "minute", "stepmode": "backward"},
                    {"count": 1, "label": "1H", "step": "hour", "stepmode": "backward"},
                    {"count": 4, "label": "4H", "step": "hour", "stepmode": "backward"},
                    {"count": 1, "label": "1D", "step": "day", "stepmode": "backward"},
                    {"label": "All", "step": "all"},
                ]
            },
        },
    )
    fig.update_yaxes(
        title_text="Price",
        secondary_y=False,
        gridcolor="rgba(128,128,128,0.18)",
        autorange=True,
        fixedrange=False,
        automargin=True,
    )
    fig.update_yaxes(
        title_text="Volume",
        secondary_y=True,
        showgrid=False,
        range=[0, volume_axis_max],
        fixedrange=False,
        automargin=True,
    )
    return fig


def _selected_or_first_symbol(candles: pd.DataFrame, symbol: str | None) -> str | None:
    if candles.empty or "symbol" not in candles:
        return None
    available_symbols = candles["symbol"].dropna().astype(str)
    if available_symbols.empty:
        return None
    if symbol and symbol != "All" and symbol in set(available_symbols):
        return symbol
    return str(available_symbols.iloc[0])


def top_volume_symbols(candles: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    """Return symbols with highest observed candle volume."""
    if candles.empty:
        return pd.DataFrame(columns=["symbol", "volume"])
    return (
        candles.groupby("symbol", as_index=False)["volume"]
        .max()
        .sort_values("volume", ascending=False)
        .head(limit)
    )


def top_price_movement_symbols(candles: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    """Return symbols with largest absolute candle return."""
    if candles.empty:
        return pd.DataFrame(columns=["symbol", "absolute_return"])
    frame = candles.copy()
    frame["absolute_return"] = (
        (pd.to_numeric(frame["close"], errors="coerce") - pd.to_numeric(frame["open"], errors="coerce"))
        / pd.to_numeric(frame["open"], errors="coerce")
    ).abs()
    return (
        frame.groupby("symbol", as_index=False)["absolute_return"]
        .max()
        .sort_values("absolute_return", ascending=False)
        .head(limit)
    )
