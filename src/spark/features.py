"""Feature engineering for NDBC buoy data."""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def add_lag_features(df: pd.DataFrame, col: str, lags: list[int]) -> pd.DataFrame:
    """Add lag features for a column."""
    for lag in lags:
        df[f"{col}_{lag}h"] = df[col].shift(lag)
    return df


def add_rolling_stats(df: pd.DataFrame, col: str, windows: list[int]) -> pd.DataFrame:
    """Add rolling mean and std."""
    for w in windows:
        df[f"{col}_roll_mean_{w}h"] = df[col].rolling(w, min_periods=1).mean()
        df[f"{col}_roll_std_{w}h"] = df[col].rolling(w, min_periods=1).std()
    return df


def add_pressure_drop_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Pressure drop rate — meteorologically meaningful storm signal."""
    if "pressure_6h" in df.columns:
        df["pressure_drop_6h"] = df["pressure"] - df["pressure_6h"]
    if "pressure_3h" in df.columns:
        df["pressure_drop_3h"] = df["pressure"] - df["pressure_3h"]
    return df


def encode_wind_direction(df: pd.DataFrame) -> pd.DataFrame:
    """Encode wind direction as sin/cos cyclical features."""
    if "wind_dir" in df.columns:
        rad = np.deg2rad(df["wind_dir"])
        df["wind_dir_sin"] = np.sin(rad)
        df["wind_dir_cos"] = np.cos(rad)
    return df


def add_hour_of_day(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour as cyclical feature."""
    if "timestamp" in df.columns:
        hour = df["timestamp"].dt.hour
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build all features for a station DataFrame."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Lag features (1h, 3h, 6h)
    for col in ["wave_height", "wind_speed", "pressure"]:
        df = add_lag_features(df, col, [1, 3, 6])
    
    # Rolling stats
    for col in ["wave_height", "wind_speed"]:
        df = add_rolling_stats(df, col, [3, 6])
    
    # Pressure drop rate
    df = add_pressure_drop_rate(df)
    
    # Wind direction encoding
    df = encode_wind_direction(df)
    
    # Hour of day
    df = add_hour_of_day(df)
    
    # Target: wave_height 3 hours ahead
    df["target_wave_height_3h"] = df["wave_height"].shift(-3)
    df["target_wind_speed_3h"] = df["wind_speed"].shift(-3)
    
    # Drop only rows where TARGET or essential features are missing
    essential = ["target_wave_height_3h", "wave_height", "wind_speed",
                 "pressure", "wave_height_1h", "wave_height_6h",
                 "wind_speed_1h", "wind_speed_6h"]
    return df.dropna(subset=[c for c in essential if c in df.columns])


def process_all_stations(input_dir: Path, output_dir: Path) -> None:
    """Process all station CSVs with feature engineering."""
    output_dir.mkdir(exist_ok=True)
    for f in sorted(input_dir.glob("*_clean.csv")):
        df = pd.read_csv(f, parse_dates=["timestamp"])
        df = build_features(df)
        out = output_dir / f.name.replace("_clean.csv", "_features.csv")
        df.to_csv(out, index=False)
        logger.info("%s -> %d rows, %d cols", out.name, len(df), len(df.columns))


def main():
    logging.basicConfig(level=logging.INFO)
    process_all_stations(Path("data/processed"), Path("data/features"))


if __name__ == "__main__":
    main()
