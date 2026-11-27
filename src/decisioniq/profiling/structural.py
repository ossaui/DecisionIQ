
import pandas as pd


class StructuralProfiler:
    """Generate structural metadata for any tabular dataset."""

    def __init__(self, config=None):
        self.config = config or {}

    @staticmethod
    def detect_type(series: pd.Series) -> str:

        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        if pd.api.types.is_integer_dtype(series):
            return "integer"

        if pd.api.types.is_float_dtype(series):
            return "float"

        if isinstance(series.dtype, pd.CategoricalDtype):
            return "categorical"

        if pd.api.types.is_string_dtype(series):
            return "text"

        return "other"

    def profile(self, df: pd.DataFrame) -> dict:

        if df.empty:
            raise ValueError("Cannot profile an empty dataset.")

        if not df.columns.is_unique:
            raise ValueError("Duplicate column names detected.")

        rows, columns = df.shape

        column_profiles = []

        candidate_keys = []
        constant_columns = []
        empty_columns = []

        for column in df.columns:

            series = df[column]

            missing = int(series.isna().sum())
            non_null = int(series.notna().sum())
            unique = int(series.nunique(dropna=True))

            uniqueness_ratio = (
                unique / non_null
                if non_null else 0.0
            )

            is_candidate_key = (
                rows > 1
                and missing == 0
                and unique == rows
            )

            if is_candidate_key:
                candidate_keys.append(str(column))

            if unique == 1:
                constant_columns.append(str(column))

            if non_null == 0:
                empty_columns.append(str(column))

            column_profiles.append({
                "column_name": str(column),
                "physical_dtype": str(series.dtype),
                "detected_type": self.detect_type(series),
                "non_null_count": non_null,
                "missing_count": missing,
                "missing_percentage": round(
                    missing / rows * 100, 4
                ),
                "unique_count": unique,
                "uniqueness_ratio": round(
                    uniqueness_ratio, 4
                ),
                "candidate_key": is_candidate_key,
                "memory_bytes": int(
                    series.memory_usage(
                        index=False, deep=True
                    )
                )
            })

        duplicate_rows = int(
            df.duplicated().sum()
        )

        missing_cells = int(
            df.isna().sum().sum()
        )

        total_cells = rows * columns

        return {
            "dataset_summary": {
                "row_count": rows,
                "column_count": columns,
                "total_cells": total_cells,
                "memory_usage_bytes": int(
                    df.memory_usage(deep=True).sum()
                ),
                "missing_cells": missing_cells,
                "missing_percentage": round(
                    missing_cells / total_cells * 100, 4
                ),
                "duplicate_rows": duplicate_rows,
                "duplicate_percentage": round(
                    duplicate_rows / rows * 100, 4
                )
            },
            "candidate_keys": candidate_keys,
            "constant_columns": constant_columns,
            "empty_columns": empty_columns,
            "columns": column_profiles
        }
