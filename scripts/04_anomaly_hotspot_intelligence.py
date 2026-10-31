"""
AirPulse India: Explainable Anomaly Detection & Hotspot Disaggregation Engine
Author: AirPulse Big Data Engineering
Module: Statistical Anomaly Detection & Station Hotspot Classification

Core Capabilities:
1. Explainable Spike Detection: Rolling Median & MAD (Median Absolute Deviation) Modified Z-Scores.
2. Station Disaggregation: Separates Persistent Hotspots (chronic high baseline) from Occasional Spike Zones (high volatility).
3. Produces audit-ready anomaly log and classification matrix.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure HADOOP_HOME and PATH are configured for Windows native Hadoop compatibility
hadoop_home = Path(__file__).resolve().parent.parent / "hadoop"
if hadoop_home.exists():
    os.environ["HADOOP_HOME"] = str(hadoop_home)
    os.environ["PATH"] = str(hadoop_home / "bin") + ";" + os.environ.get("PATH", "")

# Explicitly bind PySpark Python runtime to current environment (prevents Windows alias bug)
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType, StringType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AirPulse-AnomalyHotspot")

def detect_anomalies_and_hotspots(spark: SparkSession, curated_input_path: str, output_dir: str):
    logger.info(f"Loading curated data from {curated_input_path}...")
    df = spark.read.parquet(curated_input_path).filter(F.col("parameter_name") == "PM2.5")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Convert to daily station averages for robust baseline & volatility modeling
    daily_df = (
        df.groupBy("station_id", "station_name", "city_name", "state_name", "year", "month", "day")
        .agg(
            F.count("value").alias("hourly_readings"),
            F.avg("value").alias("daily_pm25"),
            F.max("value").alias("daily_peak_pm25"),
            F.first("latitude").alias("latitude"),
            F.first("longitude").alias("longitude")
        )
        .filter(F.col("hourly_readings") >= 16) # CPCB 16-hr completeness rule
    )

    daily_pd = daily_df.toPandas()
    logger.info(f"Loaded {len(daily_pd):,} valid daily station observations.")

    # Sort chronologically for rolling calculations
    daily_pd["date"] = pd.to_datetime(daily_pd[["year", "month", "day"]])
    daily_pd = daily_pd.sort_values(["station_id", "date"]).reset_index(drop=True)

    # =========================================================================
    # PART 1: EXPLAINABLE ANOMALY DETECTION (ROBUST ROLLING MAD)
    # =========================================================================
    logger.info("Computing station-level 14-day rolling median and MAD thresholds...")

    anomaly_records = []
    for station_id, group in daily_pd.groupby("station_id"):
        if len(group) < 7:
            continue

        group = group.copy().set_index("date")
        
        # 14-day rolling window
        rolling_median = group["daily_pm25"].rolling("14D", min_periods=5).median()
        
        # Compute deviation and rolling MAD
        abs_dev = (group["daily_pm25"] - rolling_median).abs()
        rolling_mad = abs_dev.rolling("14D", min_periods=5).median()
        
        # Guard against zero MAD in low-variance stations
        effective_mad = rolling_mad.clip(lower=5.0)

        # Boris Iglewicz and David Hoaglin (1993) Modified Z-score
        # M_i = 0.6745 * (x_i - median) / MAD
        mod_z = 0.6745 * (group["daily_pm25"] - rolling_median) / effective_mad

        # Anomaly criteria: Modified Z >= 3.5 AND daily average > 60 ug/m3 (CPCB NAAQS Standard)
        is_spike = (mod_z >= 3.5) & (group["daily_pm25"] > 60.0)

        spike_rows = group[is_spike].copy()
        if not spike_rows.empty:
            spike_rows["baseline_median"] = rolling_median[is_spike].round(2)
            spike_rows["rolling_mad"] = effective_mad[is_spike].round(2)
            spike_rows["modified_z_score"] = mod_z[is_spike].round(2)
            spike_rows["absolute_excess"] = (spike_rows["daily_pm25"] - spike_rows["baseline_median"]).round(2)
            spike_rows["spike_ratio"] = (spike_rows["daily_pm25"] / spike_rows["baseline_median"]).round(2)
            spike_rows["severity_tier"] = np.where(
                spike_rows["modified_z_score"] >= 5.0, "Severe Spike", "Acute Spike"
            )
            anomaly_records.append(spike_rows.reset_index())

    if anomaly_records:
        anomalies_df = pd.concat(anomaly_records, ignore_index=True)
        anomalies_df = anomalies_df.sort_values("modified_z_score", ascending=False)
        anomalies_df.to_csv(out_path / "spike_anomalies_log.csv", index=False)
        logger.info(f"Detected {len(anomalies_df):,} acute explainable pollution spikes across stations.")
    else:
        logger.warning("No anomalies met the strict threshold.")
        anomalies_df = pd.DataFrame()

    # =========================================================================
    # PART 2: PERSISTENT HOTSPOT VS. OCCASIONAL SPIKE DISAGGREGATION
    # =========================================================================
    logger.info("Computing Station Hotspot Classification Matrix...")

    station_metrics = []
    for station_id, group in daily_pd.groupby("station_id"):
        if len(group) < 15:
            continue

        station_name = group["station_name"].iloc[0]
        city = group["city_name"].iloc[0]
        state = group["state_name"].iloc[0]
        lat = group["latitude"].iloc[0]
        lon = group["longitude"].iloc[0]

        total_days = len(group)
        mean_pm25 = group["daily_pm25"].mean()
        median_pm25 = group["daily_pm25"].median()
        p95_pm25 = group["daily_pm25"].quantile(0.95)
        p99_pm25 = group["daily_pm25"].quantile(0.99)
        max_pm25 = group["daily_pm25"].max()

        # Chronic Exceedance: % of days exceeding CPCB 60 ug/m3
        exceed_days = (group["daily_pm25"] > 60.0).sum()
        chronic_exceedance_pct = (exceed_days / total_days) * 100.0

        # Severe Exceedance: % of days exceeding Emergency / Severe 250 ug/m3
        severe_days = (group["daily_pm25"] > 250.0).sum()
        severe_exceedance_pct = (severe_days / total_days) * 100.0

        # Spike Volatility Ratio (P95 / Median)
        volatility_ratio = p95_pm25 / max(median_pm25, 10.0)

        station_spikes = (
            len(anomalies_df[anomalies_df["station_id"] == station_id])
            if not anomalies_df.empty else 0
        )

        # Classification Taxonomy
        if chronic_exceedance_pct >= 60.0 and volatility_ratio <= 3.0:
            classification = "Persistent Hotspot (Chronic Sink)"
            color_code = "#d90429"
        elif volatility_ratio >= 2.5 and chronic_exceedance_pct < 50.0:
            classification = "Occasional Spike Zone (Episodic)"
            color_code = "#f77f00"
        elif chronic_exceedance_pct >= 40.0:
            classification = "Moderate Hotspot"
            color_code = "#fcbf49"
        else:
            classification = "Compliant / Low Exposure"
            color_code = "#2b9348"

        station_metrics.append({
            "station_id": station_id,
            "station_name": station_name,
            "city_name": city,
            "state_name": state,
            "latitude": lat,
            "longitude": lon,
            "monitored_days": total_days,
            "mean_pm25": round(mean_pm25, 2),
            "median_pm25": round(median_pm25, 2),
            "p95_pm25": round(p95_pm25, 2),
            "p99_pm25": round(p99_pm25, 2),
            "max_pm25": round(max_pm25, 2),
            "chronic_exceedance_pct": round(chronic_exceedance_pct, 2),
            "severe_exceedance_pct": round(severe_exceedance_pct, 2),
            "volatility_ratio": round(volatility_ratio, 2),
            "detected_spikes": station_spikes,
            "classification": classification,
            "color_code": color_code
        })

    classification_df = pd.DataFrame(station_metrics).sort_values("chronic_exceedance_pct", ascending=False)
    classification_df.to_csv(out_path / "station_hotspot_classification.csv", index=False)
    logger.info(f"Station classification complete: {len(classification_df)} stations mapped.")

    print("\n=== TOP PERSISTENT HOTSPOTS (CHRONIC) ===")
    persistent = classification_df[classification_df["classification"].str.contains("Persistent")]
    print(persistent[["station_name", "city_name", "mean_pm25", "chronic_exceedance_pct", "volatility_ratio"]].head(10).to_string())

    print("\n=== TOP OCCASIONAL SPIKE ZONES (EPISODIC) ===")
    episodic = classification_df[classification_df["classification"].str.contains("Occasional")]
    print(episodic[["station_name", "city_name", "mean_pm25", "volatility_ratio", "detected_spikes"]].head(10).to_string())

def main():
    parser = argparse.ArgumentParser(description="AirPulse Anomaly & Hotspot Engine")
    parser.add_argument("--curated-path", type=str, default="data/hdfs_storage/airpulse/curated/measurements",
                        help="Curated dataset path")
    parser.add_argument("--output-dir", type=str, default="data/hdfs_storage/airpulse/analytics/tables",
                        help="Output directory for anomaly and hotspot tables")
    parser.add_argument("--spark-master", type=str, default="local[*]", help="Spark Master")
    args = parser.parse_args()

    builder = (
        SparkSession.builder
        .appName("AirPulse-AnomalyHotspot-Engine")
        .master(args.spark_master)
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
    )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    detect_anomalies_and_hotspots(spark, args.curated_path, args.output_dir)
    spark.stop()

if __name__ == "__main__":
    main()
