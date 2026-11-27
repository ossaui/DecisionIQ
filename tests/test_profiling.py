
import pandas as pd
import pytest

from decisioniq.profiling import StructuralProfiler


@pytest.fixture
def profiler():
    return StructuralProfiler()


from decisioniq.profiling import RelationshipProfiler


def test_perfect_positive_correlation():

    df = pd.DataFrame({
        "x": list(range(20)),
        "y": [i * 2 for i in range(20)]
    })

    result = RelationshipProfiler().profile(df)

    pearson = next(
        r for r in result["numeric_relationships"]
        if r["method"] == "pearson"
    )

    assert pearson["coefficient"] == pytest.approx(1)


def test_perfect_negative_correlation():

    df = pd.DataFrame({
        "x": list(range(20)),
        "y": list(range(20, 0, -1))
    })

    result = RelationshipProfiler().profile(df)

    pearson = next(
        r for r in result["numeric_relationships"]
        if r["method"] == "pearson"
    )

    assert pearson["coefficient"] == pytest.approx(-1)


def test_spearman_monotonic_relationship():

    df = pd.DataFrame({
        "x": list(range(1, 21)),
        "y": [i ** 3 for i in range(1, 21)]
    })

    result = RelationshipProfiler().profile(df)

    spearman = next(
        r for r in result["numeric_relationships"]
        if r["method"] == "spearman"
    )

    assert spearman["coefficient"] == pytest.approx(1)


def test_kendall_relationship():

    df = pd.DataFrame({
        "x": list(range(20)),
        "y": list(range(20))
    })

    result = RelationshipProfiler().profile(df)

    kendall = next(
        r for r in result["numeric_relationships"]
        if r["method"] == "kendall"
    )

    assert kendall["coefficient"] == pytest.approx(1)


def test_categorical_association():

    df = pd.DataFrame({
        "a": ["A"] * 50 + ["B"] * 50,
        "b": ["X"] * 50 + ["Y"] * 50
    })

    result = RelationshipProfiler().profile(df)

    association = result[
        "categorical_relationships"
    ][0]

    assert association["cramers_v"] == pytest.approx(1)


def test_multiple_testing_correction():

    profiler = RelationshipProfiler()

    results = [
        {"p_value": 0.01},
        {"p_value": 0.04},
        {"p_value": 0.20}
    ]

    adjusted = profiler.adjust_pvalues(results)

    assert adjusted[0]["adjusted_p_value"] == pytest.approx(
        0.03
    )

    assert adjusted[1]["adjusted_p_value"] == pytest.approx(
        0.06
    )


def test_constant_relationship_column():

    df = pd.DataFrame({
        "x": list(range(20)),
        "constant": [10] * 20
    })

    result = RelationshipProfiler().profile(df)

    assert result["numeric_relationships"] == []


def test_relationship_excluded_columns():

    df = pd.DataFrame({
        "id": list(range(20)),
        "sales": list(range(20))
    })

    profiler = RelationshipProfiler({
        "excluded_columns": ["id"]
    })

    result = profiler.profile(df)

    assert result["numeric_columns"] == ["sales"]


def test_relationship_insufficient_observations():

    df = pd.DataFrame({
        "x": [1, 2, 3],
        "y": [3, 4, 5]
    })

    result = RelationshipProfiler().profile(df)

    assert result["numeric_relationships"] == []


def test_relationship_json_serialization():

    df = pd.DataFrame({
        "x": list(range(20)),
        "y": list(range(20))
    })

    result = RelationshipProfiler().profile(df)

    json.dumps(result, allow_nan=False)


def test_relationship_data_unchanged():

    df = pd.DataFrame({
        "x": list(range(20)),
        "y": list(range(20))
    })

    original = df.copy(deep=True)

    RelationshipProfiler().profile(df)

    pd.testing.assert_frame_equal(df, original)


def test_sparse_chi_square_table():

    df = pd.DataFrame({
        "a": ["A"] * 19 + ["B"],
        "b": ["X"] * 19 + ["Y"]
    })

    result = RelationshipProfiler().profile(df)

    association = result[
        "categorical_relationships"
    ][0]

    assert association["assumptions_met"] is False

    assert association["adjusted_p_value"] is None


def test_relationship_column_limit():

    df = pd.DataFrame({
        "a": list(range(20)),
        "b": list(range(20)),
        "c": list(range(20))
    })

    profiler = RelationshipProfiler({
        "max_numeric_columns": 2
    })

    result = profiler.profile(df)

    assert result["summary"]["analysis_truncated"] is True

    assert result["summary"]["numeric_columns_examined"] == 2


def test_dataset_dimensions(profiler):

    df = pd.DataFrame({
        "id": [1, 2, 3],
        "sales": [100, 200, 300]
    })

    report = profiler.profile(df)

    assert report["dataset_summary"]["row_count"] == 3
    assert report["dataset_summary"]["column_count"] == 2


