
import hashlib

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DatasetMetadata:

    file_name: str
    file_format: str
    file_size_bytes: int
    file_hash: str | None
    ingested_at: str
    row_count: int
    column_count: int
    column_names: list[str]
    memory_usage_bytes: int
    archived_path: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_file_hash(path: Path) -> str:

    sha256 = hashlib.sha256()

    with path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(65536),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


def generate_metadata(
    path: Path,
    df: pd.DataFrame,
    file_hash: str | None = None,
    archived_path: str | None = None
) -> DatasetMetadata:

    return DatasetMetadata(
        file_name=path.name,
        file_format=path.suffix.lower().lstrip("."),
        file_size_bytes=path.stat().st_size,
        file_hash=file_hash,
        ingested_at=datetime.now(
            timezone.utc
        ).isoformat(),
        row_count=len(df),
        column_count=len(df.columns),
        column_names=[
            str(column) for column in df.columns
        ],
        memory_usage_bytes=int(
            df.memory_usage(deep=True).sum()
        ),
        archived_path=archived_path
    )
