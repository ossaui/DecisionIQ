
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import StatisticalProfiler

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

    profiler = StatisticalProfiler(
        config["profiling"]["statistical"]
    )

    start = time.perf_counter()

    report = profiler.profile(df)

    elapsed = time.perf_counter() - start

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash
    }

    report["profiling_seconds"] = round(elapsed, 4)

    for column in report["columns"]:

        print("\n" + "=" * 60)
        print(column["column_name"])
        print("=" * 60)

        print(json.dumps(column, indent=4))

    report_dir = PROJECT_ROOT / "reports/profiling"

    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = (
        report_dir / "manufacturing_statistical.json"
    )

    with report_path.open("w", encoding="utf-8") as file:

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
