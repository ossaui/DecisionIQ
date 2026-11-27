
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "default.yaml"


def load_config(config_path=None) -> dict:
    """Load and validate a YAML configuration file."""

    path = (
        Path(config_path)
        if config_path is not None
        else DEFAULT_CONFIG
    )

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

    except yaml.YAMLError as error:
        raise ValueError(
            f"Invalid YAML configuration: {error}"
        ) from error

    if not isinstance(config, dict):
        raise ValueError(
            "Configuration must contain a YAML mapping."
        )

    required_sections = [
        "project",
        "storage",
        "ingestion",
        "profiling",
        "validation",
        "analytics"
    ]

    for section in required_sections:
        if section not in config:
            raise ValueError(
                f"Missing configuration section: {section}"
            )

        if not isinstance(config[section], dict):
            raise ValueError(
                f"Section must be a mapping: {section}"
            )

    return config


if __name__ == "__main__":
    config = load_config()

    print("Configuration loaded successfully!")
    print("Project:", config["project"]["name"])
    print("Version:", config["project"]["version"])
    print("Database:", config["storage"]["database_path"])
