
import json

import numpy as np
import pandas as pd
import pytest

from decisioniq.profiling import (
    TemporalProfiler,
    MulticollinearityProfiler
)


# TEMPORAL TESTS


def test_datetime_detection():

    df = pd.DataFrame({
        "date": pd.date_range(
            "2025-01-01", periods=5
        ),
        "sales": [10, 20, 30, 40, 50]
    })

    result = TemporalProfiler().profile(df)

    assert result["date_columns"] == ["date"]


def test_temporal_missing_days():

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-01-03",
            "2025-01-05"
        ])
    })

    result = TemporalProfiler().profile(df)

    coverage = result["columns"][0]["coverage"]

    assert coverage["calendar_days"] == 5
    assert coverage["unobserved_days"] == 2
    assert coverage["day_coverage_pct"] == 60


def test_repeated_timestamps():

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-01-01",
            "2025-01-02"
        ])
    })

    result = TemporalProfiler().profile(df)

    assert (
        result["columns"][0]["frequency"]
        ["repeated_timestamp_records"] == 1
    )


def test_invalid_dates():

    df = pd.DataFrame({
        "date": [
            "2025-01-01",
            "invalid",
            None
        ]
    })

    profiler = TemporalProfiler({
        "date_columns": ["date"]
    })

    column = profiler.profile(df)["columns"][0]

    assert column["valid_dates"] == 1
    assert column["invalid_dates"] == 1
    assert column["missing_dates"] == 1


def test_regular_daily_frequency():

    df = pd.DataFrame({
        "date": pd.date_range(
            "2025-01-01", periods=10
        )
    })

    result = TemporalProfiler().profile(df)

    assert (
        result["columns"][0]["frequency"]
        ["inferred_frequency"] == "D"
    )


def test_no_temporal_columns():

    df = pd.DataFrame({
        "sales": [100, 200, 300]
    })

    result = TemporalProfiler().profile(df)

    assert result["date_columns_detected"] == 0


def test_temporal_monthly_counts():

    df = pd.DataFrame({
        "date": pd.date_range(
            "2025-01-30", periods=4
        )
    })

    result = TemporalProfiler().profile(df)

    counts = result["columns"][0]["volume"][
        "monthly_records"
    ]

    assert counts["2025-01"] == 2
    assert counts["2025-02"] == 2


def test_temporal_json_serialization():

    df = pd.DataFrame({
        "date": pd.date_range(
            "2025-01-01", periods=5
        )
    })

    result = TemporalProfiler().profile(df)

    json.dumps(result, allow_nan=False)


def test_temporal_data_unchanged():

    df = pd.DataFrame({
        "date": pd.date_range(
            "2025-01-01", periods=5
        )
    })

    original = df.copy(deep=True)

    TemporalProfiler().profile(df)

    pd.testing.assert_frame_equal(df, original)


def test_temporal_empty_dataframe():

    with pytest.raises(ValueError):

        TemporalProfiler().profile(
            pd.DataFrame()
        )


# MULTICOLLINEARITY TESTS


def test_perfect_collinearity():

    df = pd.DataFrame({
        "x": np.arange(20),
        "y": np.arange(20) * 2
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["summary"]["rank_deficient"]

    assert all(
        c["severity"] == "perfect_collinearity"
        for c in result["columns"]
    )


def test_uncorrelated_predictors():

    df = pd.DataFrame({
        "x": [-1, -1, 1, 1] * 10,
        "y": [-1, 1, -1, 1] * 10
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["columns"][0]["vif"] == pytest.approx(1)


def test_high_multicollinearity():

    rng = np.random.default_rng(42)

    x = rng.normal(size=200)

    df = pd.DataFrame({
        "x": x,
        "y": x + rng.normal(
            scale=0.01, size=200
        )
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["columns"][0]["vif"] > 10


def test_predictors_not_configured():

    df = pd.DataFrame({
        "x": [1, 2, 3]
    })

    result = MulticollinearityProfiler().profile(df)

    assert (
        result["status"]
        == "predictors_not_configured"
    )


def test_missing_predictor():

    df = pd.DataFrame({
        "x": [1, 2, 3]
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["status"] == "predictors_missing"


def test_multicollinearity_constant_column():

    df = pd.DataFrame({
        "x": np.arange(20),
        "y": np.arange(20) ** 2,
        "constant": [1] * 20
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": [
            "x", "y", "constant"
        ]
    })

    result = profiler.profile(df)

    assert (
        result["summary"]["constant_columns"]
        == ["constant"]
    )


def test_multicollinearity_missing_rows():

    df = pd.DataFrame({
        "x": [1, 2, 3, 4, None],
        "y": [2, 5, 3, 7, 9]
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["summary"]["excluded_rows"] == 1


def test_multicollinearity_insufficient_data():

    df = pd.DataFrame({
        "x": [1, 2],
        "y": [3, 4]
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    result = profiler.profile(df)

    assert result["status"] == "insufficient_data"


def test_multicollinearity_json_serialization():

    df = pd.DataFrame({
        "x": np.arange(20),
        "y": np.arange(20) * 2
    })

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    json.dumps(
        profiler.profile(df),
        allow_nan=False
    )


def test_multicollinearity_data_unchanged():

    df = pd.DataFrame({
        "x": np.arange(20),
        "y": np.arange(20) ** 2
    })

    original = df.copy(deep=True)

    profiler = MulticollinearityProfiler({
        "predictor_columns": ["x", "y"]
    })

    profiler.profile(df)

    pd.testing.assert_frame_equal(df, original)
