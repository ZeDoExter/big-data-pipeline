"""ML training pipeline for wave height prediction."""
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Features to exclude from training
EXCLUDE_COLS = ["timestamp", "target_wave_height_3h", "target_wind_speed_3h"]

# Target columns
TARGETS = ["target_wave_height_3h", "target_wind_speed_3h"]


def load_all_features(feature_dir: Path) -> pd.DataFrame:
    """Load and combine all station feature CSVs."""
    frames = []
    for f in sorted(feature_dir.glob("*_features.csv")):
        df = pd.read_csv(f, parse_dates=["timestamp"])
        df["station_id"] = f.stem.replace("_features", "")
        frames.append(df)
    
    combined = pd.concat(frames, ignore_index=True)
    logger.info("loaded %d rows from %d stations", len(combined), len(frames))
    return combined


def prepare_data(df: pd.DataFrame, target: str):
    """Split into X, y for a given target."""
    # Encode station_id
    le = LabelEncoder()
    df = df.copy()
    df["station_enc"] = le.fit_transform(df["station_id"])
    
    # Select feature columns
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS + ["station_id"]]
    
    X = df[feature_cols + ["station_enc"]].values
    y = df[target].values
    
    return X, y, feature_cols, le


def time_based_split(df, train_ratio=0.7, val_ratio=0.15):
    """Split by time to avoid data leakage."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]
    
    return train, val, test


def train_random_forest(X_train, y_train, X_val, y_val):
    """Train Random Forest baseline."""
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    
    val_pred = model.predict(X_val)
    metrics = compute_metrics(y_val, val_pred)
    
    logger.info("RF val MAE=%.4f RMSE=%.4f R2=%.4f",
                metrics["mae"], metrics["rmse"], metrics["r2"])
    
    return model, metrics


def compute_metrics(y_true, y_pred):
    """Compute regression metrics."""
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "r2": r2_score(y_true, y_pred),
    }


def main():
    logging.basicConfig(level=logging.INFO)
    
    # Load data
    df = load_all_features(Path("data/features"))
    
    # Time-based split
    train, val, test = time_based_split(df)
    logger.info("train=%d val=%d test=%d", len(train), len(val), len(test))
    
    results = {}
    
    for target in TARGETS:
        logger.info("--- target: %s ---", target)
        
        # Prepare
        X_train, y_train, feature_cols, le = prepare_data(train, target)
        X_val, y_val, _, _ = prepare_data(val, target)
        
        # Drop NaN rows
        train_mask = ~np.isnan(X_train).any(axis=1) & ~np.isnan(y_train)
        val_mask = ~np.isnan(X_val).any(axis=1) & ~np.isnan(y_val)
        
        X_train = X_train[train_mask]
        y_train = y_train[train_mask]
        X_val = X_val[val_mask]
        y_val = y_val[val_mask]
        
        # Train
        model, metrics = train_random_forest(X_train, y_train, X_val, y_val)
        results[target] = {"model": model, "metrics": metrics}
    
    logger.info("training complete")
    
    # Save models
    out_dir = Path("models")
    out_dir.mkdir(exist_ok=True)
    for target, res in results.items():
        name = target.replace("target_", "").replace("_3h", "")
        path = out_dir / f"rf_{name}.pkl"
        with open(path, "wb") as f:
            pickle.dump(res["model"], f)
        logger.info("saved %s", path)
    
    return results


if __name__ == "__main__":
    main()
