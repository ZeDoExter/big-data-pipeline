"""NDBC data ingestion script."""
import argparse
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NDBC_HISTORICAL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{station_id}h{year}.txt.gz"
NDBC_REALTIME = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
NDBC_STATIONS = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"

SELECTED_STATIONS = ["41001", "44013", "41040", "41004", "41009", "46012", "46042", "42001", "42002"]


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    """Download with retry logic."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            logger.info("downloaded %s -> %s", url, dest)
            return True
        except requests.RequestException as e:
            logger.warning("attempt %d failed: %s", attempt + 1, e)
            time.sleep(2 ** attempt)
    return False


def download_historical(station: str, year: int, dest_dir: Path) -> bool:
    """Download historical data for a station/year."""
    url = NDBC_HISTORICAL.format(station_id=station, year=year)
    dest = dest_dir / "historical" / f"{station}h{year}.txt.gz"
    return download_file(url, dest)


def download_realtime(station: str, dest_dir: Path) -> bool:
    """Download realtime data (last 45 days)."""
    url = NDBC_REALTIME.format(station_id=station)
    dest = dest_dir / "realtime" / f"{station}.txt"
    return download_file(url, dest)


def download_station_list(dest_dir: Path) -> bool:
    """Download station metadata."""
    dest = dest_dir / "stations" / "station_table.txt"
    return download_file(NDBC_STATIONS, dest)


def main():
    parser = argparse.ArgumentParser(description="Download NDBC buoy data")
    parser.add_argument("--stations", nargs="+", default=SELECTED_STATIONS)
    parser.add_argument("--years", default="2020-2024", help="Year range e.g. 2020-2024")
    parser.add_argument("--dest", default="data/ndbc")
    parser.add_argument("--realtime-only", action="store_true", help="Only download realtime data")
    args = parser.parse_args()

    dest_dir = Path(args.dest)

    # Station list
    download_station_list(dest_dir)

    for station in args.stations:
        logger.info("station %s", station)
        if not args.realtime_only:
            year_start, year_end = map(int, args.years.split("-"))
            for year in range(year_start, year_end + 1):
                download_historical(station, year, dest_dir)
        download_realtime(station, dest_dir)

    logger.info("done")


if __name__ == "__main__":
    main()
