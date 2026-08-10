"""Train XGBoost model for wave height prediction."""
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

EXCLUDE_COLS = ["timestamp", "target_wave_height_3h", "target_wind_speed_3h"]


def prepare_dataset(df: pd.DataFrame):
    """Prepare features and targets from combined DataFrame."""
    df = df.copy()
    le = LabelEncoder()
    df["station_enc"] = le.fit_transform(df["station_id"])
    
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS + ["station_id"]]
    
    X = df[feature_cols + ["station_enc"]].values
    y_wave = df["target_wave_height_3h"].values
    y_wind = df["target_wind_speed_3h"].values
    
    # Drop NaN
    valid = ~np.isnan(X).any(axis=1) & ~np.isnan(y_wave) & ~np.isnan(y_wind)
    return X[valid], y_wave[valid], y_wind[valid], feature_cols + ["station_enc"]


def time_split(df, train=0.7, val=0.15):
    """Time-based split."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    te = int(n * train)
    tv = int(n * (train + val))
    return df.iloc[:te], df.iloc[te:tv], df.iloc[tv:]


def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        from xgboost import XGBRegressor
    except ImportError:
        logger.warning("xgboost not installed, skipping")
        return
    
    # Load
    feature_dir = Path("data/features")
    frames = []
    for f in sorted(feature_dir.glob("*_features.csv")):
        df = pd.read_csv(f, parse_dates=["timestamp"])
        df["station_id"] = f.stem.replace("_features", "")
        frames.append(df)
    
    combined = pd.concat(frames, ignore_index=True)
    logger.info("loaded %d rows", len(combined))
    
    # Split
    train, val, test = time_split(combined)
    
    # Prepare
    X_train, y_wave_train, y_wind_train, feature_cols = prepare_dataset(train)
    X_val, y_wave_val, y_wind_val, _ = prepare_dataset(val)
    
    logger.info("X_train shape: %s", X_train.shape)
    
    # Wave height model
    wave_model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    wave_model.fit(X_train, y_wave_train)
    val_pred = wave_model.predict(X_val)
    
    mae = np.mean(np.abs(y_wave_val - val_pred))
    rmse = np.sqrt(np.mean((y_wave_val - val_pred) ** 2))
    logger.info("XGB Wave — val MAE=%.4f RMSE=%.4f", mae, rmse)
    
    # Wind speed model
    wind_model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    wind_model.fit(X_train, y_wind_train)
    val_pred_w = wind_model.predict(X_val)
    
    mae_w = np.mean(np.abs(y_wind_val - val_pred_w))
    rmse_w = np.sqrt(np.mean((y_wind_val - val_pred_w) ** 2))
    logger.info("XGB Wind — val MAE=%.4f RMSE=%.4f", mae_w, rmse_w)
    
    # Feature importance
    importances = wave_model.feature_importances_
    top_idx = np.argsort(importances)[-5:][::-1]
    for i in top_idx:
        logger.info("  %s: %.4f", feature_cols[i], importances[i])


if __name__ == "__main__":
    main()
