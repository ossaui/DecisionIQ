
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import StructuralProfiler

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

    loader = DataLoader(config)

    df, metadata = loader.load(path)

    profiler = StructuralProfiler(
        config["profiling"]
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

    print("\nDATASET SUMMARY")

    print(json.dumps(
        report["dataset_summary"],
        indent=4
    ))

    print("\nCANDIDATE KEYS")
    print(report["candidate_keys"])

    print("\nCONSTANT COLUMNS")
    print(report["constant_columns"])

    print("\nEMPTY COLUMNS")
    print(report["empty_columns"])

    print("\nCOLUMN PROFILES")

    for column in report["columns"]:

        print(
            f"{column['column_name']:35} "
            f"{column['detected_type']:15} "
            f"Missing: {column['missing_percentage']}%"
        )

    report_dir = (
        PROJECT_ROOT / "reports" / "profiling"
    )

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        report_dir
        / "manufacturing_structural.json"
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
