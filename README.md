# AirPulse India: Distributed Air Pollution Spike & Hotspot Intelligence

A reproducible Big Data Analytics platform for distributed ingestion, cleaning, analytical querying, and explainable anomaly intelligence of Indian ambient air quality measurements using **Hadoop HDFS**, **Apache Spark / PySpark**, **Spark SQL**, and **Streamlit**.

---

## 1. Problem Statement & Motivation
Urban India experiences severe, complex air quality degradation characterized by:
1. **Acute Episodic Spikes**: Short-lived, extreme pollution surges triggered by agricultural stubble burning, festival fireworks (e.g., Diwali), or industrial flaring.
2. **Persistent Hotspots**: Monitoring stations that suffer continuous, day-in-day-out chronic exceedance of statutory limits due to proximity to traffic arteries or heavy industry.
3. **Temporal Inversions**: Strong diurnal cycles (morning and nighttime inversion peaks) and seasonal swings (winter smog vs. monsoon washouts).

Standard single-machine tools struggle with millions of hourly measurements spanning hundreds of continuous ambient air quality monitoring stations (CAAQMS). **AirPulse India** solves this by establishing a scalable, distributed HDFS-Spark architecture to disaggregate episodic spikes from chronic hotspots with mathematical explainability.

---

## 2. Dataset Reference & Attribution
- **Dataset Source**: [xKDR Forum Air-Quality-Database](https://github.com/xKDR/Air-Quality-Database)
- **Primary Monitoring Networks**:
  - Central Pollution Control Board (CPCB), Ministry of Environment, Forest and Climate Change (CAAQMS network).
  - US Department of State (AirNow Embassy/Consulate Monitors).
- **Licence**: [Creative Commons Attribution 4.0 International (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **Coverage**: 553+ monitoring stations across India, hourly timestamped observations in Indian Standard Time (IST).
- **Core Parameters**: $\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{Ozone}$, $\text{NH}_3$ ($\mu g/m^3$).

---

## 3. Distributed Architecture

```
                       +-----------------------------------+
                       |    Raw xKDR / CPCB Data Slice     |
                       | (CSVs/Parquet via Cloudflare R2)  |
                       +-----------------+-----------------+
                                         | Ingest (scripts/00_fetch_xkdr_slice.py)
                                         v
                         +-------------------------------+
                         |      Hadoop HDFS Storage      |
                         |     hdfs://namenode:9000      |
                         |  /airpulse/raw/measurements/  |
                         +---------------+---------------+
                                         |
                                         v
                     +---------------------------------------+
                     |       Apache Spark / PySpark Engine   |
                     | - Data Validation & Physical Capping  |
                     | - Diurnal (Hour) & Seasonal Patterns  |
                     | - Rolling 14-Day Robust MAD Threshold |
                     | - Hotspot vs Spike Zone Classifier    |
                     +-------------------+-------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
        +-----------------------------+     +-------------------------------+
        |    HDFS Curated Storage     |     |       Spark SQL Queries       |
        |  /airpulse/curated/parquet  |     |   (Aggregations & Rankings)   |
        +--------------+--------------+     +---------------+---------------+
                       |                                    |
                       +-----------------+------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   Visualizations & Reports    |
                         | - Matplotlib/Seaborn Plots    |
                         | - Summary KPI Tables (CSV/MD) |
                         | - Streamlit Web Dashboard     |
                         +-------------------------------+
```

---

## 4. Documented Data Quality & Validation Rules
1. **Sensor Zero-Drift & Negative Bound**: Discard readings with negative pollutant concentrations (sensor baseline calibration drift).
2. **Physical Environmental Bounds**:
   - $0.0 \le \text{PM}_{2.5} \le 1000.0\ \mu g/m^3$
   - $0.0 \le \text{PM}_{10} \le 1500.0\ \mu g/m^3$
   - Extremely unrealistic sensor spikes exceeding these caps are pruned.
3. **Physical Invariant Check**: Because $\text{PM}_{2.5}$ particles are a subset of $\text{PM}_{10}$, enforce $\text{PM}_{2.5} \le 1.05 \times \text{PM}_{10}$ (with 5% field tolerance). Violations indicate uncalibrated optical sensors.
4. **CPCB Completeness Rule**: Station-day aggregations require at least 16 valid hourly readings out of 24 ($\ge 66.7\%$ data availability).
5. **Temporal Deduplication**: Deduplication on `(station_id, parameter_name, collected_at)`.

---

## 5. Statistical Intelligence Algorithms

### A. Explainable Anomaly Detection (Modified Z-Score via Rolling MAD)
Traditional Z-scores fail during severe pollution seasons because extreme values artificially inflate both the mean and standard deviation. AirPulse uses a robust non-parametric baseline:
$$\text{Median}_i = \text{median}(X_{t-14D \dots t})$$
$$\text{MAD}_i = \text{median}(|X_j - \text{Median}_i|)$$
$$\text{Modified Z-score } M_i = \frac{0.6745 \cdot (X_i - \text{Median}_i)}{\max(\text{MAD}_i, 5.0)}$$
- **Acute Spike Trigger**: $M_i \ge 3.5$ AND $X_i > 60\ \mu g/m^3$ (CPCB NAAQS Standard).
- **Explainability Metrics**: Reports baseline median, excess concentration, and spike ratio ($X_i / \text{baseline}$).

### B. Hotspot vs. Spike Zone Disaggregation
Stations are classified on a two-dimensional matrix:
1. **Chronic Exceedance % ($C$)**: Percentage of days exceeding the 24-hr NAAQS safe limit ($60\ \mu g/m^3$).
2. **Spike Volatility Ratio ($V$)**: $P_{95} / \text{Median}$.
- **Persistent Hotspots (Class I)**: $C \ge 60\%$ and $V \le 3.0$ (chronic vehicular/industrial sinks).
- **Occasional Spike Zones (Class II)**: $C < 50\%$ and $V \ge 2.5$ (episodic events like stubble burning or fireworks).
- **Compliant Zones (Class IV)**: $C < 20\%$ (consistently clean air).

---

## 6. Setup & Execution Instructions

### Option A: Local PySpark & HDFS Staging (Fastest, zero setup)
```powershell
# 1. Activate the environment
.\.venv\Scripts\Activate.ps1

# 2. Run unit tests to verify algorithm logic
pytest tests/ -v

# 3. Execute the full end-to-end distributed pipeline
python run_pipeline.py

# 4. Launch the interactive intelligence dashboard
streamlit run dashboard/app.py
```

### Option B: Docker Compose Multi-Container Cluster
Ensure Docker Desktop is running, then execute:
```powershell
# 1. Start Hadoop NameNode, DataNode, Spark Master, and Worker
docker compose up -d

# 2. Verify containers are healthy
docker compose ps

# 3. Access Web Interfaces:
# - Hadoop HDFS NameNode: http://localhost:9870
# - Spark Master UI:     http://localhost:8080
# - AirPulse Dashboard:    http://localhost:8501
```

---

## 7. Submission Evidence Checklist

For your Big Data Analytics submission, capture the following generated artifacts:
1. **HDFS Storage Evidence**:
   - Run `python scripts/01_hdfs_manager.py` to inspect the generated `/airpulse/` HDFS hierarchy.
2. **Spark SQL Execution Plan**:
   - Review `data/hdfs_storage/airpulse/analytics/tables/spark_sql_execution_plan.txt` demonstrating distributed physical plans (`Scan parquet`, `HashAggregate`, `Exchange hashpartitioning`).
3. **Execution Logs**:
   - Terminal logs generated by `run_pipeline.py` displaying total records processed, out-of-bounds drops, and execution timings.
4. **Generated Figures**:
   - `reports/figures/fig1_diurnal_hourly_pattern.png`
   - `reports/figures/fig2_monthly_seasonality.png`
   - `reports/figures/fig3_hotspot_vs_spike_quadrant.png`
   - `reports/figures/fig4_delhi_winter_spike_timeline.png`
   - `reports/figures/fig5_city_exceedance_comparison.png`
