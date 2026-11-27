
import pytest

from decisioniq.utils.config import load_config


def test_default_config_loads():
    config = load_config()

    assert config["project"]["name"] == "DecisionIQ"


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
