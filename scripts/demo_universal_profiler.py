
import json

from decisioniq.ingestion import DataLoader

from decisioniq.profiling import UniversalProfiler

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


def main():

    config = load_industry_config(
        "manufacturing"
    )

    file_path = (
        PROJECT_ROOT
        / "data/external/manufacturing/ai4i2020.csv"
    )

    df, metadata = DataLoader(config).load(
        file_path
    )

    profiler = UniversalProfiler(config)

    report = profiler.profile(
        df,
        metadata=metadata
    )

    print("\n" + "=" * 65)
    print("DECISIONIQ | UNIVERSAL DATA INTELLIGENCE")
    print("=" * 65)

    print("\nDATASET OVERVIEW")

    print(
        f"Industry: {report['industry']}"
    )

    print(
        f"Rows: {report['dataset']['row_count']:,}"
    )

    print(
        f"Columns: {report['dataset']['column_count']}"
    )

    print(
        f"Status: {report['status']}"
    )

    print("\nMODULE EXECUTION")

    for name, module in report["modules"].items():

        print(
            f"{name:22} "
            f"{module['status']:12} "
            f"{module['execution_seconds']:.4f}s"
        )

        if module["status"] == "failed":

            print(
                f"  Error: {module['error_type']}"
            )

    print("\nQUALITY INDICATORS")

    print(json.dumps(
        report["quality_indicators"],
        indent=4
    ))

    print("\nEXECUTION SUMMARY")

    print(json.dumps(
        report["execution"],
        indent=4
    ))

    path = profiler.save_report(
        report,
        PROJECT_ROOT
        / "reports/profiling/manufacturing_unified.json"
    )

    print(f"\nReport saved: {path}")

    if report["execution"]["failed_modules"]:

        raise SystemExit(1)


if __name__ == "__main__":
    main()
