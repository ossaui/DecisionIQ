
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import MissingValueProfiler

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


def main():

    config = load_industry_config("retail")

    path = (
        PROJECT_ROOT
        / "data/external/retail/online_retail_II.xlsx"
    )

    df, metadata = DataLoader(config).load(path)

    profiler = MissingValueProfiler(
        config["profiling"]["missing_values"]
    )

    start = time.perf_counter()

    report = profiler.profile(df)

    elapsed = time.perf_counter() - start

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash,
        "industry": "retail"
    }

    report["profiling_seconds"] = round(elapsed, 4)

    print("\nMISSING VALUE SUMMARY")

    print(json.dumps(
        report["summary"],
        indent=4
    ))

    print("\nCOLUMN COMPLETENESS")

    for column in report["columns"]:

        print(
            f"{column['column_name']:25} "
            f"{column['missing_percentage']:8.2f}% "
            f"{column['severity']}"
        )

    print("\nMISSINGNESS PATTERNS")

    print(json.dumps(
        report["missingness_patterns"],
        indent=4
    ))

    report_dir = PROJECT_ROOT / "reports/profiling"

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        report_dir / "retail_missing.json"
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