def test_missing_values(profiler):

    df = pd.DataFrame({
        "sales": [100, None, 300, None]
    })

    report = profiler.profile(df)

    assert report["dataset_summary"]["missing_cells"] == 2
    assert report["columns"][0]["missing_percentage"] == 50.0


def test_candidate_keys(profiler):

    df = pd.DataFrame({
        "id": [1, 2, 3],
        "category": ["A", "A", "B"]
    })

    report = profiler.profile(df)

    assert "id" in report["candidate_keys"]
    assert "category" not in report["candidate_keys"]


def test_duplicate_detection(profiler):

    df = pd.DataFrame({
        "id": [1, 1, 2],
        "sales": [100, 100, 200]
    })

    report = profiler.profile(df)

    assert report["dataset_summary"]["duplicate_rows"] == 1


def test_constant_columns(profiler):

    df = pd.DataFrame({
        "region": ["Goa", "Goa", "Goa"]
    })

    report = profiler.profile(df)

    assert "region" in report["constant_columns"]


def test_empty_columns(profiler):

    df = pd.DataFrame({
        "sales": [None, None, None]
    })

    report = profiler.profile(df)

    assert "sales" in report["empty_columns"]


def test_empty_dataframe(profiler):

    with pytest.raises(ValueError):
        profiler.profile(pd.DataFrame())


def test_duplicate_column_names(profiler):

    df = pd.DataFrame(
        [[1, 2]],
        columns=["id", "id"]
    )

    with pytest.raises(ValueError):
        profiler.profile(df)


def test_original_data_unchanged(profiler):

    df = pd.DataFrame({
        "sales": [100, None, 300]
    })

    original = df.copy(deep=True)

    profiler.profile(df)

    pd.testing.assert_frame_equal(df, original)


import json
import numpy as np

from decisioniq.profiling import StatisticalProfiler


def test_statistical_mean_median():

    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["central_tendency"]["mean"] == 3
    assert result["central_tendency"]["median"] == 3


def test_sample_variance():

    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["dispersion"]["variance"] == 2.5


def test_interquartile_range():

    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["dispersion"]["iqr"] == 2


def test_median_absolute_deviation():

    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["dispersion"]["median_absolute_deviation"] == 1


