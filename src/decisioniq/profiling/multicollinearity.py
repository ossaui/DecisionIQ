
import numpy as np
import pandas as pd


class MulticollinearityProfiler:
    """Measure linear dependence among selected predictors."""

    def __init__(self, config=None):

        self.config = config or {}

        self.predictor_columns = self.config.get(
            "predictor_columns", []
        )

        self.warning_threshold = self.config.get(
            "warning_threshold", 5
        )

        self.critical_threshold = self.config.get(
            "critical_threshold", 10
        )

        self.max_predictors = self.config.get(
            "max_predictors", 30
        )

    def profile(self, df):

        if df.empty:
            raise ValueError("Empty dataset.")

        if not df.columns.is_unique:
            raise ValueError("Duplicate column names.")

        if not self.predictor_columns:

            return {
                "status": "predictors_not_configured",
                "columns": []
            }

        columns = list(
            dict.fromkeys(self.predictor_columns)
        )

        missing = [
            c for c in columns
            if c not in df.columns
        ]

        if missing:

            return {
                "status": "predictors_missing",
                "missing_predictors": missing,
                "columns": []
            }

        if len(columns) > self.max_predictors:

            return {
                "status": "predictor_limit_exceeded",
                "columns": []
            }

        if any(
            not pd.api.types.is_numeric_dtype(df[c])
            for c in columns
        ):

            return {
                "status": "non_numeric_predictors",
                "columns": []
            }

        data = df[columns].astype(float).replace(
            [np.inf, -np.inf], np.nan
        ).dropna()

        constant_columns = [
            c for c in columns
            if data[c].nunique() <= 1
        ]

        data = data.drop(columns=constant_columns)

        n, p = data.shape

        if p < 2 or n <= p:

            return {
                "status": "insufficient_data",
                "observations": n,
                "predictors": p,
                "constant_columns": constant_columns,
                "columns": []
            }

        matrix = data.to_numpy(dtype=float)

        # Standardization improves numerical stability.
        matrix = (
            matrix - matrix.mean(axis=0)
        ) / matrix.std(axis=0)

        rank = int(np.linalg.matrix_rank(matrix))

        results = []

        for index, column in enumerate(data.columns):

            target = matrix[:, index]

            others = np.delete(
                matrix, index, axis=1
            )

            coefficients = np.linalg.lstsq(
                others, target, rcond=None
            )[0]

            predicted = others @ coefficients

            residual = target - predicted

            sse = np.sum(residual ** 2)

            sst = np.sum(
                (target - target.mean()) ** 2
            )

            r_squared = float(
                np.clip(1 - sse / sst, 0, 1)
            )

            if 1 - r_squared <= 1e-12:

                vif = None
                severity = "perfect_collinearity"

            else:

                vif = float(
                    1 / (1 - r_squared)
                )

                if vif >= self.critical_threshold:

                    severity = "critical"

                elif vif >= self.warning_threshold:

                    severity = "warning"

                else:

                    severity = "low"

            results.append({
                "column_name": str(column),
                "r_squared": r_squared,
                "vif": vif,
                "severity": severity
            })

        results.sort(
            key=lambda r: (
                float("inf")
                if r["vif"] is None
                else r["vif"]
            ),
            reverse=True
        )

        return {

            "status": "profiled",

            "summary": {
                "original_rows": len(df),
                "complete_case_rows": n,
                "excluded_rows": len(df) - n,
                "predictor_count": p,
                "matrix_rank": rank,
                "rank_deficient": rank < p,
                "constant_columns": constant_columns
            },

            "columns": results,

            "interpretation_warning": (
                "VIF depends on the selected predictor "
                "set. High VIF does not automatically "
                "justify feature removal."
            )
        }
