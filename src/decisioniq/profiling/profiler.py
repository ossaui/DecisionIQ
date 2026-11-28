
import json
import time
import logging

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from decisioniq.utils.config import load_config

from decisioniq.profiling.structural import StructuralProfiler
from decisioniq.profiling.statistical import StatisticalProfiler
from decisioniq.profiling.missing import MissingValueProfiler
from decisioniq.profiling.outliers import OutlierProfiler
from decisioniq.profiling.relationships import RelationshipProfiler
from decisioniq.profiling.temporal import TemporalProfiler
from decisioniq.profiling.multicollinearity import (
    MulticollinearityProfiler
)


class UniversalProfiler:
    """Unified, configuration-driven dataset profiling engine."""

    MODULES = {
        "structural": StructuralProfiler,
        "statistical": StatisticalProfiler,
        "missing_values": MissingValueProfiler,
        "outliers": OutlierProfiler,
        "relationships": RelationshipProfiler,
        "temporal": TemporalProfiler,
        "multicollinearity": MulticollinearityProfiler
    }

    def __init__(self, config=None):

        self.config = deepcopy(
            config if config is not None
            else load_config()
        )

        self.settings = self.config.get(
            "profiling", {}
        )

        self.execution_settings = self.settings.get(
            "execution", {}
        )

        self.fail_fast = self.execution_settings.get(
            "fail_fast", False
        )

        self.logger = logging.getLogger(
            "decisioniq.profiling"
        )

    def run_module(self, name, profiler_class, df):

        module_config = self.settings.get(
            name, {}
        )

        if not module_config.get("enabled", True):

            return {
                "status": "skipped",
                "reason": "disabled_by_configuration",
                "execution_seconds": 0.0,
                "result": None
            }

        start = time.perf_counter()

        try:

            self.logger.info(
                "Profiling module started: %s", name
            )

            # Structural profiler receives the full
            # profiling configuration.
            if name == "structural":

                profiler = profiler_class(
                    self.settings
                )

            else:

                profiler = profiler_class(
                    module_config
                )

            result = profiler.profile(df)

            # Validate strict JSON compatibility.
            json.dumps(
                result,
                allow_nan=False
            )

            elapsed = time.perf_counter() - start

            self.logger.info(
                "Profiling module completed: %s",
                name
            )

            return {
                "status": "completed",
                "execution_seconds": round(elapsed, 6),
                "result": result
            }

        except Exception as error:

            elapsed = time.perf_counter() - start

            self.logger.error(
                "Profiling module failed: %s (%s)",
                name,
                type(error).__name__
            )

            if self.fail_fast:
                raise

            return {
                "status": "failed",
                "execution_seconds": round(elapsed, 6),
                "error_type": type(error).__name__,
                "result": None
            }

    @staticmethod
    def generate_quality_indicators(df):

        rows, columns = df.shape

        total_cells = rows * columns

        missing_cells = int(
            df.isna().sum().sum()
        )

        duplicate_rows = int(
            df.duplicated().sum()
        )

        completeness = (
            1 - missing_cells / total_cells
        ) * 100

        nonduplicate_percentage = (
            1 - duplicate_rows / rows
        ) * 100

        return {

            "total_cells": total_cells,

            "missing_cells": missing_cells,

            "duplicate_rows": duplicate_rows,

            "completeness_percentage": round(
                completeness, 4
            ),

            "nonduplicate_row_percentage": round(
                nonduplicate_percentage, 4
            ),

            "interpretation": (
                "These are descriptive indicators, "
                "not a validated business data quality score."
            )
        }

    def profile(self, df, metadata=None):

        if not isinstance(df, pd.DataFrame):

            raise TypeError(
                "Expected a pandas DataFrame."
            )

        if df.empty:

            raise ValueError(
                "Cannot profile an empty dataset."
            )

        if not df.columns.is_unique:

            raise ValueError(
                "Duplicate column names detected."
            )

        if not self.settings.get("enabled", True):

            raise RuntimeError(
                "Profiling is disabled."
            )

        start = time.perf_counter()

        modules = {}

        for name, profiler_class in self.MODULES.items():

            modules[name] = self.run_module(
                name,
                profiler_class,
                df
            )

        completed = sum(
            m["status"] == "completed"
            for m in modules.values()
        )

        failed = sum(
            m["status"] == "failed"
            for m in modules.values()
        )

        skipped = sum(
            m["status"] == "skipped"
            for m in modules.values()
        )

        if failed:

            status = (
                "partial_success"
                if completed else "failed"
            )

        elif completed:

            status = "completed"

        else:

            status = "skipped"

        source = {}

        if metadata is not None:

            if hasattr(metadata, "to_dict"):

                source = metadata.to_dict()

            elif isinstance(metadata, dict):

                source = deepcopy(metadata)

            else:

                raise TypeError(
                    "Unsupported metadata type."
                )

        quality = self.generate_quality_indicators(df)

        report = {

            "report_schema_version": "1.0.0",

            "project": "DecisionIQ",

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "industry": self.config.get(
                "business", {}
            ).get("industry", "generic"),

            "status": status,

            "source": source,

            "dataset": {
                "row_count": len(df),
                "column_count": len(df.columns),
                "column_names": list(
                    map(str, df.columns)
                ),
                "memory_usage_bytes": int(
                    df.memory_usage(
                        deep=True
                    ).sum()
                )
            },

            "execution": {
                "total_modules": len(modules),
                "completed_modules": completed,
                "failed_modules": failed,
                "skipped_modules": skipped,
                "total_seconds": round(
                    time.perf_counter() - start, 6
                )
            },

            "quality_indicators": quality,

            "modules": modules
        }

        json.dumps(report, allow_nan=False)

        return report

    @staticmethod
    def save_report(report, output_path):

        output_path = Path(output_path)

        # Serialize before writing to avoid incomplete
        # reports caused by invalid JSON values.
        content = json.dumps(
            report,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path.write_text(
            content,
            encoding="utf-8"
        )

        return output_path
