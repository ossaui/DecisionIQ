
import json

import numpy as np
import pandas as pd
import pytest

from decisioniq.profiling import UniversalProfiler
from decisioniq.utils.config import load_config


@pytest.fixture
def sample_data():

    return pd.DataFrame({

        "sales": np.arange(1, 21) * 100,

        "cost": np.arange(1, 21) * 60,

        "category": ["A", "B"] * 10,

        "date": pd.date_range(
            "2025-01-01", periods=20
        )
    })


def test_universal_all_modules(sample_data):

    report = UniversalProfiler().profile(
        sample_data
    )

    assert report["execution"]["total_modules"] == 7

    assert report["execution"]["completed_modules"] == 7

    assert report["execution"]["failed_modules"] == 0


def test_universal_dataset_dimensions(sample_data):

    report = UniversalProfiler().profile(
        sample_data
    )

    assert report["dataset"]["row_count"] == 20

    assert report["dataset"]["column_count"] == 4


def test_universal_disabled_module(sample_data):

    config = load_config()

    config["profiling"]["outliers"]["enabled"] = False

    report = UniversalProfiler(config).profile(
        sample_data
    )

    assert (
        report["modules"]["outliers"]["status"]
        == "skipped"
    )

    assert report["execution"]["skipped_modules"] == 1


def test_universal_empty_dataframe():

    with pytest.raises(ValueError):

        UniversalProfiler().profile(
            pd.DataFrame()
        )


def test_universal_invalid_input():

    with pytest.raises(TypeError):

        UniversalProfiler().profile(
            [1, 2, 3]
        )


def test_universal_duplicate_columns():

    df = pd.DataFrame(
        [[1, 2], [3, 4]],
        columns=["x", "x"]
    )

    with pytest.raises(ValueError):

        UniversalProfiler().profile(df)


def test_universal_json_serialization(sample_data):

    report = UniversalProfiler().profile(
        sample_data
    )

    json.dumps(
        report,
        allow_nan=False
    )


def test_universal_metadata(sample_data):

    metadata = {
        "file_name": "sample.csv",
        "file_hash": "test_hash"
    }

    report = UniversalProfiler().profile(
        sample_data,
        metadata=metadata
    )

    assert (
        report["source"]["file_name"]
        == "sample.csv"
    )


def test_universal_data_unchanged(sample_data):

    original = sample_data.copy(deep=True)

    UniversalProfiler().profile(
        sample_data
    )

    pd.testing.assert_frame_equal(
        sample_data,
        original
    )


def test_universal_quality_indicators():

    df = pd.DataFrame({
        "x": [1, 2, None, 4],
        "y": [1, 2, 3, 4]
    })

    report = UniversalProfiler().profile(df)

    quality = report["quality_indicators"]

    assert quality["missing_cells"] == 1

    assert (
        quality["completeness_percentage"]
        == pytest.approx(87.5)
    )


def test_universal_save_report(
    sample_data, tmp_path
):

    profiler = UniversalProfiler()

    report = profiler.profile(sample_data)

    path = profiler.save_report(
        report,
        tmp_path / "report.json"
    )

    assert path.exists()

    saved = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert saved["dataset"]["row_count"] == 20


def test_universal_fault_isolation(
    sample_data, monkeypatch
):

    class BrokenProfiler:

        def __init__(self, config=None):
            pass

        def profile(self, df):

            raise RuntimeError("Test failure")

    monkeypatch.setitem(
        UniversalProfiler.MODULES,
        "outliers",
        BrokenProfiler
    )

    config = load_config()

    config["profiling"]["execution"] = {
        "fail_fast": False
    }

    report = UniversalProfiler(config).profile(
        sample_data
    )

    assert report["status"] == "partial_success"

    assert report["execution"]["failed_modules"] == 1

    assert report["execution"]["completed_modules"] == 6


def test_universal_fail_fast(
    sample_data, monkeypatch
):

    class BrokenProfiler:

        def __init__(self, config=None):
            pass

        def profile(self, df):

            raise RuntimeError("Test failure")

    monkeypatch.setitem(
        UniversalProfiler.MODULES,
        "outliers",
        BrokenProfiler
    )

    config = load_config()

    config["profiling"]["execution"] = {
        "fail_fast": True
    }

    with pytest.raises(RuntimeError):

        UniversalProfiler(config).profile(
            sample_data
        )


def test_universal_configuration_unchanged(
    sample_data
):

    from copy import deepcopy

    config = load_config()

    original = deepcopy(config)

    UniversalProfiler(config).profile(
        sample_data
    )

    assert config == original
