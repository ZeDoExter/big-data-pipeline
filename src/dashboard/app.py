import pickle
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Buoy Watch", layout="wide", initial_sidebar_state="expanded")

_MODEL_DIR = Path("models")
_DATA_DIR = Path("data/features")
_COORDS_FILE = Path("data/stations_coords.csv")
_SELECTED = ["41001", "44013", "41040", "41004", "41009", "46012", "46042", "42001", "42002"]

# Windy.com-inspired dark theme + color scale
_BG = "#1a1a2e"
_PANEL = "#16213e"
_TEXT = "#e0e0e0"
_ACCENT = "#f7b731"
_RISK_SCALE = [[0, "#00e676"], [0.5, "#ffeb3b"], [1, "#ff1744"]]


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


def main():
    st.markdown("""
        <style>
        .main { background-color: #1a1a2e; }
        .stApp { background: #1a1a2e; }
        h1, h2, h3, p, label, .stMetric { color: #e0e0e0 !important; }
        .stSelectbox > div { background: #16213e; color: #e0e0e0; }
        .stMetric { background: #16213e; border-radius: 8px; padding: 16px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        "<h1 style='margin-bottom:0; font-size:26px; letter-spacing:-0.5px; color:#f7b731;'>"
        "Buoy Watch</h1>"
        "<p style='color:#a0a0b0; margin-top:0; font-size:13px;'>"
        "Global ocean monitoring & wave forecast</p>",
        unsafe_allow_html=True,
    )

    models = load_models()
    coords = load_coords()
    stations = coords[coords["station_id"].astype(str).isin(_SELECTED)].copy()

    if stations.empty:
        st.error("No station coordinates")
        return

    rows = []
    for _, row in stations.iterrows():
        sid = str(row["station_id"])
        df = load_station_data(sid)
        if df.empty:
            continue

        latest = df.iloc[-1]
        wave = latest.get("wave_height")
        wind = latest.get("wind_speed")
        pressure = latest.get("pressure")

        rows.append({
            "station_id": sid,
            "name": f"{row['name'].title()} ({sid})",
            "short_name": row["name"].title(),
            "lat": row["lat"],
            "lon": row["lon"],
            "wave_height": wave,
            "wind_speed": wind,
            "pressure": pressure,
            "risk": wave if wave is not None else 0,
        })

    pred_df = pd.DataFrame(rows)
    if pred_df.empty:
        st.warning("No data")
        return

    # Windy-style map: dark bg, orthographic globe, color = wave height
    fig = px.scatter_geo(
        pred_df,
        lat="lat",
        lon="lon",
        color="wave_height",
        color_continuous_scale=_RISK_SCALE,
        size="wave_height",
        size_max=18,
        hover_name="short_name",
        hover_data=["wave_height", "wind_speed", "pressure"],
        projection="orthographic",
        title=None,
    )

    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showcoastlines=True,
        coastlinecolor="#4a5568",
        showland=True,
        landcolor="#2d3748",
        showocean=True,
        oceancolor="#1a202c",
        showcountries=True,
        countrycolor="#4a5568",
        showframe=False,
    )

    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=dict(text="Wave Height (m)", font=dict(color="#e0e0e0")),
            thickness=12,
            len=0.6,
            tickfont=dict(color="#e0e0e0"),
        ),
        legend=dict(font=dict(color="#e0e0e0")),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detail section
    st.markdown("---")
    st.subheader("Station Detail")

    selected_label = st.selectbox("Select a station", pred_df["name"].tolist(), label_visibility="collapsed")
    selected = pred_df.loc[pred_df["name"] == selected_label, "station_id"].iloc[0]

    df = load_station_data(selected)
    if not df.empty:
        latest = df.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wave Height", f"{latest.get('wave_height', 0):.2f} m")
        c2.metric("Wind Speed", f"{latest.get('wind_speed', 0):.1f} m/s")
        c3.metric("Pressure", f"{latest.get('pressure', 0):.0f} hPa")
        c4.metric("Air Temp", f"{latest.get('air_temp', 0):.1f} °C" if 'air_temp' in latest else "Air Temp", "N/A")

        st.markdown("**24h Trend**")
        st.line_chart(df.tail(48).set_index("timestamp")[["wave_height", "wind_speed"]], height=180)


if __name__ == "__main__":
    main()
