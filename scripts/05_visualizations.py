"""
AirPulse India: Publication Visualizations & Reporting Module
Author: AirPulse Big Data Engineering
Module: Figures and Summary Evidence Generator

Generates high-resolution analytical charts from HDFS analytical tables:
1. fig1_diurnal_hourly_pattern.png: 24-hour diurnal PM2.5 cycles across metros.
2. fig2_monthly_seasonality.png: Monthly seasonal contrast (Winter smog vs Monsoon washout).
3. fig3_hotspot_vs_spike_quadrant.png: 2D Hotspot vs Spike volatility taxonomy.
4. fig4_delhi_winter_spike_timeline.png: Explainable rolling baseline with flagged anomaly spikes.
5. fig5_city_exceedance_comparison.png: Cross-city NAAQS compliance comparison.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AirPulse-Visualizations")

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300
})

CITY_COLORS = {
    "Delhi": "#e63946",
    "Lucknow": "#d62828",
    "Patna": "#f77f00",
    "Kolkata": "#0077b6",
    "Mumbai": "#023e8a",
    "Hyderabad": "#588157",
    "Bengaluru": "#2a9d8f"
}

def generate_visualizations(tables_dir: Path, figures_dir: Path):
    figures_dir.mkdir(parents=True, exist_ok=True)

    # FIGURE 1: Diurnal Hourly Cycle
    diurnal_file = tables_dir / "diurnal_hourly_trends.csv"
    if diurnal_file.exists():
        logger.info(f"Generating Figure 1 from {diurnal_file}...")
        df_diurnal = pd.read_csv(diurnal_file)
        pm25_diurnal = df_diurnal[df_diurnal["parameter_name"] == "PM2.5"]

        fig, ax = plt.subplots(figsize=(10, 5))
        for city in ["Delhi", "Kolkata", "Mumbai", "Bengaluru", "Hyderabad"]:
            sub = pm25_diurnal[pm25_diurnal["city_name"] == city]
            if not sub.empty:
                color = CITY_COLORS.get(city, "#333333")
                ax.plot(sub["hour"], sub["mean_value"], marker="o", markersize=4, 
                        linewidth=2.2, label=city, color=color)

        ax.axhline(60, color="gray", linestyle="--", linewidth=1.2, label="CPCB NAAQS 24-hr Standard (60 µg/m³)")
        ax.set_title("Figure 1: Diurnal (Hourly) PM2.5 Concentrations Across Indian Metros")
        ax.set_xlabel("Hour of Day (IST, 00:00 - 23:00)")
        ax.set_ylabel("Mean PM2.5 (µg/m³)")
        ax.set_xticks(range(0, 24, 2))
        ax.set_xlim(-0.5, 23.5)
        ax.legend(frameon=True, facecolor="white", edgecolor="none")
        plt.tight_layout()
        fig.savefig(figures_dir / "fig1_diurnal_hourly_pattern.png")
        plt.close(fig)
        logger.info("Saved fig1_diurnal_hourly_pattern.png")

    # FIGURE 2: Monthly Seasonality Trends
    monthly_file = tables_dir / "monthly_seasonal_trends.csv"
    if monthly_file.exists():
        logger.info(f"Generating Figure 2 from {monthly_file}...")
        df_monthly = pd.read_csv(monthly_file)
        pm25_monthly = df_monthly[df_monthly["parameter_name"] == "PM2.5"]

        fig, ax = plt.subplots(figsize=(10, 5))
        for city in ["Delhi", "Kolkata", "Mumbai", "Bengaluru", "Hyderabad"]:
            sub = pm25_monthly[pm25_monthly["city_name"] == city]
            if not sub.empty:
                color = CITY_COLORS.get(city, "#333333")
                ax.plot(sub["month"], sub["monthly_mean"], marker="s", markersize=5, 
                        linewidth=2.2, label=city, color=color)

        ax.axhline(60, color="gray", linestyle="--", linewidth=1.2, label="CPCB NAAQS Safe Limit (60 µg/m³)")
        ax.set_title("Figure 2: Seasonal Pollution Trajectories (Winter Peak vs. Monsoon Washout)")
        ax.set_xlabel("Month of Year")
        ax.set_ylabel("Monthly Mean PM2.5 (µg/m³)")
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        present_months = sorted(pm25_monthly["month"].unique())
        ax.set_xticks(present_months)
        ax.set_xticklabels([month_labels[m-1] for m in present_months])
        ax.legend(frameon=True, facecolor="white", edgecolor="none")
        plt.tight_layout()
        fig.savefig(figures_dir / "fig2_monthly_seasonality.png")
        plt.close(fig)
        logger.info("Saved fig2_monthly_seasonality.png")

    # FIGURE 3: Hotspot vs Spike Quadrant Scatter Plot
    hotspot_file = tables_dir / "station_hotspot_classification.csv"
    if hotspot_file.exists():
        logger.info(f"Generating Figure 3 from {hotspot_file}...")
        df_hotspot = pd.read_csv(hotspot_file)

        fig, ax = plt.subplots(figsize=(10, 6.5))
        palette = {
            "Persistent Hotspot (Chronic Sink)": "#d90429",
            "Occasional Spike Zone (Episodic)": "#f77f00",
            "Moderate Hotspot": "#fcbf49",
            "Compliant / Low Exposure": "#2b9348"
        }

        sns.scatterplot(
            data=df_hotspot,
            x="chronic_exceedance_pct",
            y="volatility_ratio",
            hue="classification",
            palette=palette,
            size="mean_pm25",
            sizes=(30, 250),
            alpha=0.85,
            edgecolor="black",
            linewidth=0.5,
            ax=ax
        )

        ax.axvline(50, color="black", linestyle=":", alpha=0.5)
        ax.axhline(2.5, color="black", linestyle=":", alpha=0.5)

        ax.text(75, 4.2, "QUADRANT I:\nHigh Chronic Exceedance\n+ High Volatility", 
                ha="center", fontsize=9, alpha=0.6, weight="bold")
        ax.text(75, 1.6, "QUADRANT II (Persistent Hotspots):\nChronic Sinks (Continuous Exceedance)", 
                ha="center", fontsize=9, color="#d90429", weight="bold")
        ax.text(25, 4.2, "QUADRANT III (Occasional Spike Zones):\nLow Baseline + Acute Episodic Spikes", 
                ha="center", fontsize=9, color="#f77f00", weight="bold")
        ax.text(25, 1.6, "QUADRANT IV:\nCompliant Air Attainment Zones", 
                ha="center", fontsize=9, color="#2b9348", weight="bold")

        ax.set_title("Figure 3: Disaggregation Matrix — Persistent Hotspots vs. Occasional Spike Zones")
        ax.set_xlabel("Chronic Exposure (% of Monitored Days Exceeding 60 µg/m³)")
        ax.set_ylabel("Spike Volatility Ratio (P95 / Median Concentration)")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
        plt.tight_layout()
        fig.savefig(figures_dir / "fig3_hotspot_vs_spike_quadrant.png")
        plt.close(fig)
        logger.info("Saved fig3_hotspot_vs_spike_quadrant.png")

    # FIGURE 4: Explainable Spike Timeline
    spike_file = tables_dir / "spike_anomalies_log.csv"
    if spike_file.exists() and hotspot_file.exists():
        logger.info(f"Generating Figure 4 from {spike_file}...")
        df_spikes = pd.read_csv(spike_file)
        if not df_spikes.empty:
            focal_station = df_spikes["station_id"].iloc[0]
            focal_name = df_spikes[df_spikes["station_id"] == focal_station]["station_name"].iloc[0]
            station_spikes = df_spikes[df_spikes["station_id"] == focal_station].copy()
            station_spikes["date"] = pd.to_datetime(station_spikes["date"])

            fig, ax = plt.subplots(figsize=(11, 4.8))
            ax.plot(station_spikes["date"], station_spikes["baseline_median"], 
                    label="14-Day Rolling Median Baseline", color="#0077b6", linewidth=2.0)
            ax.plot(station_spikes["date"], station_spikes["daily_pm25"], 
                    label="Actual Daily Mean PM2.5", color="#333333", alpha=0.5, linestyle="--")

            ax.scatter(station_spikes["date"], station_spikes["daily_pm25"], 
                       color="#d90429", s=70, zorder=5, label="Flagged Acute Anomaly (MAD Mod-Z >= 3.5)")

            ax.axhline(60, color="green", linestyle=":", linewidth=1.2, label="CPCB NAAQS Limit (60 µg/m³)")
            ax.set_title(f"Figure 4: Explainable Robust Anomaly Spikes at {focal_name}")
            ax.set_xlabel("Date")
            ax.set_ylabel("PM2.5 Concentration (µg/m³)")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            ax.legend(frameon=True, facecolor="white", loc="upper left")
            plt.tight_layout()
            fig.savefig(figures_dir / "fig4_delhi_winter_spike_timeline.png")
            plt.close(fig)
            logger.info("Saved fig4_delhi_winter_spike_timeline.png")

    # FIGURE 5: City Exceedance Comparison Bar Chart
    exceedance_file = tables_dir / "station_naaqs_exceedance.csv"
    if exceedance_file.exists():
        logger.info(f"Generating Figure 5 from {exceedance_file}...")
        df_exc = pd.read_csv(exceedance_file)
        pm25_exc = df_exc[df_exc["parameter_name"] == "PM2.5"]
        
        city_summary = (
            pm25_exc.groupby("city_name")
            .agg(
                mean_exceedance=("exceedance_percentage", "mean"),
                avg_concentration=("overall_mean_concentration", "mean"),
                station_count=("station_id", "count")
            )
            .sort_values("mean_exceedance", ascending=False)
            .reset_index()
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(city_summary["city_name"], city_summary["mean_exceedance"], 
                      color="#d62828", edgecolor="black", alpha=0.85)

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{yval:.1f}%", 
                    ha="center", va="bottom", fontsize=9, weight="bold")

        ax.set_title("Figure 5: Percentage of Days Exceeding CPCB NAAQS Standard (60 µg/m³) by City")
        ax.set_ylabel("Mean Station Exceedance Rate (%)")
        ax.set_xlabel("City")
        ax.set_ylim(0, 105)
        plt.tight_layout()
        fig.savefig(figures_dir / "fig5_city_exceedance_comparison.png")
        plt.close(fig)
        logger.info("Saved fig5_city_exceedance_comparison.png")

    logger.info("All analytical figures generated successfully in reports/figures/")

def main():
    parser = argparse.ArgumentParser(description="AirPulse Visualizations Engine")
    parser.add_argument("--tables-dir", type=str, default="data/hdfs_storage/airpulse/analytics/tables")
    parser.add_argument("--figures-dir", type=str, default="reports/figures")
    args = parser.parse_args()

    generate_visualizations(Path(args.tables_dir), Path(args.figures_dir))

if __name__ == "__main__":
    main()
