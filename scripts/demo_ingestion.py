
import json
from pathlib import Path

from decisioniq.ingestion import DataLoader
from decisioniq.utils.config import PROJECT_ROOT


def main():

    source = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "sample_transactions.csv"
    )

    loader = DataLoader()

    df, metadata = loader.load(source)

    print("\nDATA PREVIEW")
    print(df.head())

    print("\nDATASET METADATA")
    print(
        json.dumps(
            metadata.to_dict(),
            indent=4
        )
    )

    report_dir = PROJECT_ROOT / "reports"

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        report_dir / "ingestion_metadata.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata.to_dict(),
            file,
            indent=4
        )

    print(
        f"\nMetadata report saved: {report_path}"
    )


if __name__ == "__main__":
    main()
