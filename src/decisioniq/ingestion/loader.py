
from pathlib import Path
from shutil import copy2
from uuid import uuid4

import pandas as pd

from decisioniq.utils.config import (
    load_config,
    PROJECT_ROOT
)

from decisioniq.utils.logger import get_logger

from decisioniq.ingestion.metadata import (
    DatasetMetadata,
    calculate_file_hash,
    generate_metadata
)

from decisioniq.ingestion.exceptions import (
    UnsupportedFormatError,
    EmptyDatasetError,
    FileSizeLimitError,
    DataReadError
)


logger = get_logger("decisioniq.ingestion")


class DataLoader:

    def __init__(self, config=None):

        self.config = (
            config if config is not None
            else load_config()
        )

        self.settings = self.config["ingestion"]

        self.supported_formats = {
            f".{fmt.lower().lstrip('.')}"
            for fmt in self.settings[
                "supported_formats"
            ]
        }

    def validate_file(self, path: Path) -> None:

        if not path.is_file():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if path.suffix.lower() not in (
            self.supported_formats
        ):
            raise UnsupportedFormatError(
                f"Unsupported format: {path.suffix}"
            )

        max_bytes = (
            self.settings.get(
                "max_file_size_mb", 250
            ) * 1024 * 1024
        )

        if path.stat().st_size > max_bytes:
            raise FileSizeLimitError(
                "File exceeds configured size limit."
            )

        if path.stat().st_size == 0:
            raise EmptyDatasetError(
                "The input file is empty."
            )

    def archive_file(
        self,
        path: Path,
        file_hash: str | None
    ) -> Path:

        raw_dir = Path(
            self.config["storage"]["raw_path"]
        )

        if not raw_dir.is_absolute():
            raw_dir = PROJECT_ROOT / raw_dir

        raw_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        identifier = file_hash or uuid4().hex

        destination = (
            raw_dir
            / f"{identifier}{path.suffix.lower()}"
        )

        if not destination.exists():
            copy2(path, destination)

        return destination

    def read_file(self, path: Path) -> pd.DataFrame:

        extension = path.suffix.lower()

        try:

            if extension == ".csv":

                return pd.read_csv(
                    path,
                    encoding=self.settings.get(
                        "encoding", "utf-8"
                    ),
                    sep=self.settings.get(
                        "csv_separator", ","
                    )
                )

            if extension == ".xlsx":

                return pd.read_excel(
                    path,
                    sheet_name=self.settings.get(
                        "excel_sheet", 0
                    ),
                    engine="openpyxl"
                )

            if extension == ".parquet":

                return pd.read_parquet(path)

        except pd.errors.EmptyDataError as error:

            raise EmptyDatasetError(
                "No readable data found."
            ) from error

        except Exception as error:

            raise DataReadError(
                f"Unable to read {extension} file."
            ) from error

        raise UnsupportedFormatError(extension)

    def load(
        self,
        file_path: str | Path
    ) -> tuple[pd.DataFrame, DatasetMetadata]:

        path = Path(file_path).resolve()

        logger.info(
            "Ingestion started: format=%s",
            path.suffix.lower()
        )

        self.validate_file(path)

        file_hash = None

        if self.settings.get(
            "calculate_file_hash", True
        ):
            file_hash = calculate_file_hash(path)

        archived_path = None

        if self.settings.get(
            "preserve_raw_data", True
        ):
            archived_path = self.archive_file(
                path,
                file_hash
            )

        read_path = archived_path or path

        df = self.read_file(read_path)

        if df.empty:
            raise EmptyDatasetError(
                "Dataset contains no records."
            )

        metadata = generate_metadata(
            path=path,
            df=df,
            file_hash=file_hash,
            archived_path=(
                str(archived_path)
                if archived_path else None
            )
        )

        logger.info(
            "Ingestion completed: rows=%d, columns=%d",
            metadata.row_count,
            metadata.column_count
        )

        return df, metadata
