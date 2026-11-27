
from itertools import combinations

import pandas as pd


class MissingValueProfiler:
    """Analyze dataset completeness and missingness patterns."""

    def __init__(self, config=None):

        self.config = config or {}

        self.warning_threshold = self.config.get(
            "warning_threshold", 10
        )

        self.critical_threshold = self.config.get(
            "critical_threshold", 40
        )

        self.max_pattern_columns = self.config.get(
            "max_pattern_columns", 30
        )

        self.critical_columns = set(
            self.config.get("critical_columns", [])
        )

        if not (
            0 <= self.warning_threshold
            <= self.critical_threshold <= 100
        ):
            raise ValueError("Invalid missingness thresholds.")

    def classify_severity(self, percentage):

        if percentage == 0:
            return "complete"

        if percentage == 100:
            return "empty"

        if percentage >= self.critical_threshold:
            return "critical"

        if percentage >= self.warning_threshold:
            return "warning"

        return "low"

    @staticmethod
    def recommend_action(severity, critical):

        if severity == "complete":
            return "No missing-value action required."

        if severity == "empty":
            return (
                "Investigate source availability before "
                "using this column."
            )

        if critical:
            return (
                "Investigate missing business-critical "
                "values before downstream analysis."
            )

        if severity == "critical":
            return (
                "Assess analytical usefulness and "
                "investigate the missingness mechanism."
            )

        if severity == "warning":
            return (
                "Investigate missingness patterns and "
                "evaluate suitable treatment."
            )

        return (
            "Monitor missingness and assess whether "
            "treatment is necessary."
        )

    def analyze_patterns(self, mask):

        missing_counts = mask.sum()

        affected_columns = missing_counts[
            missing_counts > 0
        ].sort_values(ascending=False)

        selected = affected_columns.index[
            :self.max_pattern_columns
        ].tolist()

        patterns = []

        for first, second in combinations(selected, 2):

            both_missing = int(
                (mask[first] & mask[second]).sum()
            )

            either_missing = int(
                (mask[first] | mask[second]).sum()
            )

            if both_missing == 0:
                continue

            patterns.append({
                "column_a": str(first),
                "column_b": str(second),
                "both_missing_count": both_missing,
                "jaccard_similarity": round(
                    both_missing / either_missing, 4
                )
            })

        patterns.sort(
            key=lambda item: item["jaccard_similarity"],
            reverse=True
        )

        return {
            "columns_examined": len(selected),
            "columns_with_missing_values": len(
                affected_columns
            ),
            "analysis_truncated": (
                len(affected_columns) > len(selected)
            ),
            "total_matching_pairs": len(patterns),
            "top_co_missing_patterns": patterns[:20]
        }

    def profile(self, df):

        if df.empty:
            raise ValueError(
                "Cannot profile an empty dataset."
            )

        if not df.columns.is_unique:
            raise ValueError(
                "Duplicate column names detected."
            )

        rows, columns = df.shape

        mask = df.isna()

        column_profiles = []

        for column in df.columns:

            missing_count = int(mask[column].sum())

            percentage = missing_count / rows * 100

            severity = self.classify_severity(
                percentage
            )

            critical = (
                str(column) in self.critical_columns
            )

            column_profiles.append({
                "column_name": str(column),
                "missing_count": missing_count,
                "missing_percentage": round(
                    percentage, 4
                ),
                "completeness_percentage": round(
                    100 - percentage, 4
                ),
                "severity": severity,
                "business_critical": critical,
                "recommended_action": (
                    self.recommend_action(
                        severity, critical
                    )
                )
            })

        column_profiles.sort(
            key=lambda item: item["missing_count"],
            reverse=True
        )

        row_missing_counts = mask.sum(axis=1)

        total_missing = int(mask.sum().sum())

        complete_rows = int(
            (row_missing_counts == 0).sum()
        )

        fully_missing_rows = int(
            (row_missing_counts == columns).sum()
        )

        critical_issues = [
            item["column_name"]
            for item in column_profiles
            if item["business_critical"]
            and item["missing_count"] > 0
        ]

        return {

            "summary": {
                "total_cells": rows * columns,
                "missing_cells": total_missing,
                "missing_percentage": round(
                    total_missing / (rows * columns)
                    * 100, 4
                ),
                "completeness_percentage": round(
                    (1 - total_missing / (rows * columns))
                    * 100, 4
                ),
                "complete_rows": complete_rows,
                "incomplete_rows": rows - complete_rows,
                "fully_missing_rows": fully_missing_rows,
                "complete_row_percentage": round(
                    complete_rows / rows * 100, 4
                ),
                "affected_columns": sum(
                    item["missing_count"] > 0
                    for item in column_profiles
                )
            },

            "severity_summary": {
                severity: sum(
                    item["severity"] == severity
                    for item in column_profiles
                )
                for severity in [
                    "complete",
                    "low",
                    "warning",
                    "critical",
                    "empty"
                ]
            },

            "business_critical_issues": critical_issues,

            "unmapped_critical_columns": sorted(
                self.critical_columns
                - set(map(str, df.columns))
            ),

            "columns": column_profiles,

            "missingness_patterns": (
                self.analyze_patterns(mask)
            )
        }
