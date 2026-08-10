"""Streamlit dashboard — global buoy monitoring."""
import pickle
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Buoy Watch — Global Ocean Monitoring",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clean, professional color palette (not default green/orange/red)
_RISK_COLORS = {
    "low": "#22c55e",      # emerald-500
    "moderate": "#f59e0b", # amber-500
    "high": "#ef4444",     # red-500
}

_MODEL_DIR = Path("models")
_DATA_DIR = Path("data/features")
_COORDS_FILE = Path("data/stations_coords.csv")
_SELECTED = ["41001", "44013", "41040", "41004", "41009", "46012", "46042", "42001", "42002"]


@st.cache_data
def load_models():
    models = {}
    for f in _MODEL_DIR.glob("rf_*.pkl"):
        with open(f, "rb") as fp:
            models[f.stem.replace("rf_", "")] = pickle.load(fp)
    return models


@st.cache_data
def load_coords():
    return pd.read_csv(_COORDS_FILE)


@st.cache_data
def load_station_data(station_id):
    f = _DATA_DIR / f"{station_id}_features.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["timestamp"])
    return pd.DataFrame()


def risk_level(wave_h):
    if wave_h < 2.0:
        return "low"
    elif wave_h < 4.0:
        return "moderate"
    return "high"


def main():
    # Header
    st.markdown(
        "<h1 style='margin-bottom:0; font-size:28px; letter-spacing:-0.5px;'>"
        "🌊 Buoy Watch</h1>"
        "<p style='color:#6b7280; margin-top:0; font-size:14px;'>"
        "Real-time ocean monitoring & wave forecast — 9 NDBC stations</p>",
        unsafe_allow_html=True,
    )

    models = load_models()
    coords = load_coords()
    stations = coords[coords["station_id"].astype(str).isin(_SELECTED)].copy()

    if stations.empty:
        st.error("No station coordinates found")
        return

    # Predict for each station
    rows = []
    for _, row in stations.iterrows():
        sid = str(row["station_id"])
        df = load_station_data(sid)
        if df.empty:
            continue

        latest = df.iloc[-1]
        wave = latest.get("wave_height")

        rows.append({
            "station_id": sid,
            "name": f"{row['name'].title()} ({sid})",
            "lat": row["lat"],
            "lon": row["lon"],
            "wave_height": wave,
            "wind_speed": latest.get("wind_speed"),
            "pressure": latest.get("pressure"),
            "risk": risk_level(wave) if wave is not None else "low",
        })

    pred_df = pd.DataFrame(rows)
    if pred_df.empty:
        st.warning("No data available")
        return

    # World map
    fig = px.scatter_geo(
        pred_df,
        lat="lat",
        lon="lon",
        color="risk",
        color_discrete_map=_RISK_COLORS,
        hover_name="name",
        hover_data=["wave_height", "wind_speed", "pressure"],
        projection="natural earth",
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="#d1d5db",
        showland=True,
        landcolor="#f3f4f6",
        showocean=True,
        oceancolor="#dbeafe",
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title="Risk",
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Station detail
    st.markdown("---")
    st.subheader("Station Detail")

    pred_df["label"] = pred_df["name"]
    selected_label = st.selectbox("Select a station", pred_df["label"].tolist(), label_visibility="collapsed")
    selected = pred_df.loc[pred_df["label"] == selected_label, "station_id"].iloc[0]

    df = load_station_data(selected)
    if not df.empty:
        latest = df.iloc[-1]

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Wave Height", f"{latest.get('wave_height', 0):.2f} m")
        with col2:
            st.metric("Wind Speed", f"{latest.get('wind_speed', 0):.1f} m/s")
        with col3:
            st.metric("Pressure", f"{latest.get('pressure', 0):.0f} hPa")
        with col4:
            risk = risk_level(latest.get("wave_height", 0))
            st.metric("Risk Level", risk.upper())

        # Trend chart
        st.markdown("**24h Trend**")
        trend_df = df.tail(48).set_index("timestamp")[["wave_height", "wind_speed"]]
        st.line_chart(trend_df, height=200)


if __name__ == "__main__":
    main()
