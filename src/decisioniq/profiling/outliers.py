
import numpy as np
import pandas as pd


class OutlierProfiler:
    """Detect statistical outliers without modifying data."""

    def __init__(self, config=None):

        self.config = config or {}

        self.iqr_multiplier = self.config.get(
            "iqr_multiplier", 1.5
        )

        self.zscore_threshold = self.config.get(
            "zscore_threshold", 3.0
        )

        self.mad_threshold = self.config.get(
            "mad_threshold", 3.5
        )

        self.min_observations = self.config.get(
            "min_observations", 4
        )

        self.consensus_threshold = self.config.get(
            "consensus_threshold", 2
        )

        self.excluded_columns = set(
            self.config.get("excluded_columns", [])
        )

        thresholds = [
            self.iqr_multiplier,
            self.zscore_threshold,
            self.mad_threshold
        ]

        if any(
            not np.isfinite(t) or t <= 0
            for t in thresholds
        ):
            raise ValueError(
                "Outlier thresholds must be positive and finite."
            )

        if self.min_observations < 4:
            raise ValueError(
                "At least four observations are required."
            )

        if self.consensus_threshold not in [1, 2, 3]:
            raise ValueError(
                "Consensus threshold must be 1, 2 or 3."
            )

    @staticmethod
    def empty_mask(values):

        return np.zeros(len(values), dtype=bool)

    @staticmethod
    def method_result(mask, status, **details):

        return {
            "status": status,
            "outlier_count": int(mask.sum()),
            "outlier_percentage": round(
                float(mask.mean()) * 100, 4
            ) if len(mask) else 0.0,
            **details
        }

    def detect_iqr(self, values):

        q1, q3 = np.quantile(
            values, [0.25, 0.75]
        )

        iqr = q3 - q1

        if iqr == 0:

            mask = self.empty_mask(values)

            return mask, self.method_result(
                mask,
                "zero_iqr",
                iqr=0.0
            )

        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr

        mask = (
            (values < lower)
            | (values > upper)
        )

        return mask, self.method_result(
            mask,
            "evaluated",
            q1=float(q1),
            q3=float(q3),
            iqr=float(iqr),
            lower_bound=float(lower),
            upper_bound=float(upper)
        )

    def detect_zscore(self, values):

        mean = np.mean(values)

        std = np.std(values, ddof=1)

        if std == 0 or not np.isfinite(std):

            mask = self.empty_mask(values)

            return mask, self.method_result(
                mask,
                "undefined_standard_deviation"
            )

        scores = (values - mean) / std

        mask = (
            np.abs(scores)
            > self.zscore_threshold
        )

        return mask, self.method_result(
            mask,
            "evaluated",
            mean=float(mean),
            standard_deviation=float(std),
            threshold=self.zscore_threshold
        )

    def detect_modified_zscore(self, values):

        median = np.median(values)

        mad = np.median(
            np.abs(values - median)
        )

        if mad == 0:

            mask = self.empty_mask(values)

            return mask, self.method_result(
                mask,
                "zero_mad",
                mad=0.0
            )

        scores = (
            0.67448975
            * (values - median)
            / mad
        )

        mask = (
            np.abs(scores)
            > self.mad_threshold
        )

        return mask, self.method_result(
            mask,
            "evaluated",
            median=float(median),
            mad=float(mad),
            threshold=self.mad_threshold
        )

    def profile_column(self, series):

        numeric = series.to_numpy(
            dtype=float,
            na_value=np.nan
        )

        finite_mask = np.isfinite(numeric)

        values = numeric[finite_mask]

        result = {
            "column_name": str(series.name),
            "total_count": len(series),
            "finite_count": len(values),
            "missing_count": int(series.isna().sum()),
            "infinite_count": int(np.isinf(numeric).sum())
        }

        if len(values) < self.min_observations:

            result["status"] = "insufficient_data"

            return result

        if np.unique(values).size <= 2:

            result["status"] = (
                "skipped_constant_or_binary"
            )

            return result

        iqr_mask, iqr_result = self.detect_iqr(
            values
        )

        z_mask, z_result = self.detect_zscore(
            values
        )

        mad_mask, mad_result = (
            self.detect_modified_zscore(values)
        )

        votes = (
            iqr_mask.astype(int)
            + z_mask.astype(int)
            + mad_mask.astype(int)
        )

        evaluated_methods = sum(
            method["status"] == "evaluated"
            for method in [
                iqr_result,
                z_result,
                mad_result
            ]
        )

        any_mask = votes >= 1

        consensus_mask = (
            votes >= self.consensus_threshold
        )

        consensus_available = (
            evaluated_methods
            >= self.consensus_threshold
        )

        result.update({

            "status": "profiled",

            "methods": {
                "iqr": iqr_result,
                "zscore": z_result,
                "modified_zscore": mad_result
            },

            "agreement": {
                "evaluated_methods": evaluated_methods,
                "flagged_by_any_method": int(
                    any_mask.sum()
                ),
                "flagged_by_exactly_one": int(
                    (votes == 1).sum()
                ),
                "flagged_by_exactly_two": int(
                    (votes == 2).sum()
                ),
                "flagged_by_all_three": int(
                    (votes == 3).sum()
                ),
                "consensus_available": consensus_available,
                "consensus_threshold": self.consensus_threshold,
                "consensus_outlier_count": (
                    int(consensus_mask.sum())
                    if consensus_available else None
                ),
                "consensus_outlier_percentage": (
                    round(
                        float(consensus_mask.mean())
                        * 100, 4
                    )
                    if consensus_available else None
                )
            },

            "recommendation": (
                "Investigate flagged observations using "
                "business context before removing or "
                "correcting any records."
            )

        })

        return result

    def profile(self, df):

        if df.empty:
            raise ValueError(
                "Cannot profile an empty dataset."
            )

        if not df.columns.is_unique:
            raise ValueError(
                "Duplicate column names detected."
            )

        numeric_columns = df.select_dtypes(
            include=["integer", "floating"]
        ).columns

        profiles = []
        excluded = []

        for column in numeric_columns:

            if str(column) in self.excluded_columns:

                excluded.append(str(column))

                continue

            profiles.append(
                self.profile_column(df[column])
            )

        return {
            "numeric_columns_detected": len(
                numeric_columns
            ),
            "columns_examined": len(profiles),
            "columns_profiled": sum(
                p["status"] == "profiled"
                for p in profiles
            ),
            "excluded_columns": excluded,
            "columns": profiles
        }
