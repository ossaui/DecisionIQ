
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


DATASETS = [
    {
        "industry": "retail",
        "path": "data/external/retail/online_retail_II.xlsx",
        "expected_rows": 525461,
        "expected_columns": 8
    },
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
    }
]


def test_dataset(dataset):

    industry = dataset["industry"]
    path = PROJECT_ROOT / dataset["path"]

    print("\n" + "=" * 60)
    print(f"INDUSTRY: {industry.upper()}")
    print("=" * 60)

    try:
        config = load_industry_config(industry)
        loader = DataLoader(config)

        start = time.perf_counter()

        df, metadata = loader.load(path)

        elapsed = time.perf_counter() - start

        rows_match = (
            len(df) == dataset["expected_rows"]
        )

        columns_match = (
            len(df.columns) == dataset["expected_columns"]
        )

        status = (
            "PASSED"
            if rows_match and columns_match
            else "REVIEW_REQUIRED"
        )

        result = {
            "industry": industry,
            "dataset": path.name,
            "status": status,
            "rows": len(df),
            "columns": len(df.columns),
            "rows_match": rows_match,
            "columns_match": columns_match,
            "missing_cells": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "memory_mb": round(
                metadata.memory_usage_bytes / (1024 ** 2), 3
            ),
            "ingestion_seconds": round(elapsed, 4),
            "file_hash": metadata.file_hash
        }

        print(json.dumps(result, indent=4))

        return result

    except Exception as error:

        result = {
            "industry": industry,
            "dataset": path.name,
            "status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error)
        }

        print(json.dumps(result, indent=4))

        return result


def main():

    results = []

    for dataset in DATASETS:
        results.append(test_dataset(dataset))

    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = (
        report_dir / "cross_industry_validation.json"
    )

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    passed = sum(
        result["status"] == "PASSED"
        for result in results
    )

    total_rows = sum(
        result.get("rows", 0)
        for result in results
    )

    print("\n" + "=" * 60)
    print("CROSS-INDUSTRY VALIDATION SUMMARY")
    print("=" * 60)

    for result in results:
        print(
            f"{result['industry']:20}"
            f"{result['status']}"
        )

    print(f"\nDatasets passed: {passed}/{len(results)}")
    print(f"Total records ingested: {total_rows:,}")
    print(f"Report saved: {report_path}")

    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
