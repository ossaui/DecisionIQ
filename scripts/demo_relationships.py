
import json
import time

from decisioniq.ingestion import DataLoader
from decisioniq.profiling import RelationshipProfiler

from decisioniq.profiling.visualizations import (
    save_correlation_heatmap
)

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

    profiler = RelationshipProfiler(
        config["profiling"]["relationships"]
    )

    start = time.perf_counter()

    report = profiler.profile(df)

    elapsed = time.perf_counter() - start

    report["source"] = {
        "file_name": metadata.file_name,
        "file_hash": metadata.file_hash,
        "industry": "manufacturing"
    }

    report["profiling_seconds"] = round(elapsed, 4)

    # 1. Print relationship summary

    print("\nRELATIONSHIP SUMMARY")

    print(json.dumps(
        report["summary"],
        indent=4
    ))

    # 2. Print numerical relationships

    print("\nTOP NUMERIC RELATIONSHIPS")

    for result in report["numeric_relationships"][:15]:

        print(
            f"{result['column_a']} vs "
            f"{result['column_b']} | "
            f"{result['method']} | "
            f"coefficient={result['coefficient']:.4f} | "
            f"adjusted p="
            f"{result['adjusted_p_value']:.4g}"
        )

    # 3. Print categorical relationships

    print("\nTOP CATEGORICAL RELATIONSHIPS")

    for result in report["categorical_relationships"][:10]:

        print(
            f"{result['column_a']} vs "
            f"{result['column_b']} | "
            f"Cramer's V={result['cramers_v']:.4f} | "
            f"assumptions_met="
            f"{result['assumptions_met']}"
        )

    # 4. Create report directory

    report_dir = PROJECT_ROOT / "reports/profiling"

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # 5. Save JSON report

    report_path = (
        report_dir
        / "manufacturing_relationships.json"
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

    # 6. Generate correlation heatmap

    heatmap_path = save_correlation_heatmap(
        df=df,
        output_path=(
            report_dir
            / "manufacturing_correlation.png"
        ),
        method="pearson",
        excluded_columns=config["profiling"][
            "relationships"
        ].get("excluded_columns", [])
    )

    # 7. Print heatmap location

    print(f"Heatmap saved: {heatmap_path}")

    print("\nRelationship profiling completed successfully!")


if __name__ == "__main__":
    main()
