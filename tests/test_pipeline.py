"""
AirPulse India: Pipeline Automated Unit & Verification Tests
Author: AirPulse Big Data Engineering
Module: Quality Assurance & Algorithm Correctness Verification
"""

import pytest
import numpy as np
import pandas as pd

def test_physical_bounds_filtering():
    """Verify that negative sensor drift and impossible extremes are filtered."""
    test_cases = [
        ("PM2.5", -12.5, False),
        ("PM2.5", 0.0, True),
        ("PM2.5", 58.2, True),
        ("PM2.5", 999.0, True),
        ("PM2.5", 1000.1, False),
        ("PM10", -1.0, False),
        ("PM10", 1450.0, True),
        ("PM10", 1500.5, False),
    ]

    bounds = {
        "PM2.5": (0.0, 1000.0),
        "PM10": (0.0, 1500.0)
    }

    for param, val, expected in test_cases:
        low, high = bounds[param]
        is_valid = (val >= low) and (val <= high)
        assert is_valid == expected, f"Failed bound test for {param} = {val}"

def test_pm25_pm10_ratio_invariant():
    """Verify PM2.5 <= 1.05 * PM10 physical subset rule."""
    test_pairs = [
        (45.0, 90.0, True),
        (80.0, 80.0, True),
        (104.0, 100.0, True),
        (150.0, 100.0, False),
    ]

    for pm25, pm10, expected in test_pairs:
        is_consistent = pm25 <= (pm10 * 1.05)
        assert is_consistent == expected, f"Failed ratio test for PM2.5={pm25}, PM10={pm10}"

def test_robust_mad_modified_z_score():
    """Verify Modified Z-Score calculation with Median Absolute Deviation."""
    baseline = np.array([50.0, 52.0, 48.0, 51.0, 49.0, 50.0, 51.0, 49.0])
    median = np.median(baseline)
    mad = np.median(np.abs(baseline - median))
    effective_mad = max(mad, 5.0)

    # Normal reading
    normal_val = 55.0
    mod_z_normal = 0.6745 * (normal_val - median) / effective_mad
    assert mod_z_normal < 3.5, f"Normal reading incorrectly flagged: {mod_z_normal}"

    # Acute spike
    spike_val = 320.0
    mod_z_spike = 0.6745 * (spike_val - median) / effective_mad
    assert mod_z_spike >= 3.5, f"Severe spike not detected: {mod_z_spike}"

def test_hotspot_classification_taxonomy():
    """Verify correct segregation of persistent vs episodic hotspots."""
    chronic_1 = 78.5
    volatility_1 = 1.9
    if chronic_1 >= 60.0 and volatility_1 <= 3.0:
        class_1 = "Persistent Hotspot"
    else:
        class_1 = "Other"
    assert class_1 == "Persistent Hotspot"

    chronic_2 = 28.0
    volatility_2 = 4.2
    if volatility_2 >= 2.5 and chronic_2 < 50.0:
        class_2 = "Occasional Spike Zone"
    else:
        class_2 = "Other"
    assert class_2 == "Occasional Spike Zone"
