
import json
import time

from decisioniq.ingestion import DataLoader

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)

from decisioniq.validation import (
    ConstraintValidator,
    load_industry_contract
)


DATASETS = {

    "manufacturing":
        "data/external/manufacturing/ai4i2020.csv",

    "retail":
        "data/external/retail/online_retail_II.xlsx",

    "banking":
        "data/external/banking/bank-full.csv"
}


def main():

    report_dir = (
        PROJECT_ROOT
        / "reports"
        / "validation"
    )

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 65)
    print("DECISIONIQ CONSTRAINT VALIDATION")
    print("=" * 65)

    for industry, relative_path in DATASETS.items():

        print(f"\nINDUSTRY: {industry.upper()}")
        print("-" * 55)

        config = load_industry_config(industry)

        contract = load_industry_contract(industry)

        df, metadata = DataLoader(config).load(
            PROJECT_ROOT / relative_path
        )

        validator = ConstraintValidator(
            contract
        )

        start = time.perf_counter()

        result = validator.validate(df)

        result["execution_seconds"] = round(
            time.perf_counter() - start,
            6
        )

        result["source"] = {
            "file_name": metadata.file_name,
            "file_hash": metadata.file_hash
        }

        summary = result["summary"]

        print("Records:", f"{len(df):,}")

        print(
            "Status:",
            result["status"].upper()
        )

        print(
            "Configured checks:",
            summary["configured_checks"]
        )

        print(
            "Passed checks:",
            summary["passed_checks"]
        )

        print(
            "Failed checks:",
            summary["failed_checks"]
        )

        print(
            "Unavailable checks:",
            summary["unavailable_checks"]
        )

        print(
            "Affected rows:",
            f"{summary['affected_rows']:,}"
        )

        print(
            "Affected percentage:",
            summary["affected_percentage"]
        )

        print(
            "Execution seconds:",
            result["execution_seconds"]
        )

        for issue in result["issues"]:

            print(
                f"  [{issue['severity'].upper()}] "
                f"{issue['column']} | "
                f"{issue['rule']} | "
                f"{issue['affected_rows']:,} rows"
            )

        output = (
            report_dir
            / f"{industry}_constraints.json"
        )

        output.write_text(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False,
                allow_nan=False
            ),
            encoding="utf-8"
        )

        print("Report saved:", output)

    print("\nConstraint validation completed.")


if __name__ == "__main__":
    main()
