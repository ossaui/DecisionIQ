
import json
import time

from decisioniq.ingestion import DataLoader

from decisioniq.profiling import (
    TemporalProfiler,
    MulticollinearityProfiler
)

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)


def save_report(report, filename):

    directory = PROJECT_ROOT / "reports/profiling"

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    path = directory / filename

    with path.open("w", encoding="utf-8") as file:

        json.dump(
            report,
            file,
            indent=4,
            allow_nan=False
        )

    print(f"Report saved: {path}")


def run_temporal():

    config = load_industry_config("retail")

    df, metadata = DataLoader(config).load(
        PROJECT_ROOT
        / "data/external/retail/online_retail_II.xlsx"
    )

    start = time.perf_counter()

    report = TemporalProfiler(
        config["profiling"]["temporal"]
    ).profile(df)

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash
    }

    report["profiling_seconds"] = round(
        time.perf_counter() - start, 4
    )

    print("\nTEMPORAL INTELLIGENCE")

    for column in report["columns"]:

        print(column["column_name"])

        print(json.dumps(
            column.get("coverage", column),
            indent=4
        ))

    save_report(
        report,
        "retail_temporal.json"
    )


def run_multicollinearity():

    config = load_industry_config("manufacturing")

    df, metadata = DataLoader(config).load(
        PROJECT_ROOT
        / "data/external/manufacturing/ai4i2020.csv"
    )

    start = time.perf_counter()

    report = MulticollinearityProfiler(
        config["profiling"]["multicollinearity"]
    ).profile(df)

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash
    }

    report["profiling_seconds"] = round(
        time.perf_counter() - start, 4
    )

    print("\nMULTICOLLINEARITY INTELLIGENCE")

    print(json.dumps(
        report.get("summary", report),
        indent=4
    ))

    for column in report["columns"]:

        vif = column["vif"]

        display = (
            f"{vif:.4f}"
            if vif is not None
            else "Infinite"
        )

        print(
            f"{column['column_name']:35} "
            f"VIF={display:12} "
            f"{column['severity']}"
        )

    save_report(
        report,
        "manufacturing_multicollinearity.json"
    )


def main():

    run_temporal()

    run_multicollinearity()

    print("\nAdvanced profiling completed.")


if __name__ == "__main__":
    main()
