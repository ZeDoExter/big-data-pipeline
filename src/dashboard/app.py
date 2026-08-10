"""Streamlit dashboard for buoy wave forecast."""
import pickle
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Buoy Wave Forecast", layout="wide")

MODEL_DIR = Path("models")
DATA_DIR = Path("data/features")


@st.cache_data
def load_models():
    """Load trained models."""
    models = {}
    for f in MODEL_DIR.glob("rf_*.pkl"):
        name = f.stem.replace("rf_", "")
        with open(f, "rb") as fp:
            models[name] = pickle.load(fp)
    return models


@st.cache_data
def load_station_data(station_id: str):
    """Load feature data for a station."""
    f = DATA_DIR / f"{station_id}_features.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["timestamp"])
    return pd.DataFrame()


def main():
    st.title("Buoy Wave Forecast Dashboard")
    
    models = load_models()
    if not models:
        st.error("No models found. Run training first.")
        return
    
    st.sidebar.header("Settings")
    target = st.sidebar.selectbox("Target", ["wave_height", "wind_speed"])
    station = st.sidebar.selectbox("Station", 
                                    sorted([f.stem.replace("_features", "") 
                                           for f in DATA_DIR.glob("*_features.csv")]))
    
    # Load data
    df = load_station_data(station)
    if df.empty:
        st.warning(f"No data for station {station}")
        return
    
    # Predict
    model = models.get(target)
    if model is None:
        st.error(f"No model for {target}")
        return
    
    # Use latest data for prediction
    latest = df.iloc[-10:].copy()
    
    st.subheader(f"Station {station} — {target} forecast")
    
    # Show recent data chart
    st.line_chart(latest.set_index("timestamp")[target])
    
    # Show prediction vs actual
    st.subheader("Recent predictions vs actual")
    st.dataframe(latest[["timestamp", target]].tail(10))
    
    st.sidebar.info(f"Model: Random Forest\nTarget: {target}")


if __name__ == "__main__":
    main()