def test_statistical_missing_values():

    df = pd.DataFrame({"x": [10, None, 20]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["valid_count"] == 2
    assert result["missing_count"] == 1
    assert result["central_tendency"]["mean"] == 15


def test_statistical_infinite_values():

    df = pd.DataFrame({"x": [10, 20, np.inf, -np.inf]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["infinite_count"] == 2
    assert result["valid_count"] == 2


def test_constant_distribution():

    df = pd.DataFrame({"x": [10] * 20})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["dispersion"]["standard_deviation"] == 0
    assert result["distribution"]["skewness"] is None


def test_non_numeric_exclusion():

    df = pd.DataFrame({
        "sales": [100, 200],
        "region": ["Goa", "Pune"],
        "active": [True, False]
    })

    result = StatisticalProfiler().profile(df)

    assert result["numeric_columns"] == ["sales"]


def test_statistical_all_missing():

    df = pd.DataFrame({"x": [np.nan, np.nan]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["status"] == "no_finite_values"


def test_zero_mean_cv():

    df = pd.DataFrame({"x": [-1, 0, 1]})

    result = StatisticalProfiler().profile(df)["columns"][0]

    assert result["dispersion"]["coefficient_of_variation_pct"] is None


def test_statistical_json_serialization():

    df = pd.DataFrame({"x": [10.0]})

    result = StatisticalProfiler().profile(df)

    json.dumps(result, allow_nan=False)


def test_statistical_data_unchanged():

    df = pd.DataFrame({"x": [1, 2, 3, np.nan]})

    original = df.copy(deep=True)

    StatisticalProfiler().profile(df)

    pd.testing.assert_frame_equal(df, original)


from decisioniq.profiling import MissingValueProfiler


def test_missing_summary():

    df = pd.DataFrame({
        "a": [1, None, 3],
        "b": [1, 2, None]
    })

    result = MissingValueProfiler().profile(df)

    assert result["summary"]["missing_cells"] == 2
    assert result["summary"]["total_cells"] == 6


def test_complete_dataset():

    df = pd.DataFrame({
        "a": [1, 2, 3]
    })

    result = MissingValueProfiler().profile(df)

    assert result["summary"]["completeness_percentage"] == 100
    assert result["summary"]["complete_rows"] == 3


def test_missing_severity():

    df = pd.DataFrame({
        "a": [1, None, None, 4]
    })

    result = MissingValueProfiler().profile(df)

    assert result["columns"][0]["severity"] == "critical"


def test_fully_missing_column():

    df = pd.DataFrame({
        "a": [None, None, None]
    })

    result = MissingValueProfiler().profile(df)

    assert result["columns"][0]["severity"] == "empty"
    assert result["summary"]["fully_missing_rows"] == 3


def test_complete_row_count():

    df = pd.DataFrame({
        "a": [1, None, 3],
        "b": [1, 2, 3]
    })

    result = MissingValueProfiler().profile(df)

    assert result["summary"]["complete_rows"] == 2
    assert result["summary"]["incomplete_rows"] == 1


def test_co_missing_patterns():

    df = pd.DataFrame({
        "a": [None, None, 3],
        "b": [None, None, 4]
    })

    result = MissingValueProfiler().profile(df)

    pattern = result["missingness_patterns"][
        "top_co_missing_patterns"
    ][0]

    assert pattern["both_missing_count"] == 2
    assert pattern["jaccard_similarity"] == 1.0


def test_business_critical_column():

    df = pd.DataFrame({
        "revenue": [100, None, 200]
    })

    profiler = MissingValueProfiler({
        "critical_columns": ["revenue"]
    })

    result = profiler.profile(df)

    assert result["business_critical_issues"] == [
        "revenue"
    ]


def test_custom_threshold():

    df = pd.DataFrame({
        "a": [1, 2, 3, None]
    })

    profiler = MissingValueProfiler({
        "warning_threshold": 20,
        "critical_threshold": 50
    })

    result = profiler.profile(df)

    assert result["columns"][0]["severity"] == "warning"


def test_missing_data_unchanged():

    df = pd.DataFrame({
        "a": [1, None, 3]
    })

    original = df.copy(deep=True)

    MissingValueProfiler().profile(df)

    pd.testing.assert_frame_equal(df, original)


def test_missing_json_serialization():

    df = pd.DataFrame({
        "a": [1, None]
    })

    result = MissingValueProfiler().profile(df)

    json.dumps(result, allow_nan=False)


def test_invalid_missing_thresholds():

    with pytest.raises(ValueError):

        MissingValueProfiler({
            "warning_threshold": 60,
            "critical_threshold": 40
        })


def test_missing_empty_dataframe():

    with pytest.raises(ValueError):

        MissingValueProfiler().profile(
            pd.DataFrame()
        )


from decisioniq.profiling import OutlierProfiler


def test_iqr_outlier_detection():

    df = pd.DataFrame({
        "x": [10, 11, 12, 13, 14, 1000]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["methods"]["iqr"]
        ["outlier_count"] == 1
    )


def test_zscore_outlier_detection():

    df = pd.DataFrame({
        "x": list(range(100)) + [10000]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["methods"]["zscore"]
        ["outlier_count"] == 1
    )


def test_modified_zscore_detection():

    df = pd.DataFrame({
        "x": [10, 11, 12, 13, 14, 1000]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["methods"]
        ["modified_zscore"]["outlier_count"] == 1
    )


def test_outlier_consensus():

    df = pd.DataFrame({
        "x": list(range(100)) + [10000]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["agreement"]
        ["consensus_outlier_count"] == 1
    )


def test_outlier_constant_column():

    df = pd.DataFrame({"x": [10] * 20})

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["status"]
        == "skipped_constant_or_binary"
    )


def test_outlier_binary_column():

    df = pd.DataFrame({
        "x": [0, 1, 0, 1, 1, 0]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["status"]
        == "skipped_constant_or_binary"
    )


def test_outlier_insufficient_data():

    df = pd.DataFrame({"x": [1, 2, 3]})

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["status"]
        == "insufficient_data"
    )


def test_outlier_missing_and_infinite():

    df = pd.DataFrame({
        "x": [1, 2, 3, 4, np.nan, np.inf]
    })

    result = OutlierProfiler().profile(df)

    column = result["columns"][0]

    assert column["finite_count"] == 4
    assert column["missing_count"] == 1
    assert column["infinite_count"] == 1


def test_outlier_excluded_columns():

    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "sales": [10, 20, 30, 40, 1000]
    })

    profiler = OutlierProfiler({
        "excluded_columns": ["id"]
    })

    result = profiler.profile(df)

    assert result["excluded_columns"] == ["id"]
    assert result["columns_examined"] == 1


def test_outlier_zero_mad():

    df = pd.DataFrame({
        "x": [1, 1, 1, 1, 2, 100]
    })

    result = OutlierProfiler().profile(df)

    assert (
        result["columns"][0]["methods"]
        ["modified_zscore"]["status"] == "zero_mad"
    )


def test_outlier_invalid_threshold():

    with pytest.raises(ValueError):

        OutlierProfiler({
            "iqr_multiplier": -1
        })


def test_outlier_json_serialization():

    df = pd.DataFrame({
        "x": [10, 11, 12, 13, 1000]
    })

    result = OutlierProfiler().profile(df)

    json.dumps(result, allow_nan=False)


def test_outlier_data_unchanged():

    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 1000]
    })

    original = df.copy(deep=True)

    OutlierProfiler().profile(df)

    pd.testing.assert_frame_equal(df, original)

