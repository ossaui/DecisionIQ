
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

def merge_configs(base: dict, override: dict) -> dict:
    """Merge default and business-specific configurations."""

    from copy import deepcopy

    merged = deepcopy(base)

    for key, value in override.items():

        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = merge_configs(
                merged[key], value
            )

        else:
            merged[key] = deepcopy(value)

    return merged


def load_industry_config(industry: str) -> dict:
    """Load default configuration with industry overrides."""

    base_config = load_config()

    industry_path = (
        PROJECT_ROOT
        / "configs"
        / "industries"
        / f"{industry}.yaml"
    )

    if not industry_path.is_file():
        raise FileNotFoundError(
            f"Industry configuration not found: {industry}"
        )

    with industry_path.open(
        "r", encoding="utf-8-sig"
    ) as file:

        industry_config = yaml.safe_load(file)

    if not isinstance(industry_config, dict):
        raise ValueError(
            "Industry configuration must be a mapping."
        )

    return merge_configs(
        base_config, industry_config
    )

if __name__ == "__main__":
    config = load_config()
    print("Configuration loaded successfully!")
    print("Project:", config["project"]["name"])
    print("Version:", config["project"]["version"])
    print("Database:", config["storage"]["database_path"])
