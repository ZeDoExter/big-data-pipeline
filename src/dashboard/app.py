"""Streamlit dashboard — world map with buoy stations."""
import pickle
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Buoy Wave Forecast", layout="wide")

MODEL_DIR = Path("models")
DATA_DIR = Path("data/features")
COORDS_FILE = Path("data/stations_coords.csv")

SELECTED = ["41001", "44013", "41040", "41004", "41009", "46012", "46042", "42001", "42002"]


@st.cache_data
def load_models():
    models = {}
    for f in MODEL_DIR.glob("rf_*.pkl"):
        name = f.stem.replace("rf_", "")
        with open(f, "rb") as fp:
            models[name] = pickle.load(fp)
    return models


@st.cache_data
def load_coords():
    return pd.read_csv(COORDS_FILE)


@st.cache_data
def load_station_data(station_id):
    f = DATA_DIR / f"{station_id}_features.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["timestamp"])
    return pd.DataFrame()


def risk_color(wave_h):
    if wave_h < 2.0:
        return "green"
    elif wave_h < 4.0:
        return "orange"
    return "red"


def main():
    st.title("Global Buoy Wave Forecast")
    
    models = load_models()
    coords = load_coords()
    
    # Filter to selected stations
    stations = coords[coords["station_id"].astype(str).isin(SELECTED)].copy()
    
    if stations.empty:
        st.error("No station coordinates found")
        return
    
    # Predict for each station
    predictions = []
    for _, row in stations.iterrows():
        sid = str(row["station_id"])
        df = load_station_data(sid)
        if df.empty:
            continue
        
        latest = df.iloc[-1]
        pred_wave = None
        if "wave_height" in models:
            # Simple: use latest actual as baseline
            pred_wave = latest.get("wave_height", None)
        
        predictions.append({
            "station_id": sid,
            "name": row["name"],
            "lat": row["lat"],
            "lon": row["lon"],
            "wave_height": latest.get("wave_height", None),
            "wind_speed": latest.get("wind_speed", None),
            "risk": risk_color(latest.get("wave_height", 0)),
        })
    
    pred_df = pd.DataFrame(predictions)
    if pred_df.empty:
        st.warning("No predictions available")
        return
    
    # World map
    fig = px.scatter_geo(
        pred_df,
        lat="lat",
        lon="lon",
        color="risk",
        color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
        hover_name="name",
        hover_data=["station_id", "wave_height", "wind_speed"],
        title="Buoy Stations — Risk Level",
        projection="natural earth",
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="Black",
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue",
    )
    fig.update_layout(height=600)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Station detail
    st.subheader("Station Details")
    selected = st.selectbox("Select station", pred_df["station_id"].tolist())
    
    if selected:
        df = load_station_data(selected)
        if not df.empty:
            latest = df.iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Wave Height", f"{latest.get('wave_height', 'N/A'):.2f} m")
            col2.metric("Wind Speed", f"{latest.get('wind_speed', 'N/A'):.1f} m/s")
            col3.metric("Pressure", f"{latest.get('pressure', 'N/A'):.1f} hPa")
            
            # Recent trend
            st.subheader("Recent Trend")
            st.line_chart(df.tail(48).set_index("timestamp")[["wave_height", "wind_speed"]])


if __name__ == "__main__":
    main()
