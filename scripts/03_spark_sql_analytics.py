"""
AirPulse India: Spark SQL Distributed Analytical Query Engine
Author: AirPulse Big Data Engineering
Module: Analytical SQL Queries, Diurnal Patterns, Seasonality, and NAAQS Exceedance

Executes Spark SQL queries on Curated HDFS Parquet:
1. Diurnal (Hourly 0-23) PM2.5 & PM10 profiles by city.
2. Monthly seasonal trends (Winter Inversion vs Monsoon Washout).
3. Daily NAAQS regulatory exceedance rates (PM2.5 > 60 ug/m3, PM10 > 100 ug/m3).
4. Top 25 Most Polluted Monitoring Stations in India ranking.
5. Exports analytical summary tables to HDFS / local storage for dashboarding.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AirPulse-SparkSQL")

def run_analytics(spark: SparkSession, curated_input_path: str, analytics_output_dir: str):
    logger.info(f"Loading curated measurements from {curated_input_path}...")
    df = spark.read.parquet(curated_input_path)
    df.createOrReplaceTempView("curated_air_quality")

    out_dir = Path(analytics_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # QUERY 1: Diurnal Hourly Trend (Hour 0 to 23)
    # =========================================================================
    logger.info("Executing Query 1: Diurnal (Hourly) PM2.5 and PM10 Trends across Cities...")
    diurnal_sql = """
    SELECT 
        city_name,
        parameter_name,
        hour,
        COUNT(*) AS reading_count,
        ROUND(AVG(value), 2) AS mean_value,
        ROUND(PERCENTILE_APPROX(value, 0.50), 2) AS median_value,
        ROUND(PERCENTILE_APPROX(value, 0.90), 2) AS p90_value,
        ROUND(STDDEV(value), 2) AS std_dev
    FROM curated_air_quality
    WHERE parameter_name IN ('PM2.5', 'PM10')
      AND city_name IN ('Delhi', 'Mumbai', 'Bengaluru', 'Kolkata', 'Hyderabad', 'Lucknow', 'Patna')
    GROUP BY city_name, parameter_name, hour
    ORDER BY city_name, parameter_name, hour
    """
    diurnal_df = spark.sql(diurnal_sql)
    diurnal_pd = diurnal_df.toPandas()
    diurnal_pd.to_csv(out_dir / "diurnal_hourly_trends.csv", index=False)
    logger.info(f"Query 1 saved: {len(diurnal_pd)} city-hour aggregated records.")

    # =========================================================================
    # QUERY 2: Monthly Seasonal Trends
    # =========================================================================
    logger.info("Executing Query 2: Monthly Seasonal Profiles across Metros...")
    monthly_sql = """
    SELECT 
        city_name,
        parameter_name,
        month,
        COUNT(*) AS reading_count,
        ROUND(AVG(value), 2) AS monthly_mean,
        ROUND(PERCENTILE_APPROX(value, 0.50), 2) AS monthly_median,
        ROUND(PERCENTILE_APPROX(value, 0.95), 2) AS monthly_p95
    FROM curated_air_quality
    WHERE parameter_name IN ('PM2.5', 'PM10')
      AND city_name IN ('Delhi', 'Mumbai', 'Bengaluru', 'Kolkata', 'Hyderabad', 'Lucknow', 'Patna')
    GROUP BY city_name, parameter_name, month
    ORDER BY city_name, parameter_name, month
    """
    monthly_df = spark.sql(monthly_sql)
    monthly_pd = monthly_df.toPandas()
    monthly_pd.to_csv(out_dir / "monthly_seasonal_trends.csv", index=False)
    logger.info(f"Query 2 saved: {len(monthly_pd)} city-month records.")

    # =========================================================================
    # QUERY 3: Daily NAAQS Regulatory Exceedance Rates
    # Standard: PM2.5 > 60 ug/m3, PM10 > 100 ug/m3 (24-hour average)
    # =========================================================================
    logger.info("Executing Query 3: Daily CPCB NAAQS Exceedance Analysis by Station...")
    daily_station_sql = """
    WITH daily_averages AS (
        SELECT 
            station_id,
            station_name,
            city_name,
            state_name,
            parameter_name,
            year,
            month,
            day,
            COUNT(*) AS valid_hours,
            AVG(value) AS daily_avg
        FROM curated_air_quality
        WHERE parameter_name IN ('PM2.5', 'PM10')
        GROUP BY station_id, station_name, city_name, state_name, parameter_name, year, month, day
        HAVING valid_hours >= 16  -- CPCB 16/24 hour completeness rule
    )
    SELECT 
        station_id,
        station_name,
        city_name,
        state_name,
        parameter_name,
        COUNT(*) AS total_monitored_days,
        ROUND(AVG(daily_avg), 2) AS overall_mean_concentration,
        ROUND(PERCENTILE_APPROX(daily_avg, 0.50), 2) AS median_concentration,
        ROUND(PERCENTILE_APPROX(daily_avg, 0.95), 2) AS p95_concentration,
        SUM(CASE 
            WHEN parameter_name = 'PM2.5' AND daily_avg > 60.0 THEN 1
            WHEN parameter_name = 'PM10' AND daily_avg > 100.0 THEN 1
            ELSE 0 
        END) AS naaqs_exceedance_days,
        ROUND(SUM(CASE 
            WHEN parameter_name = 'PM2.5' AND daily_avg > 60.0 THEN 1
            WHEN parameter_name = 'PM10' AND daily_avg > 100.0 THEN 1
            ELSE 0 
        END) * 100.0 / COUNT(*), 2) AS exceedance_percentage
    FROM daily_averages
    GROUP BY station_id, station_name, city_name, state_name, parameter_name
    HAVING total_monitored_days >= 10
    ORDER BY exceedance_percentage DESC, overall_mean_concentration DESC
    """
    exceedance_df = spark.sql(daily_station_sql)
    exceedance_pd = exceedance_df.toPandas()
    exceedance_pd.to_csv(out_dir / "station_naaqs_exceedance.csv", index=False)
    logger.info(f"Query 3 saved: {len(exceedance_pd)} station exceedance profiles.")

    # =========================================================================
    # QUERY 4: Top 25 Most Polluted Stations (PM2.5 Focus)
    # =========================================================================
    logger.info("Executing Query 4: Top 25 Most Polluted Monitoring Stations...")
    top_stations_sql = """
    SELECT 
        station_id,
        station_name,
        city_name,
        state_name,
        COUNT(*) AS reading_count,
        ROUND(AVG(value), 2) AS mean_pm25,
        ROUND(PERCENTILE_APPROX(value, 0.50), 2) AS median_pm25,
        ROUND(PERCENTILE_APPROX(value, 0.95), 2) AS p95_pm25,
        ROUND(MAX(value), 2) AS max_pm25
    FROM curated_air_quality
    WHERE parameter_name = 'PM2.5'
    GROUP BY station_id, station_name, city_name, state_name
    HAVING reading_count >= 200
    ORDER BY mean_pm25 DESC
    LIMIT 25
    """
    top_df = spark.sql(top_stations_sql)
    top_pd = top_df.toPandas()
    top_pd.to_csv(out_dir / "top_polluted_stations_pm25.csv", index=False)
    logger.info("Top 25 Most Polluted Stations:")
    top_df.show(10, truncate=False)

    # Capture Spark Query Execution Plan (Distributed Execution Evidence)
    plan_file = out_dir / "spark_sql_execution_plan.txt"
    with open(plan_file, "w", encoding="utf-8") as f:
        f.write("=== SPARK SQL PHYSICAL PLAN FOR EXCEEDANCE QUERY ===\n")
        f.write(exceedance_df._jdf.queryExecution().toString())
    logger.info(f"Saved Spark execution plan evidence to {plan_file}")

def main():
    parser = argparse.ArgumentParser(description="AirPulse Spark SQL Analytics Engine")
    parser.add_argument("--curated-path", type=str, default="data/hdfs_storage/airpulse/curated/measurements",
                        help="Path to curated parquet dataset")
    parser.add_argument("--output-dir", type=str, default="data/hdfs_storage/airpulse/analytics/tables",
                        help="Destination for analytical tables")
    parser.add_argument("--spark-master", type=str, default="local[*]", help="Spark Master URL")
    args = parser.parse_args()

    builder = (
        SparkSession.builder
        .appName("AirPulse-SparkSQL-Analytics")
        .master(args.spark_master)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "Asia/Kolkata")
    )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    run_analytics(spark, args.curated_path, args.output_dir)
    spark.stop()

if __name__ == "__main__":
    main()
