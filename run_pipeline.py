"""
AirPulse India: Master Distributed Pipeline Orchestrator
Author: AirPulse Big Data Engineering
Project: Distributed Air Pollution Spike & Hotspot Intelligence

Orchestrates the entire distributed pipeline:
Step 0: Pre-flight Verification & Environment Sanity
Step 1: Ingestion of Real xKDR/CPCB CAAQMS Data Slice
Step 2: HDFS Hierarchy Provisioning & Data Placement
Step 3: PySpark Distributed Cleaning & Invariant Validation
Step 4: Spark SQL Analytical Trends (Diurnal, Seasonal, Exceedances)
Step 5: Robust Statistical Anomaly Detection & Hotspot Segregation
Step 6: Publication-Quality Figures & Submission Evidence Generation
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AirPulse-Master")

def run_step(step_name: str, cmd_list: list):
    logger.info("============================================================")
    logger.info(f"STARTING {step_name}")
    logger.info(f"Executing: {' '.join(cmd_list)}")
    logger.info("============================================================")
    t0 = time.time()
    
    result = subprocess.run(cmd_list, check=True)
    
    elapsed = time.time() - t0
    logger.info(f"SUCCESS: {step_name} completed in {elapsed:.2f} seconds.\n")

def main():
    python_bin = sys.executable
    logger.info(f"Using Python runtime: {python_bin}")

    # Step 1: Download verified slice
    run_step(
        "STEP 1: Fetching xKDR CAAQMS Real Measurement Slices",
        [python_bin, "scripts/00_fetch_xkdr_slice.py", "--months", "1", "7", "11"]
    )

    # Step 2: HDFS Ingestion & Directory Provisioning
    run_step(
        "STEP 2: Provisioning HDFS Storage & Uploading Raw Datasets",
        [python_bin, "scripts/01_hdfs_manager.py"]
    )

    # Step 3: Spark ETL Cleaning & Validation
    run_step(
        "STEP 3: PySpark Distributed Cleaning & Validation",
        [python_bin, "scripts/02_spark_etl_clean.py"]
    )

    # Step 4: Spark SQL Analytical Trends
    run_step(
        "STEP 4: Spark SQL Distributed Analytical Query Engine",
        [python_bin, "scripts/03_spark_sql_analytics.py"]
    )

    # Step 5: Anomaly & Hotspot Intelligence
    run_step(
        "STEP 5: Robust Anomaly Detection & Hotspot Classification",
        [python_bin, "scripts/04_anomaly_hotspot_intelligence.py"]
    )

    # Step 6: Visualizations & Submission Evidence
    run_step(
        "STEP 6: Generating Publication-Ready Figures & Reports",
        [python_bin, "scripts/05_visualizations.py"]
    )

    logger.info("============================================================")
    logger.info("AIRPULSE INDIA DISTRIBUTED PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("All HDFS artifacts, Spark SQL results, and figures generated.")
    logger.info("============================================================")

if __name__ == "__main__":
    main()
