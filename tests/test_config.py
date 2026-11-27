
import pytest

from decisioniq.utils.config import load_config


def test_default_config_loads():
    config = load_config()

    assert config["project"]["name"] == "DecisionIQ"


from decisioniq.utils.config import (
    merge_configs,
    load_industry_config
)


def test_nested_config_merge():

    base = {
        "ingestion": {
            "encoding": "utf-8",
            "csv_separator": ","
        }
    }

    override = {
        "ingestion": {
            "csv_separator": ";"
        }
    }

    result = merge_configs(base, override)

    assert result["ingestion"]["csv_separator"] == ";"
    assert result["ingestion"]["encoding"] == "utf-8"
    assert base["ingestion"]["csv_separator"] == ","


def test_banking_config():

    config = load_industry_config("banking")

    assert config["ingestion"]["csv_separator"] == ";"
    assert config["ingestion"]["preserve_raw_data"] is True


def test_retail_config():

    config = load_industry_config("retail")

    assert config["ingestion"]["excel_sheet"] == 0


def test_unknown_industry():

    with pytest.raises(FileNotFoundError):
        load_industry_config("unknown_industry")


def test_required_sections_exist():
    config = load_config()

    required = [
        "project",
        "storage",
        "ingestion",
        "profiling",
        "validation",
        "analytics"
    ]

    for section in required:
        assert section in config


def test_missing_config_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")


def test_invalid_yaml(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("project: [invalid", encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(path)


def test_missing_required_sections(tmp_path):
    path = tmp_path / "incomplete.yaml"
    path.write_text(
        "project:\n  name: DecisionIQ",
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        load_config(path)
