
import gc
import json
import time
import platform
import threading

from datetime import datetime, timezone

import pandas as pd
import numpy as np
import scipy
import psutil

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import UniversalProfiler

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


DATASETS = [
    {
        "industry": "manufacturing",
        "path": "data/external/manufacturing/ai4i2020.csv",
        "expected_rows": 10000,
        "expected_columns": 14
    },
    {
        "industry": "banking",
        "path": "data/external/banking/bank-full.csv",
        "expected_rows": 45211,
        "expected_columns": 17
    },
    {
        "industry": "retail",
        "path": "data/external/retail/online_retail_II.xlsx",
        "expected_rows": 525461,
        "expected_columns": 8
    }
]


class MemoryMonitor:

    def __init__(self, interval=0.05):

        self.process = psutil.Process()

        self.interval = interval

        self.baseline = 0
        self.peak = 0

        self.stop_event = threading.Event()

        self.thread = None

    def sample(self):

        memory = self.process.memory_info().rss

        self.peak = max(self.peak, memory)

    def monitor(self):

        while not self.stop_event.is_set():

            self.sample()

            self.stop_event.wait(self.interval)

    def __enter__(self):

        self.baseline = (
            self.process.memory_info().rss
        )

        self.peak = self.baseline

        self.thread = threading.Thread(
            target=self.monitor,
            daemon=True
        )

        self.thread.start()

        return self

    def __exit__(self, *args):

        self.stop_event.set()

        self.thread.join()

        self.sample()

    def results(self):

        return {

            "baseline_rss_mb": round(
                self.baseline / 1024 ** 2, 2
            ),

            "peak_sampled_rss_mb": round(
                self.peak / 1024 ** 2, 2
            ),

            "additional_peak_rss_mb": round(
                (self.peak - self.baseline)
                / 1024 ** 2, 2
            ),

            "sampling_interval_seconds": self.interval
        }


def benchmark_dataset(dataset):

    industry = dataset["industry"]

    print("\n" + "=" * 65)

    print(f"BENCHMARKING: {industry.upper()}")

    print("=" * 65)

    gc.collect()

    config = load_industry_config(industry)

    file_path = PROJECT_ROOT / dataset["path"]

    total_start = time.perf_counter()

    with MemoryMonitor() as monitor:

        ingestion_start = time.perf_counter()

        df, metadata = DataLoader(config).load(
            file_path
        )

        ingestion_seconds = (
            time.perf_counter() - ingestion_start
        )

        profiler = UniversalProfiler(config)

        profiling_start = time.perf_counter()

        report = profiler.profile(
            df,
            metadata=metadata
        )

        profiling_seconds = (
            time.perf_counter() - profiling_start
        )

        output_path = profiler.save_report(
            report,
            PROJECT_ROOT
            / "reports/profiling"
            / f"{industry}_unified.json"
        )

    total_seconds = (
        time.perf_counter() - total_start
    )

    rows, columns = df.shape

    dimensions_match = (
        rows == dataset["expected_rows"]
        and columns == dataset["expected_columns"]
    )

    failed_modules = report["execution"][
        "failed_modules"
    ]

    completed_modules = report["execution"][
        "completed_modules"
    ]

    passed = (
        dimensions_match
        and failed_modules == 0
        and completed_modules == 7
    )

    result = {

        "industry": industry,

        "status": (
            "PASSED" if passed
            else "REVIEW_REQUIRED"
        ),

        "file_name": metadata.file_name,

        "file_hash": metadata.file_hash,

        "rows": rows,

        "columns": columns,

        "dimensions_match": dimensions_match,

        "ingestion_seconds": round(
            ingestion_seconds, 4
        ),

        "profiling_seconds": round(
            profiling_seconds, 4
        ),

        "total_seconds": round(
            total_seconds, 4
        ),

        "profiling_rows_per_second": round(
            rows / max(profiling_seconds, 1e-9), 2
        ),

        "dataframe_memory_mb": round(
            df.memory_usage(deep=True).sum()
            / 1024 ** 2, 2
        ),

        "process_memory": monitor.results(),

        "report_size_kb": round(
            output_path.stat().st_size / 1024, 2
        ),

        "completed_modules": completed_modules,

        "failed_modules": failed_modules,

        "skipped_modules": report["execution"][
            "skipped_modules"
        ],

        "quality_indicators": report[
            "quality_indicators"
        ],

        "module_performance": {

            name: {

                "status": module["status"],

                "execution_seconds": module[
                    "execution_seconds"
                ],

                "error_type": module.get(
                    "error_type"
                )

            }

            for name, module
            in report["modules"].items()
        }
    }

    print(f"Status: {result['status']}")

    print(f"Records: {rows:,}")

    print(f"Columns: {columns}")

    print(
        f"Ingestion: {ingestion_seconds:.4f}s"
    )

    print(
        f"Profiling: {profiling_seconds:.4f}s"
    )

    print(
        f"Total: {total_seconds:.4f}s"
    )

    print(
        "Profiling throughput:",
        result["profiling_rows_per_second"],
        "rows/sec"
    )

    print(
        "Peak sampled RSS:",
        result["process_memory"][
            "peak_sampled_rss_mb"
        ],
        "MB"
    )

    print("\nMODULE PERFORMANCE")

    for name, module in (
        result["module_performance"].items()
    ):

        print(
            f"{name:22} "
            f"{module['status']:12} "
            f"{module['execution_seconds']:.4f}s"
        )

    return result


def main():

    results = []

    start = time.perf_counter()

    for dataset in DATASETS:

        try:

            result = benchmark_dataset(dataset)

        except Exception as error:

            result = {

                "industry": dataset["industry"],

                "status": "FAILED",

                "error_type": type(error).__name__,

                "error_message": str(error)
            }

            print(
                f"Benchmark failed: {error}"
            )

        results.append(result)

        gc.collect()

    report = {

        "benchmark_version": "1.0.0",

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "environment": {

            "platform": platform.platform(),

            "python_version": platform.python_version(),

            "processor": platform.processor(),

            "logical_cpu_count": psutil.cpu_count(),

            "physical_cpu_count": psutil.cpu_count(
                logical=False
            ),

            "system_memory_gb": round(
                psutil.virtual_memory().total
                / 1024 ** 3, 2
            ),

            "pandas_version": pd.__version__,

            "numpy_version": np.__version__,

            "scipy_version": scipy.__version__
        },

        "methodology": {

            "runs_per_dataset": 1,

            "execution": "sequential",

            "memory_metric": "sampled process RSS",

            "retail_scope": "first Excel worksheet",

            "cache_control": "uncontrolled"
        },

        "summary": {

            "datasets_tested": len(results),

            "datasets_passed": sum(
                r["status"] == "PASSED"
                for r in results
            ),

            "total_records_processed": sum(
                r.get("rows", 0)
                for r in results
            ),

            "total_module_executions_completed": sum(
                r.get("completed_modules", 0)
                for r in results
            ),

            "total_seconds": round(
                time.perf_counter() - start, 4
            )
        },

        "datasets": results
    }

    output_path = (
        PROJECT_ROOT
        / "reports/benchmarks"
        / "cross_industry_profiling.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=4,
            allow_nan=False
        ),
        encoding="utf-8"
    )

    print("\n" + "=" * 65)

    print("CROSS-INDUSTRY BENCHMARK SUMMARY")

    print("=" * 65)

    print(json.dumps(
        report["summary"],
        indent=4
    ))

    print(f"\nReport saved: {output_path}")

    if report["summary"]["datasets_passed"] != len(DATASETS):

        raise SystemExit(1)


if __name__ == "__main__":
    main()
