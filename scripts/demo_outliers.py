
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import OutlierProfiler

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


def main():

    config = load_industry_config("manufacturing")

    path = (
        PROJECT_ROOT
        / "data/external/manufacturing/ai4i2020.csv"
    )

    df, metadata = DataLoader(config).load(path)

    profiler = OutlierProfiler(
        config["profiling"]["outliers"]
    )

    start = time.perf_counter()

    report = profiler.profile(df)

    elapsed = time.perf_counter() - start

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash,
        "industry": "manufacturing"
    }

    report["profiling_seconds"] = round(
        elapsed, 4
    )

    print("\nOUTLIER DETECTION SUMMARY")

    print("-" * 85)

    print(
        f"{'Column':35}"
        f"{'IQR':>10}"
        f"{'Z-score':>10}"
        f"{'Modified Z':>15}"
        f"{'Consensus':>12}"
    )

    print("-" * 85)

    for column in report["columns"]:

        if column["status"] != "profiled":

            print(
                column["column_name"],
                column["status"]
            )

            continue

        methods = column["methods"]

        agreement = column["agreement"]

        consensus = agreement[
            "consensus_outlier_count"
        ]

        print(
            f"{column['column_name']:35}"
            f"{methods['iqr']['outlier_count']:>10}"
            f"{methods['zscore']['outlier_count']:>10}"
            f"{methods['modified_zscore']['outlier_count']:>15}"
            f"{str(consensus):>12}"
        )

    report_dir = (
        PROJECT_ROOT / "reports/profiling"
    )

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        report_dir
        / "manufacturing_outliers.json"
    )

    with report_path.open(
        "w", encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            allow_nan=False
        )

    print(f"\nProfiling time: {elapsed:.4f} seconds")
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
