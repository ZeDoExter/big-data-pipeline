"""Batch scoring — predict wave_height 3h ahead for all stations."""
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

MODEL_DIR = Path("models")
DATA_DIR = Path("data/features")
OUTPUT_FILE = Path("data/predictions.csv")

EXCLUDE_COLS = ["timestamp", "target_wave_height_3h", "target_wind_speed_3h"]


def score_station(model, df: pd.DataFrame, le: LabelEncoder, station_id: str):
    """Score a single station and return prediction."""
    df = df.copy()
    df["station_enc"] = le.transform([station_id])[0]
    
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS + ["station_id"]]
    X = df[feature_cols + ["station_enc"]].values
    
    # Drop NaN rows
    valid = ~np.isnan(X).any(axis=1)
    X_valid = X[valid]
    
    if len(X_valid) == 0:
        return None
    
    preds = model.predict(X_valid)
    
    # Return prediction for the latest row
    return {
        "station_id": station_id,
        "timestamp": df.iloc[-1]["timestamp"],
        "predicted_wave_height_3h": preds[-1],
        "actual_wave_height": df.iloc[-1].get("wave_height"),
    }


def main():
    # Load model
    model_path = MODEL_DIR / "rf_wave_height.pkl"
    if not model_path.exists():
        print("model not found")
        return
    
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    
    le = LabelEncoder()
    le.fit(["41001", "44013", "41040", "41004", "41009", "46012", "46042", "42001", "42002"])
    
    results = []
    for f in sorted(DATA_DIR.glob("*_features.csv")):
        station_id = f.stem.replace("_features", "")
        df = pd.read_csv(f, parse_dates=["timestamp"])
        result = score_station(model, df, le, station_id)
        if result:
            results.append(result)
    
    pred_df = pd.DataFrame(results)
    pred_df.to_csv(OUTPUT_FILE, index=False)
    print(f"scored {len(pred_df)} stations")
    print(pred_df.to_string())


if __name__ == "__main__":
    main()
