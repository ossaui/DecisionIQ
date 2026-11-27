
import pandas as pd
import pytest

from decisioniq.ingestion import DataLoader

from decisioniq.utils.config import load_config

from decisioniq.ingestion.exceptions import (
    UnsupportedFormatError,
    EmptyDatasetError,
    FileSizeLimitError,
    DataReadError
)


@pytest.fixture
def loader(tmp_path):

    config = load_config()

    config["storage"]["raw_path"] = str(
        tmp_path / "raw"
    )

    return DataLoader(config)


@pytest.fixture
def sample_df():

    return pd.DataFrame({
        "id": [1, 2, 3],
        "revenue": [100, 200, 300]
    })


def test_csv_loading(
    loader, sample_df, tmp_path
):

    path = tmp_path / "sample.csv"
    sample_df.to_csv(path, index=False)

    df, metadata = loader.load(path)

    pd.testing.assert_frame_equal(
        df, sample_df
    )

    assert metadata.row_count == 3
    assert metadata.column_count == 2


def test_excel_loading(
    loader, sample_df, tmp_path
):

    path = tmp_path / "sample.xlsx"
    sample_df.to_excel(path, index=False)

    df, metadata = loader.load(path)

    assert len(df) == 3
    assert metadata.file_format == "xlsx"


def test_parquet_loading(
    loader, sample_df, tmp_path
):

    path = tmp_path / "sample.parquet"
    sample_df.to_parquet(path, index=False)

    df, metadata = loader.load(path)

    pd.testing.assert_frame_equal(
        df, sample_df
    )

    assert metadata.file_format == "parquet"


def test_missing_file(loader, tmp_path):

    with pytest.raises(FileNotFoundError):
        loader.load(tmp_path / "missing.csv")


def test_unsupported_format(
    loader, tmp_path
):

    path = tmp_path / "sample.txt"
    path.write_text("test", encoding="utf-8")

    with pytest.raises(UnsupportedFormatError):
        loader.load(path)


def test_empty_file(loader, tmp_path):

    path = tmp_path / "empty.csv"
    path.touch()

    with pytest.raises(EmptyDatasetError):
        loader.load(path)


def test_header_only_file(loader, tmp_path):

    path = tmp_path / "header.csv"

    path.write_text(
        "id,revenue\n",
        encoding="utf-8"
    )

    with pytest.raises(EmptyDatasetError):
        loader.load(path)


def test_file_size_limit(loader, tmp_path):

    loader.settings["max_file_size_mb"] = 0

    path = tmp_path / "sample.csv"
    path.write_text("id\n1", encoding="utf-8")

    with pytest.raises(FileSizeLimitError):
        loader.load(path)


def test_hash_consistency(
    loader, sample_df, tmp_path
):

    path = tmp_path / "sample.csv"
    sample_df.to_csv(path, index=False)

    _, metadata1 = loader.load(path)
    _, metadata2 = loader.load(path)

    assert metadata1.file_hash is not None

    assert (
        metadata1.file_hash
        == metadata2.file_hash
    )


def test_raw_file_preservation(
    loader, sample_df, tmp_path
):

    from pathlib import Path

    path = tmp_path / "sample.csv"
    sample_df.to_csv(path, index=False)

    _, metadata = loader.load(path)

    archived = Path(metadata.archived_path)

    assert archived.exists()

    assert (
        archived.read_bytes()
        == path.read_bytes()
    )


def test_corrupted_excel(loader, tmp_path):

    path = tmp_path / "corrupted.xlsx"

    path.write_text(
        "Not an Excel file",
        encoding="utf-8"
    )

    with pytest.raises(DataReadError):
        loader.load(path)


def test_duplicate_rows_preserved(
    loader, tmp_path
):

    path = tmp_path / "duplicates.csv"

    path.write_text(
        "id,revenue\n1,100\n1,100\n",
        encoding="utf-8"
    )

    df, metadata = loader.load(path)

    assert metadata.row_count == 2
    assert df.duplicated().sum() == 1

