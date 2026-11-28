
import numpy as np
import pandas as pd

from .contracts import DatasetContract
from .schema import SchemaValidator


class ConstraintValidator:

    def __init__(self, contract: DatasetContract):

        if not isinstance(contract, DatasetContract):
            raise TypeError(
                "A valid DatasetContract is required."
            )

        self.contract = contract

    @staticmethod
    def numeric_values(series):

        return pd.to_numeric(
            series,
            errors="coerce"
        )

    @staticmethod
    def configured_rules(definition):

        rules = []

        if definition.minimum is not None:
            rules.append("minimum")

        if definition.maximum is not None:
            rules.append("maximum")

        if definition.allowed_values is not None:
            rules.append("allowed_values")

        if definition.pattern is not None:
            rules.append("regex_pattern")

        if definition.unique:
            rules.append("uniqueness")

        if not definition.allow_blank:
            rules.append("blank_string")

        return rules

    def validate(
        self,
        df,
        include_row_positions=False
    ):

        if not isinstance(df, pd.DataFrame):

            raise TypeError(
                "Input must be a pandas DataFrame."
            )

        working = df.reset_index(drop=True)

        total_rows = len(working)

        issues = []
        checks = []
        column_results = []

        invalid_rows = np.zeros(
            total_rows,
            dtype=bool
        )

        duplicate_columns = set(
            working.columns[
                working.columns.duplicated()
            ]
        )

        def evaluate(
            column,
            rule,
            mask,
            eligible,
            severity,
            message
        ):

            eligible = np.asarray(
                eligible,
                dtype=bool
            )

            mask = (
                np.asarray(mask, dtype=bool)
                & eligible
            )

            affected = int(mask.sum())

            evaluated = int(eligible.sum())

            invalid_rows[:] |= mask

            result = {
                "column": column,
                "rule": rule,
                "severity": severity,

                "status": (
                    "not_evaluable"
                    if evaluated == 0
                    else "failed"
                    if affected
                    else "passed"
                ),

                "evaluated_rows": evaluated,

                "excluded_rows":
                    total_rows - evaluated,

                "affected_rows": affected,

                "affected_percentage": (
                    round(
                        affected / evaluated * 100,
                        4
                    )
                    if evaluated
                    else None
                )
            }

            checks.append(result)

            if affected:

                issue = {
                    **result,
                    "scope": "row",
                    "message": message
                }

                if include_row_positions:

                    issue["row_positions"] = (
                        np.flatnonzero(mask).tolist()
                    )

                issues.append(issue)

        for name, definition in (
            self.contract.columns.items()
        ):

            rules = self.configured_rules(
                definition
            )

            if not rules:

                column_results.append({
                    "column_name": name,
                    "status": "no_constraints",
                    "configured_rules": 0
                })

                continue

            if (
                name not in working.columns
                or name in duplicate_columns
            ):

                reason = (
                    "ambiguous_column"
                    if name in duplicate_columns
                    else "missing_column"
                )

                column_results.append({
                    "column_name": name,
                    "status": reason,
                    "configured_rules": len(rules)
                })

                for rule in rules:

                    checks.append({
                        "column": name,
                        "rule": rule,
                        "severity": definition.severity,
                        "status": "not_evaluable",
                        "reason": reason,
                        "evaluated_rows": 0,
                        "excluded_rows": total_rows,
                        "affected_rows": 0,
                        "affected_percentage": None
                    })

                continue

            series = working[name]

            present = series.notna()

            type_invalid = (
                SchemaValidator.validate_type(
                    series,
                    definition
                )
            )

            eligible = (
                present & ~type_invalid
            )

            severity = definition.severity

            before = len(checks)

            numeric = None

            if definition.dtype in {
                "integer",
                "float",
                "numeric"
            }:

                numeric = self.numeric_values(
                    series
                )

            # Minimum boundary

            if definition.minimum is not None:

                mask = (
                    numeric < definition.minimum
                ).fillna(False)

                evaluate(
                    column=name,
                    rule="minimum",
                    mask=mask,
                    eligible=eligible,
                    severity=severity,
                    message=(
                        f"{name} must be greater "
                        f"than or equal to "
                        f"{definition.minimum}."
                    )
                )

            # Maximum boundary

            if definition.maximum is not None:

                mask = (
                    numeric > definition.maximum
                ).fillna(False)

                evaluate(
                    column=name,
                    rule="maximum",
                    mask=mask,
                    eligible=eligible,
                    severity=severity,
                    message=(
                        f"{name} must be less "
                        f"than or equal to "
                        f"{definition.maximum}."
                    )
                )

            # Accepted domain values

            if definition.allowed_values is not None:

                values = (
                    numeric
                    if numeric is not None
                    else series
                )

                mask = ~values.isin(
                    definition.allowed_values
                )

                evaluate(
                    column=name,
                    rule="allowed_values",
                    mask=mask,
                    eligible=eligible,
                    severity=severity,
                    message=(
                        f"{name} contains values "
                        "outside its accepted domain."
                    )
                )

            # Full regular-expression matching

            if definition.pattern is not None:

                values = series.astype("string")

                matched = values.str.fullmatch(
                    definition.pattern,
                    na=False
                )

                evaluate(
                    column=name,
                    rule="regex_pattern",
                    mask=~matched,
                    eligible=eligible,
                    severity=severity,
                    message=(
                        f"{name} does not match "
                        "the configured format."
                    )
                )

            # Blank and whitespace-only strings

            if not definition.allow_blank:

                blank = series.map(
                    lambda value:
                        isinstance(value, str)
                        and value.strip() == ""
                )

                evaluate(
                    column=name,
                    rule="blank_string",
                    mask=blank,
                    eligible=present,
                    severity=severity,
                    message=(
                        f"{name} contains blank "
                        "or whitespace-only values."
                    )
                )

            # Single-column uniqueness

            if definition.unique:

                values = (
                    numeric
                    if numeric is not None
                    else series
                )

                duplicates = pd.Series(
                    False,
                    index=working.index
                )

                duplicates.loc[eligible] = (
                    values.loc[eligible]
                    .duplicated(keep=False)
                    .to_numpy()
                )

                evaluate(
                    column=name,
                    rule="uniqueness",
                    mask=duplicates,
                    eligible=eligible,
                    severity=severity,
                    message=(
                        f"{name} contains duplicate "
                        "non-null values."
                    )
                )

            completed = checks[before:]

            failed = sum(
                check["status"] == "failed"
                for check in completed
            )

            unavailable = sum(
                check["status"] == "not_evaluable"
                for check in completed
            )

            column_results.append({
                "column_name": name,

                "configured_rules": len(rules),

                "failed_rules": failed,

                "unavailable_rules": unavailable,

                "status": (
                    "failed"
                    if failed
                    else "not_evaluable"
                    if unavailable == len(completed)
                    else "partial"
                    if unavailable
                    else "passed"
                )
            })

        affected = int(invalid_rows.sum())

        severity_summary = {
            severity: sum(
                issue["severity"] == severity
                for issue in issues
            )
            for severity in [
                "critical",
                "high",
                "medium",
                "low"
            ]
        }

        passed_checks = sum(
            check["status"] == "passed"
            for check in checks
        )

        failed_checks = sum(
            check["status"] == "failed"
            for check in checks
        )

        unavailable_checks = sum(
            check["status"] == "not_evaluable"
            for check in checks
        )

        status = (
            "failed"
            if failed_checks
            else "not_applicable"
            if not checks
            else "not_evaluable"
            if unavailable_checks == len(checks)
            else "partial"
            if unavailable_checks
            else "passed"
        )

        result = {

            "contract": {
                "name": self.contract.name,
                "version": self.contract.version,
                "industry": self.contract.industry
            },

            "status": status,

            "summary": {

                "total_rows": total_rows,

                "configured_checks": len(checks),

                "passed_checks": passed_checks,

                "failed_checks": failed_checks,

                "unavailable_checks":
                    unavailable_checks,

                "affected_rows": affected,

                "unflagged_rows":
                    total_rows - affected,

                "affected_percentage": (
                    round(
                        affected / total_rows * 100,
                        4
                    )
                    if total_rows
                    else None
                )
            },

            "severity_summary": severity_summary,

            "columns": column_results,

            "checks": checks,

            "issues": issues,

            "interpretation": (
                "Constraint checks evaluate configured "
                "domain rules. Missing and invalid-type "
                "values are generally excluded and handled "
                "by schema validation. Unflagged records "
                "are not necessarily fully valid. "
                "No records were modified or removed."
            )
        }

        if include_row_positions:

            result["affected_row_positions"] = (
                np.flatnonzero(invalid_rows).tolist()
            )

        return result
