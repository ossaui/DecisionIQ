
import json
import time

from pathlib import Path

from decisioniq.ingestion import DataLoader

from decisioniq.utils.config import (
    PROJECT_ROOT,
    load_industry_config
)

from decisioniq.validation import (
    SchemaValidator,
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
    print("DECISIONIQ SCHEMA VALIDATION")
    print("=" * 65)

    for industry, relative_path in DATASETS.items():

        print(f"\nINDUSTRY: {industry.upper()}")
        print("-" * 50)

        config = load_industry_config(
            industry
        )

        contract = load_industry_contract(
            industry
        )

        loader = DataLoader(config)

        df, metadata = loader.load(
            PROJECT_ROOT / relative_path
        )

        validator = SchemaValidator(
            contract
        )

        start = time.perf_counter()

        result = validator.validate(df)

        elapsed = round(
            time.perf_counter() - start,
            6
        )

        result["execution_seconds"] = elapsed

        result["source"] = {
            "file_name": metadata.file_name,
            "file_hash": metadata.file_hash
        }

        summary = result["summary"]

        print(
            "Records:",
            f"{summary['total_rows']:,}"
        )

        print(
            "Columns:",
            summary["actual_columns"]
        )

        print(
            "Validation status:",
            result["status"].upper()
        )

        print(
            "Total issues:",
            summary["total_issues"]
        )

        print(
            "Affected rows:",
            f"{summary['affected_rows']:,}"
        )

        print(
            "Missing required columns:",
            summary["missing_required_columns"]
        )

        print(
            "Primary key:",
            result["primary_key"]["status"]
        )

        print(
            "Validation seconds:",
            elapsed
        )

        for issue in result["issues"]:

            print(
                f"  [{issue['severity'].upper()}] "
                f"{issue['rule']} | "
                f"{issue['column']} | "
                f"Affected: {issue['affected_rows']}"
            )

        output = (
            report_dir
            / f"{industry}_schema.json"
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

        print(f"Report saved: {output}")

    print("\nSchema validation completed.")


if __name__ == "__main__":
    main()
