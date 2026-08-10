import gzip
import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Match only NDBC observation files: 41001h2020.txt.gz or 41001.txt
_OBS_PATTERN = re.compile(r"^\d{5}\.(txt\.gz|txt)$")

# Column names from NDBC stdmet format
COLUMNS = [
    "year", "month", "day", "hour", "minute",
    "wind_dir", "wind_speed", "gust", "wave_height", "dominant_period",
    "average_period", "mean_wave_dir", "pressure", "air_temp", "water_temp",
    "dewpoint", "visibility", "pressure_tendency", "tide",
]

# Sentinel value for missing data in NDBC
MISSING = "MM"


def parse_file(filepath: Path) -> pd.DataFrame:
    """Parse a single NDBC file (handles both .txt and .txt.gz)."""
    if filepath.suffix == ".gz":
        with gzip.open(filepath, "rt") as f:
            lines = f.readlines()
    else:
        lines = filepath.read_text().splitlines()
    
    # Skip header lines (start with #)
    data_lines = [l for l in lines if not l.startswith("#") and l.strip()]
    
    rows = []
    for line in data_lines:
        fields = line.split()
        if len(fields) < len(COLUMNS):
            continue
        rows.append(fields[:len(COLUMNS)])
    
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert types and handle missing values."""
    # Numeric columns
    numeric_cols = [
        "wind_dir", "wind_speed", "gust", "wave_height", "dominant_period",
        "average_period", "mean_wave_dir", "pressure", "air_temp", "water_temp",
        "dewpoint", "visibility", "pressure_tendency", "tide",
    ]
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Build timestamp
    df["timestamp"] = pd.to_datetime(
        df[["year", "month", "day", "hour", "minute"]]
    )
    
    # Keep only relevant columns
    keep = ["timestamp", "wind_dir", "wind_speed", "wave_height", "pressure",
            "air_temp", "water_temp"]
    
    return df[keep].dropna(subset=["wave_height", "wind_speed"], how="all")


def parse_all_stations(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Parse all observation files recursively."""
    results = {}
    station_files: dict[str, list[Path]] = {}
    
    def collect_files(path: Path):
        for item in sorted(path.iterdir()):
            if item.is_dir():
                collect_files(item)
            elif item.is_file() and _OBS_PATTERN.match(item.name):
                station = item.name.split("h")[0].split(".")[0]
                station_files.setdefault(station, []).append(item)
    
    collect_files(data_dir)
    
    for station, files in station_files.items():
        frames = []
        for f in files:
            try:
                df = parse_file(f)
                frames.append(df)
            except Exception as e:
                logger.warning("skip %s: %s", f, e)
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            cleaned = clean_dataframe(combined)
            if not cleaned.empty:
                results[station] = cleaned
                logger.info("station %s: %d rows", station, len(cleaned))
    return results


def main():
    logging.basicConfig(level=logging.INFO)
    data_dir = Path("data/ndbc")
    results = parse_all_stations(data_dir)
    
    # Save cleaned data
    out_dir = Path("data/processed")
    out_dir.mkdir(exist_ok=True)
    for station, df in results.items():
        out = out_dir / f"{station}_clean.csv"
        df.to_csv(out, index=False)
        logger.info("saved %s (%d rows)", out, len(df))


if __name__ == "__main__":
    main()
