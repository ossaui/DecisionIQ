
from itertools import combinations
import warnings

import numpy as np
import pandas as pd

from scipy import stats
from statsmodels.stats.multitest import multipletests


class RelationshipProfiler:
    """Analyze numerical and categorical associations."""

    def __init__(self, config=None):

        self.config = config or {}

        self.threshold = self.config.get(
            "correlation_threshold", 0.8
        )

        self.alpha = self.config.get(
            "significance_level", 0.05
        )

        self.max_numeric_columns = self.config.get(
            "max_numeric_columns", 50
        )

        self.max_categorical_columns = self.config.get(
            "max_categorical_columns", 20
        )

        self.max_categories = self.config.get(
            "max_categories", 30
        )

        self.min_observations = self.config.get(
            "min_observations", 10
        )

        self.excluded_columns = set(
            self.config.get("excluded_columns", [])
        )

        self.methods = [
            method
            for method in ["pearson", "spearman", "kendall"]
            if self.config.get(method, True)
        ]

        if not 0 < self.alpha < 1:
            raise ValueError("Invalid significance level.")

        if not 0 <= self.threshold <= 1:
            raise ValueError("Invalid correlation threshold.")

        if self.min_observations < 3:
            raise ValueError("At least 3 observations required.")

    @staticmethod
    def safe_number(value):

        value = float(value)

        return value if np.isfinite(value) else None

    @staticmethod
    def classify_strength(value):

        value = abs(value)

        if value >= 0.8:
            return "very_strong"

        if value >= 0.6:
            return "strong"

        if value >= 0.4:
            return "moderate"

        if value >= 0.2:
            return "weak"

        return "very_weak"

    def numeric_relationships(self, df, columns):

        results = []

        functions = {
            "pearson": stats.pearsonr,
            "spearman": stats.spearmanr,
            "kendall": stats.kendalltau
        }

        for first, second in combinations(columns, 2):

            pair = df[[first, second]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            if len(pair) < self.min_observations:
                continue

            if (
                pair[first].nunique() < 2
                or pair[second].nunique() < 2
            ):
                continue

            for method in self.methods:

                with warnings.catch_warnings():

                    warnings.simplefilter("ignore")

                    coefficient, p_value = functions[method](
                        pair[first].to_numpy(dtype=float),
                        pair[second].to_numpy(dtype=float)
                    )

                coefficient = self.safe_number(coefficient)
                p_value = self.safe_number(p_value)

                if coefficient is None or p_value is None:
                    continue

                results.append({

                    "column_a": str(first),
                    "column_b": str(second),

                    "method": method,

                    "coefficient": coefficient,
                    "p_value": p_value,

                    "observations": len(pair),

                    "strength": self.classify_strength(
                        coefficient
                    ),

                    "direction": (
                        "positive" if coefficient > 0
                        else "negative" if coefficient < 0
                        else "zero"
                    ),

                    "high_correlation": (
                        abs(coefficient) >= self.threshold
                    )
                })

        return results

    def categorical_relationships(self, df, columns):

        results = []

        for first, second in combinations(columns, 2):

            pair = df[[first, second]].dropna()

            if len(pair) < self.min_observations:
                continue

            table = pd.crosstab(
                pair[first], pair[second]
            )

            rows, cols = table.shape

            if rows < 2 or cols < 2:
                continue

            chi2, p_value, dof, expected = (
                stats.chi2_contingency(
                    table,
                    correction=False
                )
            )

            n = int(table.to_numpy().sum())

            denominator = min(rows - 1, cols - 1)

            cramers_v = np.sqrt(
                chi2 / (n * denominator)
            )

            small_expected_fraction = float(
                (expected < 5).mean()
            )

            assumptions_met = (
                expected.min() >= 1
                and small_expected_fraction <= 0.2
            )

            results.append({

                "column_a": str(first),
                "column_b": str(second),

                "method": "chi_square",

                "chi_square": float(chi2),
                "p_value": float(p_value),
                "degrees_of_freedom": int(dof),

                "cramers_v": float(cramers_v),

                "observations": n,

                "minimum_expected_count": float(
                    expected.min()
                ),

                "expected_cells_below_5_pct": (
                    small_expected_fraction * 100
                ),

                "assumptions_met": bool(
                    assumptions_met
                )
            })

        return results

    def adjust_pvalues(self, results):

        for result in results:

            result["adjusted_p_value"] = None
            result["statistically_significant"] = None

        eligible = [
            result
            for result in results
            if result.get("assumptions_met", True)
        ]

        if not eligible:
            return results

        p_values = [
            result["p_value"]
            for result in eligible
        ]

        rejected, adjusted, _, _ = multipletests(
            p_values,
            alpha=self.alpha,
            method="fdr_bh"
        )

        for result, p_value, reject in zip(
            eligible, adjusted, rejected
        ):

            result["adjusted_p_value"] = float(p_value)

            result["statistically_significant"] = bool(
                reject
            )

        return results

    def profile(self, df):

        if df.empty:
            raise ValueError(
                "Cannot profile an empty dataset."
            )

        if not df.columns.is_unique:
            raise ValueError(
                "Duplicate column names detected."
            )

        numeric = []
        categorical = []

        for column in df.columns:

            if str(column) in self.excluded_columns:
                continue

            series = df[column]

            unique = series.nunique(dropna=True)

            if unique < 2:
                continue

            is_numeric = (
                pd.api.types.is_integer_dtype(series)
                or pd.api.types.is_float_dtype(series)
            )

            if is_numeric and unique > 2:

                numeric.append(column)

            elif 2 <= unique <= self.max_categories:

                categorical.append(column)

        numeric_selected = numeric[
            :self.max_numeric_columns
        ]

        categorical_selected = categorical[
            :self.max_categorical_columns
        ]

        numeric_results = self.numeric_relationships(
            df, numeric_selected
        )

        categorical_results = (
            self.categorical_relationships(
                df, categorical_selected
            )
        )

        self.adjust_pvalues(numeric_results)
        self.adjust_pvalues(categorical_results)

        numeric_results.sort(
            key=lambda r: abs(r["coefficient"]),
            reverse=True
        )

        categorical_results.sort(
            key=lambda r: r["cramers_v"],
            reverse=True
        )

        return {

            "summary": {

                "numeric_columns_detected": len(numeric),

                "categorical_columns_detected": len(
                    categorical
                ),

                "numeric_columns_examined": len(
                    numeric_selected
                ),

                "categorical_columns_examined": len(
                    categorical_selected
                ),

                "numeric_tests": len(numeric_results),

                "categorical_tests": len(
                    categorical_results
                ),

                "high_correlation_results": sum(
                    r["high_correlation"]
                    for r in numeric_results
                ),

                "analysis_truncated": (
                    len(numeric) > len(numeric_selected)
                    or len(categorical)
                    > len(categorical_selected)
                )
            },

            "settings": {
                "significance_level": self.alpha,
                "correlation_threshold": self.threshold,
                "multiple_testing_method": "fdr_bh",
                "correction_families": [
                    "numeric_tests",
                    "eligible_categorical_tests"
                ]
            },

            "numeric_columns": list(
                map(str, numeric_selected)
            ),

            "categorical_columns": list(
                map(str, categorical_selected)
            ),

            "numeric_relationships": numeric_results,

            "categorical_relationships": (
                categorical_results
            ),

            "interpretation_warning": (
                "Association does not establish causation. "
                "Statistical significance does not imply "
                "business importance."
            )
        }
