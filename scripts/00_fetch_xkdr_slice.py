"""
AirPulse India: Ingestion & Dataset Slicing Script
Author: AirPulse Big Data Engineering
Reference: xKDR Forum Air-Quality-Database (https://airquality.xkdr.org)
Licence: CC-BY 4.0 (Central Pollution Control Board / US State Dept / xKDR Forum)

Downloads verified CAAQMS air quality measurements directly from xKDR Cloudflare R2 endpoints.
Stages raw parquet files into the local / HDFS staging directory: data/raw/
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AirPulse-Ingestion")

BASE_URL = "https://airquality.xkdr.org"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"
DEFAULT_HEADERS = {
    "Authorization": f"Bearer {DEMO_KEY}",
    "User-Agent": "AirPulse-BDA-Research/1.0 (Academic Big Data Analytics Pipeline)"
}

TARGET_CITIES = [
    "Delhi", "Mumbai", "Bengaluru", "Kolkata", 
    "Hyderabad", "Lucknow", "Patna", "Chennai", "Ahmedabad"
]

def fetch_file(endpoint_key: str, destination_path: Path) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists() and destination_path.stat().st_size > 0:
        logger.info(f"File already cached: {destination_path} ({destination_path.stat().st_size / 1024:.1f} KB)")
        return destination_path

    url = f"{BASE_URL}/v1/files/{endpoint_key}"
    logger.info(f"Downloading {url} -> {destination_path}...")
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=60)
    resp.raise_for_status()

    destination_path.write_bytes(resp.content)
    logger.info(f"Successfully saved {destination_path} ({len(resp.content) / (1024 * 1024):.2f} MB)")
    return destination_path

def main():
    parser = argparse.ArgumentParser(description="AirPulse India: xKDR CPCB Data Slice Fetcher")
    parser.add_argument("--output-dir", type=str, default="data/raw", help="Directory to store raw files")
    parser.add_argument("--year", type=int, default=2024, help="Target year")
    parser.add_argument("--months", nargs="+", type=int, default=[1, 4, 7, 10, 11], 
                        help="Months to fetch (default: Jan, Apr, Jul, Oct, Nov for seasonal contrast)")
    parser.add_argument("--all-months", action="store_true", help="Download all 12 months")
    parser.add_argument("--filter-metros", action="store_true", default=True, 
                        help="Filter to key representative metro zones to optimize memory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== STEP 1: Fetching Station & Parameter Metadata ===")
    stations_path = fetch_file("v1/stations.parquet", out_dir / "metadata" / "stations.parquet")
    params_path = fetch_file("v1/parameters.parquet", out_dir / "metadata" / "parameters.parquet")

    stations_df = pd.read_parquet(stations_path)
    logger.info(f"Total Stations in registry: {len(stations_df)} ({stations_df['latitude'].notna().sum()} geolocated)")

    months = list(range(1, 13)) if args.all_months else args.months
    logger.info(f"=== STEP 2: Fetching Hourly Measurements for Year {args.year}, Months {months} ===")

    downloaded_files = []
    for m in months:
        key = f"v1/measurements/year={args.year}/month={m:02d}/data.parquet"
        dest = out_dir / f"measurements_year_{args.year}_month_{m:02d}.parquet"
        try:
            saved = fetch_file(key, dest)
            downloaded_files.append(saved)
        except Exception as e:
            logger.error(f"Failed to fetch {key}: {e}")

    logger.info(f"=== STEP 3: Ingestion Verification & Local Staging Summary ===")
    total_size_mb = sum(f.stat().st_size for f in downloaded_files) / (1024 * 1024)
    logger.info(f"Ingested {len(downloaded_files)} monthly slices totaling {total_size_mb:.2f} MB")
    
    if downloaded_files:
        sample_df = pd.read_parquet(downloaded_files[0])
        logger.info(f"Sample monthly slice columns: {list(sample_df.columns)}")
        logger.info(f"Sample row count in month {months[0]}: {len(sample_df):,}")
        logger.info(f"Unique pollutants present: {sample_df['parameter_name'].unique().tolist()}")

    logger.info("Raw data staging complete. Ready for HDFS upload and Spark ETL.")

if __name__ == "__main__":
    main()
