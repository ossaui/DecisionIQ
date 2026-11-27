
import warnings

import numpy as np
import pandas as pd

from scipy import stats


class StatisticalProfiler:
    """Generate descriptive statistics for numerical columns."""

    def __init__(self, config=None):

        self.config = config or {}

        self.percentiles = self.config.get(
            "percentiles",
            [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
        )

    @staticmethod
    def safe_number(value):

        if value is None:
            return None

        value = float(value)

        return value if np.isfinite(value) else None

    @staticmethod
    def classify_skewness(skewness):

        if skewness is None:
            return "undefined"

        if skewness > 1:
            return "highly_right_skewed"

        if skewness > 0.5:
            return "moderately_right_skewed"

        if skewness < -1:
            return "highly_left_skewed"

        if skewness < -0.5:
            return "moderately_left_skewed"

        return "approximately_symmetric"

    def normality_test(self, values):

        if len(values) < 8 or values.nunique() < 2:
            return {
                "test": None,
                "statistic": None,
                "p_value": None,
                "conclusion": "insufficient_variation_or_data"
            }

        # D'Agostino-Pearson normality test
        with warnings.catch_warnings():

            warnings.simplefilter("ignore", UserWarning)

            statistic, p_value = stats.normaltest(values)

        statistic = self.safe_number(statistic)
        p_value = self.safe_number(p_value)

        if p_value is None:
            conclusion = "undefined"

        elif p_value < 0.05:
            conclusion = "reject_normality"

        else:
            conclusion = "normality_not_rejected"

        return {
            "test": "dagostino_pearson",
            "statistic": statistic,
            "p_value": p_value,
            "significance_level": 0.05,
            "conclusion": conclusion
        }

    def profile_column(self, series):

        numeric = series.astype(float)

        infinite_count = int(
            np.isinf(numeric).sum()
        )

        values = numeric.replace(
            [np.inf, -np.inf], np.nan
        ).dropna()

        count = len(values)

        result = {
            "column_name": str(series.name),
            "valid_count": count,
            "missing_count": int(series.isna().sum()),
            "infinite_count": infinite_count
        }

        if count == 0:

            result["status"] = "no_finite_values"

            return result

        mean = self.safe_number(values.mean())
        median = self.safe_number(values.median())

        variance = self.safe_number(values.var(ddof=1))
        std = self.safe_number(values.std(ddof=1))

        minimum = self.safe_number(values.min())
        maximum = self.safe_number(values.max())

        q1 = self.safe_number(values.quantile(0.25))
        q3 = self.safe_number(values.quantile(0.75))

        iqr = q3 - q1

        mad = self.safe_number(
            (values - median).abs().median()
        )

        skewness = (
            self.safe_number(values.skew())
            if count >= 3 and values.nunique() > 1
            else None
        )

        kurtosis = (
            self.safe_number(values.kurt())
            if count >= 4 and values.nunique() > 1
            else None
        )

        # CV is meaningful mainly for ratio-scale
        # variables with a positive mean.
        cv = (
            self.safe_number(std / mean * 100)
            if mean is not None
            and mean > 0
            and std is not None
            and minimum >= 0
            else None
        )

        frequencies = values.value_counts()

        mode_frequency = int(frequencies.iloc[0])

        modes = (
            frequencies[
                frequencies == mode_frequency
            ].index.tolist()
            if mode_frequency > 1
            else []
        )

        result.update({

            "status": "profiled",

            "central_tendency": {
                "mean": mean,
                "median": median,
                "modes": [
                    self.safe_number(v)
                    for v in modes[:10]
                ],
                "mode_frequency": mode_frequency,
                "mode_count": len(modes)
            },

            "dispersion": {
                "variance": variance,
                "standard_deviation": std,
                "range": self.safe_number(
                    maximum - minimum
                ),
                "iqr": self.safe_number(iqr),
                "median_absolute_deviation": mad,
                "coefficient_of_variation_pct": cv
            },

            "position": {
                "minimum": minimum,
                "maximum": maximum,
                "q1": q1,
                "q2": median,
                "q3": q3
            },

            "percentiles": {
                str(p): self.safe_number(
                    values.quantile(p)
                )
                for p in self.percentiles
            },

            "distribution": {
                "skewness": skewness,
                "excess_kurtosis": kurtosis,
                "shape": self.classify_skewness(
                    skewness
                ),
                "normality": self.normality_test(
                    values
                )
            },

            "value_composition": {
                "zero_count": int((values == 0).sum()),
                "positive_count": int((values > 0).sum()),
                "negative_count": int((values < 0).sum())
            }

        })

        return result

    def profile(self, df):

        if df.empty:
            raise ValueError("Cannot profile an empty dataset.")

        if not df.columns.is_unique:
            raise ValueError("Duplicate column names detected.")

        numerical_columns = df.select_dtypes(
            include=["integer", "floating"]
        ).columns

        profiles = [
            self.profile_column(df[column])
            for column in numerical_columns
        ]

        return {
            "numeric_column_count": len(numerical_columns),
            "numeric_columns": [
                str(c) for c in numerical_columns
            ],
            "columns": profiles
        }
