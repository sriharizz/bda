"""
Export Spark & HDFS Analytics Data to JSON for High-Performance React Frontend
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data/hdfs_storage/airpulse/analytics/tables")
OUT_DIR = Path("frontend/src/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Exporting analytics data to frontend/src/data/...")

# 1. Station classification
hotspots = pd.read_csv(DATA_DIR / "station_hotspot_classification.csv")
hotspots['latitude'] = pd.to_numeric(hotspots['latitude'], errors='coerce')
hotspots['longitude'] = pd.to_numeric(hotspots['longitude'], errors='coerce')
hotspots = hotspots.dropna(subset=['latitude', 'longitude']).copy()
hotspots['short_name'] = hotspots['station_name'].apply(lambda x: str(x).split(',')[0].strip())
hotspots = hotspots.fillna({
    'mean_pm25': 0.0,
    'chronic_exceedance_pct': 0.0,
    'volatility_ratio': 1.0,
    'detected_spikes': 0
})

stations_list = hotspots[[
    'station_id', 'station_name', 'short_name', 'city_name', 'state_name',
    'latitude', 'longitude', 'mean_pm25', 'chronic_exceedance_pct',
    'volatility_ratio', 'detected_spikes', 'classification', 'color_code'
]].to_dict(orient='records')

with open(OUT_DIR / "stations.json", "w") as f:
    json.dump(stations_list, f, indent=2)

print(f"Exported {len(stations_list)} stations to stations.json")

# 2. City Summaries
cities = hotspots['city_name'].dropna().unique()
city_summaries = {}

for city in cities:
    sub = hotspots[hotspots['city_name'] == city]
    if sub.empty:
        continue
    cleanest = sub.sort_values(by='mean_pm25').iloc[0]
    worst = sub.sort_values(by='mean_pm25', ascending=False).iloc[0]
    city_summaries[city] = {
        'city': city,
        'state': sub['state_name'].iloc[0] if 'state_name' in sub.columns else '',
        'station_count': int(len(sub)),
        'mean_pm25': round(float(sub['mean_pm25'].mean()), 1),
        'cleanest_station': {
            'name': cleanest['short_name'],
            'mean_pm25': round(float(cleanest['mean_pm25']), 1),
            'class': cleanest['classification']
        },
        'worst_station': {
            'name': worst['short_name'],
            'mean_pm25': round(float(worst['mean_pm25']), 1),
            'chronic_exceedance_pct': round(float(worst['chronic_exceedance_pct']), 1),
            'class': worst['classification']
        },
        'persistent_hotspots': int((sub['classification'].str.contains('Persistent')).sum()),
        'occasional_spikes': int((sub['classification'].str.contains('Occasional')).sum()),
        'compliant_count': int((sub['classification'].str.contains('Compliant')).sum())
    }

with open(OUT_DIR / "city_summaries.json", "w") as f:
    json.dump(city_summaries, f, indent=2)

print(f"Exported {len(city_summaries)} city summaries to city_summaries.json")

# 3. Diurnal trends (Hourly 0-23 by city)
diurnal = pd.read_csv(DATA_DIR / "diurnal_hourly_trends.csv")
diurnal_map = {}

for city in diurnal['city_name'].unique():
    c_sub = diurnal[diurnal['city_name'] == city]
    hours_data = []
    for h in range(24):
        h_pm25 = c_sub[(c_sub['hour'] == h) & (c_sub['parameter_name'] == 'PM2.5')]
        h_pm10 = c_sub[(c_sub['hour'] == h) & (c_sub['parameter_name'] == 'PM10')]
        
        pm25_val = round(float(h_pm25['mean_value'].iloc[0]), 1) if (not h_pm25.empty and pd.notna(h_pm25['mean_value'].iloc[0])) else 0.0
        pm10_val = round(float(h_pm10['mean_value'].iloc[0]), 1) if (not h_pm10.empty and pd.notna(h_pm10['mean_value'].iloc[0])) else 0.0
        
        hours_data.append({
            'hour': f"{h:02d}:00",
            'hour_num': h,
            'pm25': pm25_val,
            'pm10': pm10_val,
        })
    diurnal_map[city] = hours_data

with open(OUT_DIR / "diurnal_trends.json", "w") as f:
    json.dump(diurnal_map, f, indent=2)

print(f"Exported diurnal trends for {len(diurnal_map)} cities to diurnal_trends.json")

# 4. Spikes log (Top 50 acute anomalies)
spikes = pd.read_csv(DATA_DIR / "spike_anomalies_log.csv")
spikes = spikes.fillna({
    'city_name': 'Unknown',
    'daily_pm25': 0.0,
    'baseline_median': 0.0,
    'modified_z_score': 0.0,
    'spike_ratio': 1.0,
    'severity_tier': 'Moderate'
})
spikes = spikes.replace({np.nan: None})

spikes_top = spikes.sort_values(by='modified_z_score', ascending=False).head(50)[[
    'date', 'station_name', 'city_name', 'daily_pm25', 'baseline_median', 'modified_z_score', 'spike_ratio', 'severity_tier'
]].to_dict(orient='records')

with open(OUT_DIR / "spikes_recent.json", "w") as f:
    json.dump(spikes_top, f, indent=2)

print(f"Exported {len(spikes_top)} top spikes to spikes_recent.json")

# 5. System & Spark Architecture Metadata
plan_path = DATA_DIR / "spark_sql_execution_plan.txt"
plan_snippet = ""
if plan_path.exists():
    with open(plan_path) as f:
        plan_snippet = f.read()[:2000]

bigdata_meta = {
    'total_raw_rows': 11988849,
    'total_stations': 558,
    'active_sensor_stations': len(hotspots),
    'storage_backend': 'Apache Hadoop 3.3.6 HDFS',
    'compute_engine': 'Apache Spark 3.5.1 (PySpark)',
    'curated_partitions': 'year=2024/month=01,07,11 (Snappy Parquet)',
    'invariants_enforced': [
        'CPCB Physical Limits: 0 <= PM2.5 <= 1000 µg/m³',
        'Physical Particle Invariant: PM2.5 <= 1.05 * PM10 (1,065 optical refraction errors flagged)',
        'Temporal Deduplication on (station_id, timestamp)',
        'Robust Hoaglin-Iglewicz MAD Outlier Engine (14-day rolling baseline, M_i >= 3.5)'
    ],
    'execution_plan_snippet': plan_snippet
}

with open(OUT_DIR / "bigdata_meta.json", "w") as f:
    json.dump(bigdata_meta, f, indent=2)

print("Export completed successfully!")
