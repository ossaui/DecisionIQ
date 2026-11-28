
import numpy as np
import pandas as pd

from pandas.api.types import (
    is_datetime64_any_dtype,
    is_bool_dtype
)

from .contracts import DatasetContract


class SchemaValidator:

    def __init__(self, contract: DatasetContract):

        if not isinstance(contract, DatasetContract):
            raise TypeError(
                "A valid DatasetContract is required."
            )

        self.contract = contract

    @staticmethod
    def detect_physical_type(series):

        return str(series.dtype)

    @staticmethod
    def validate_type(series, definition):

        dtype = definition.dtype

        # Missing values are handled separately.
        present = series.notna()

        values = series.loc[present]

        invalid = pd.Series(
            False,
            index=series.index,
            dtype=bool
        )

        if values.empty:
            return invalid

        if dtype in {"integer", "float", "numeric"}:

            numeric = pd.to_numeric(
                values,
                errors="coerce"
            )

            numbers = numeric.to_numpy(
                dtype=float,
                na_value=np.nan
            )

            valid = np.isfinite(numbers)

            boolean_values = values.map(
                lambda x: isinstance(
                    x, (bool, np.bool_)
                )
            ).to_numpy(dtype=bool)

            valid &= ~boolean_values

            if dtype == "integer":

                valid &= (
                    numbers == np.trunc(numbers)
                )

        elif dtype in {"string", "category"}:

            valid = values.map(
                lambda x: isinstance(x, str)
            ).to_numpy(dtype=bool)

        elif dtype == "datetime":

            if is_datetime64_any_dtype(values):

                valid = np.ones(
                    len(values),
                    dtype=bool
                )

            else:

                # Prevent numeric IDs from being
                # interpreted as Unix timestamps.
                textual = values.map(
                    lambda x: isinstance(x, str)
                ).to_numpy(dtype=bool)

                parsed = pd.to_datetime(
                    values.where(textual),
                    format=definition.date_format
                    or "mixed",
                    errors="coerce",
                    utc=True
                )

                valid = (
                    parsed.notna().to_numpy()
                    & textual
                )

        elif dtype == "boolean":

            if is_bool_dtype(values):

                valid = np.ones(
                    len(values),
                    dtype=bool
                )

            else:

                valid = values.map(
                    lambda x: isinstance(
                        x, (bool, np.bool_)
                    )
                ).to_numpy(dtype=bool)

        else:

            raise ValueError(
                f"Unsupported data type: {dtype}"
            )

        invalid.loc[present] = ~valid

        return invalid

    @staticmethod
    def create_issue(
        rule,
        severity,
        message,
        column=None,
        affected_rows=None,
        total_rows=None,
        scope="row"
    ):

        percentage = None

        if (
            affected_rows is not None
            and total_rows
        ):

            percentage = round(
                affected_rows / total_rows * 100,
                4
            )

        return {
            "rule": rule,
            "scope": scope,
            "column": column,
            "severity": severity,
            "message": message,
            "affected_rows": affected_rows,
            "affected_percentage": percentage
        }

    def validate(self, df):

        if not isinstance(df, pd.DataFrame):

            raise TypeError(
                "Input must be a pandas DataFrame."
            )

        # Positional index prevents ambiguous masks
        # when the original index contains duplicates.
        working = df.reset_index(drop=True)

        contract = self.contract

        rows, columns = working.shape

        issues = []

        column_results = []

        invalid_rows = np.zeros(
            rows,
            dtype=bool
        )

        expected = set(contract.columns)

        actual = set(working.columns)

        missing_required = [
            name
            for name, definition
            in contract.columns.items()
            if definition.required
            and name not in actual
        ]

        missing_optional = [
            name
            for name, definition
            in contract.columns.items()
            if not definition.required
            and name not in actual
        ]

        unexpected = sorted(
            map(str, actual - expected)
        )

        duplicate_columns = [
            str(name)
            for name in working.columns[
                working.columns.duplicated()
            ].unique()
        ]

        def add_row_issue(
            mask,
            rule,
            severity,
            message,
            column=None
        ):

            nonlocal invalid_rows

            mask = np.asarray(
                mask,
                dtype=bool
            )

            count = int(mask.sum())

            if count:

                invalid_rows |= mask

                issues.append(
                    self.create_issue(
                        rule=rule,
                        severity=severity,
                        message=message,
                        column=column,
                        affected_rows=count,
                        total_rows=rows
                    )
                )

        if duplicate_columns:

            issues.append(
                self.create_issue(
                    rule="duplicate_column_names",
                    severity="critical",
                    message=(
                        "Duplicate column names: "
                        + ", ".join(duplicate_columns)
                    ),
                    scope="dataset"
                )
            )

        for name in missing_required:

            issues.append(
                self.create_issue(
                    rule="required_column_missing",
                    severity="critical",
                    column=name,
                    message=(
                        f"Required column missing: {name}"
                    ),
                    scope="dataset"
                )
            )

        if not contract.allow_extra_columns:

            for name in unexpected:

                issues.append(
                    self.create_issue(
                        rule="unexpected_column",
                        severity="high",
                        column=name,
                        message=(
                            f"Unexpected column: {name}"
                        ),
                        scope="dataset"
                    )
                )

        if rows < contract.minimum_rows:

            issues.append(
                self.create_issue(
                    rule="minimum_rows",
                    severity="critical",
                    message=(
                        f"Expected at least "
                        f"{contract.minimum_rows} rows; "
                        f"received {rows}."
                    ),
                    scope="dataset"
                )
            )

        if (
            contract.maximum_rows is not None
            and rows > contract.maximum_rows
        ):

            issues.append(
                self.create_issue(
                    rule="maximum_rows",
                    severity="high",
                    message=(
                        f"Expected at most "
                        f"{contract.maximum_rows} rows; "
                        f"received {rows}."
                    ),
                    scope="dataset"
                )
            )

        for name, definition in (
            contract.columns.items()
        ):

            if name not in actual:

                column_results.append({
                    "column_name": name,
                    "expected_dtype": definition.dtype,
                    "status": (
                        "missing_required"
                        if definition.required
                        else "missing_optional"
                    )
                })

                continue

            if name in duplicate_columns:

                column_results.append({
                    "column_name": name,
                    "status": "ambiguous_column"
                })

                continue

            series = working[name]

            missing_mask = series.isna()

            type_mask = self.validate_type(
                series,
                definition
            )

            null_violations = (
                int(missing_mask.sum())
                if not definition.nullable
                else 0
            )

            type_violations = int(
                type_mask.sum()
            )

            if not definition.nullable:

                add_row_issue(
                    missing_mask,
                    rule="nullability_violation",
                    severity=definition.severity,
                    message=(
                        f"{name} does not permit "
                        "missing values."
                    ),
                    column=name
                )

            add_row_issue(
                type_mask,
                rule="data_type_violation",
                severity=definition.severity,
                message=(
                    f"{name} contains values that "
                    f"do not conform to "
                    f"{definition.dtype}."
                ),
                column=name
            )

            column_results.append({
                "column_name": name,
                "expected_dtype": definition.dtype,
                "physical_dtype":
                    self.detect_physical_type(series),
                "required": definition.required,
                "nullable": definition.nullable,
                "missing_count":
                    int(missing_mask.sum()),
                "null_violations": null_violations,
                "type_violations": type_violations,
                "status": (
                    "failed"
                    if null_violations
                    or type_violations
                    else "passed"
                )
            })

        primary_key = contract.primary_key

        key_status = "not_configured"

        if primary_key:

            if (
                all(
                    name in actual
                    for name in primary_key
                )
                and not any(
                    name in duplicate_columns
                    for name in primary_key
                )
            ):

                keys = working[primary_key]

                null_keys = keys.isna().any(axis=1)

                duplicate_keys = (
                    keys.duplicated(keep=False)
                    & ~null_keys
                )

                add_row_issue(
                    null_keys,
                    rule="primary_key_null",
                    severity="critical",
                    message=(
                        "Primary key contains "
                        "missing values."
                    ),
                    column=", ".join(primary_key)
                )

                add_row_issue(
                    duplicate_keys,
                    rule="primary_key_duplicate",
                    severity="critical",
                    message=(
                        "Primary key is not unique."
                    ),
                    column=", ".join(primary_key)
                )

                key_status = (
                    "failed"
                    if null_keys.any()
                    or duplicate_keys.any()
                    else "passed"
                )

            else:

                key_status = "not_evaluable"

        severity_summary = {
            level: sum(
                issue["severity"] == level
                for issue in issues
            )
            for level in [
                "critical",
                "high",
                "medium",
                "low"
            ]
        }

        dataset_issues = [
            issue for issue in issues
            if issue["scope"] == "dataset"
        ]

        affected = int(invalid_rows.sum())

        return {
            "contract": {
                "name": contract.name,
                "version": contract.version,
                "industry": contract.industry,
                "grain": contract.grain
            },

            "status": (
                "failed" if issues else "passed"
            ),

            "summary": {
                "total_rows": rows,
                "actual_columns": columns,
                "expected_columns": len(expected),
                "missing_required_columns":
                    len(missing_required),
                "missing_optional_columns":
                    len(missing_optional),
                "unexpected_columns":
                    len(unexpected),
                "total_issues": len(issues),
                "dataset_level_issues":
                    len(dataset_issues),
                "affected_rows": affected,
                "unflagged_rows": rows - affected,
                "affected_percentage": (
                    round(affected / rows * 100, 4)
                    if rows else None
                )
            },

            "schema_drift": {
                "missing_required":
                    missing_required,
                "missing_optional":
                    missing_optional,
                "unexpected_columns":
                    unexpected,
                "duplicate_columns":
                    duplicate_columns
            },

            "primary_key": {
                "columns": primary_key,
                "status": key_status
            },

            "severity_summary":
                severity_summary,

            "columns": column_results,

            "issues": issues,

            "interpretation": (
                "Schema checks evaluate structural "
                "and type conformance only. "
                "Unflagged rows are not necessarily "
                "business-valid records. "
                "No records were modified or removed."
            )
        }
