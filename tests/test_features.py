"""Tests for feature engineering."""
import numpy as np
import pandas as pd
import pytest

from src.spark.features import (
    add_lag_features,
    add_rolling_stats,
    add_pressure_drop_rate,
    encode_wind_direction,
    add_hour_of_day,
    build_features,
)


@pytest.fixture
def sample_df():
    """Create a small sample DataFrame for testing."""
    idx = pd.date_range("2024-01-01", periods=24, freq="h")
    return pd.DataFrame({
        "timestamp": idx,
        "wave_height": np.linspace(1.0, 3.0, 24),
        "wind_speed": np.linspace(5.0, 15.0, 24),
        "pressure": np.linspace(1015.0, 1000.0, 24),
        "wind_dir": np.linspace(0, 360, 24),
    })


def test_add_lag_features(sample_df):
    """Lag columns should be created."""
    df = add_lag_features(sample_df.copy(), "wave_height", [1, 3])
    assert "wave_height_1h" in df.columns
    assert "wave_height_3h" in df.columns


def test_add_rolling_stats(sample_df):
    """Rolling mean and std should be created."""
    df = add_rolling_stats(sample_df.copy(), "wave_height", [3])
    assert "wave_height_roll_mean_3h" in df.columns
    assert "wave_height_roll_std_3h" in df.columns


def test_add_pressure_drop_rate(sample_df):
    """Pressure drop requires lag columns first."""
    df = add_lag_features(sample_df.copy(), "pressure", [3, 6])
    df = add_pressure_drop_rate(df)
    assert "pressure_drop_3h" in df.columns
    assert "pressure_drop_6h" in df.columns


def test_encode_wind_direction(sample_df):
    """Wind dir sin/cos should be in [-1, 1]."""
    df = encode_wind_direction(sample_df.copy())
    assert "wind_dir_sin" in df.columns
    assert "wind_dir_cos" in df.columns
    assert df["wind_dir_sin"].between(-1, 1).all()
    assert df["wind_dir_cos"].between(-1, 1).all()


def test_add_hour_of_day(sample_df):
    """Hour sin/cos should be in [-1, 1]."""
    df = add_hour_of_day(sample_df.copy())
    assert "hour_sin" in df.columns
    assert "hour_cos" in df.columns
    assert df["hour_sin"].between(-1, 1).all()
    assert df["hour_cos"].between(-1, 1).all()


def test_build_features(sample_df):
    """Full feature pipeline should add targets and drop NaN."""
    df = build_features(sample_df.copy())
    assert "target_wave_height_3h" in df.columns
    assert "target_wind_speed_3h" in df.columns
    assert df.isna().sum().sum() == 0  # all NaN dropped
    assert len(df) < len(sample_df)  # some rows dropped due to lag/target
