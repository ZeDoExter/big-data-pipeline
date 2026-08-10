"""Tests for ML training pipeline."""
import numpy as np
import pandas as pd
import pytest

from src.ml.train import load_all_features, prepare_data, time_based_split, compute_metrics


@pytest.fixture
def combined_df():
    """Create a combined sample DataFrame."""
    frames = []
    for station in ["41001", "41004"]:
        idx = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "timestamp": idx,
            "wave_height": np.linspace(1.0, 3.0, 100),
            "wind_speed": np.linspace(5.0, 15.0, 100),
            "pressure": np.linspace(1015.0, 1000.0, 100),
            "wind_dir": np.linspace(0, 360, 100),
            "wave_height_1h": np.linspace(1.0, 3.0, 100),
            "wave_height_6h": np.linspace(1.0, 3.0, 100),
            "wind_speed_1h": np.linspace(5.0, 15.0, 100),
            "wind_speed_6h": np.linspace(5.0, 15.0, 100),
            "target_wave_height_3h": np.linspace(1.5, 3.5, 100),
            "target_wind_speed_3h": np.linspace(6.0, 16.0, 100),
            "station_id": station,
        })
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def test_load_all_features(tmp_path):
    """Should load and combine station CSVs."""
    # Create test CSVs
    for station in ["41001", "41004"]:
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="h"),
            "wave_height": np.arange(10, dtype=float),
            "wind_speed": np.arange(10, dtype=float),
            "target_wave_height_3h": np.arange(10, dtype=float),
            "target_wind_speed_3h": np.arange(10, dtype=float),
        })
        df.to_csv(tmp_path / f"{station}_features.csv", index=False)
    
    result = load_all_features(tmp_path)
    assert len(result) == 20
    assert "station_id" in result.columns


def test_time_based_split(combined_df):
    """Split should be chronological."""
    train, val, test = time_based_split(combined_df)
    
    # No overlap
    assert train["timestamp"].max() < val["timestamp"].min()
    assert val["timestamp"].max() < test["timestamp"].min()
    
    # Roughly 70/15/15
    n = len(combined_df)
    assert len(train) > int(n * 0.6)
    assert len(train) < int(n * 0.8)


def test_compute_metrics():
    """Metrics should compute correctly."""
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 2.1, 2.9])
    
    metrics = compute_metrics(y_true, y_pred)
    
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert metrics["mae"] > 0
    assert metrics["mae"] < 0.2
    assert metrics["r2"] > 0.9


def test_prepare_data(combined_df):
    """Should encode station_id and split X/y."""
    X, y, feature_cols, le = prepare_data(combined_df, "target_wave_height_3h")
    
    assert X.shape[0] == len(combined_df)
    assert "station_enc" in feature_cols
    assert not np.isnan(y).any()
