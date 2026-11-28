
from pathlib import Path
from typing import Any, Literal

import yaml

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)

from decisioniq.utils.config import PROJECT_ROOT


Severity = Literal[
    "critical",
    "high",
    "medium",
    "low"
]

DataType = Literal[
    "integer",
    "float",
    "numeric",
    "string",
    "datetime",
    "boolean",
    "category"
]


class ColumnContract(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False
    )

    dtype: DataType

    required: bool = True

    nullable: bool = True

    unique: bool = False

    minimum: float | None = None

    maximum: float | None = None

    allowed_values: list[Any] | None = None

    pattern: str | None = None

    date_format: str | None = None

    allow_blank: bool = True

    severity: Severity = "high"

    description: str = ""

    @model_validator(mode="after")
    def validate_constraints(self):

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError(
                "Minimum cannot exceed maximum."
            )

        if (
            self.minimum is not None
            or self.maximum is not None
        ) and self.dtype not in {
            "integer",
            "float",
            "numeric"
        }:
            raise ValueError(
                "Range constraints require numeric data."
            )

        if (
            self.allowed_values is not None
            and len(self.allowed_values) == 0
        ):
            raise ValueError(
                "Allowed values cannot be empty."
            )

        if self.pattern is not None:

            import re

            if self.dtype not in {
                "string", "category"
            }:
                raise ValueError(
                    "Pattern requires string data."
                )

            try:
                re.compile(self.pattern)
            except re.error as error:
                raise ValueError(
                    f"Invalid regex: {error}"
                ) from error

        if (
            self.date_format is not None
            and self.dtype != "datetime"
        ):
            raise ValueError(
                "Date format requires datetime data."
            )

        return self


class DatasetContract(BaseModel):

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)

    version: str = "1.0.0"

    industry: str = Field(min_length=1)

    description: str = ""

    grain: str = Field(min_length=1)

    allow_extra_columns: bool = True

    minimum_rows: int = Field(
        default=1,
        ge=1
    )

    maximum_rows: int | None = Field(
        default=None,
        ge=1
    )

    primary_key: list[str] = Field(
        default_factory=list
    )

    columns: dict[str, ColumnContract]

    @model_validator(mode="after")
    def validate_contract(self):

        if not self.columns:
            raise ValueError(
                "Contract must define columns."
            )

        if (
            self.maximum_rows is not None
            and self.maximum_rows < self.minimum_rows
        ):
            raise ValueError(
                "Maximum rows cannot be below minimum."
            )

        if len(self.primary_key) != len(
            set(self.primary_key)
        ):
            raise ValueError(
                "Duplicate primary-key columns."
            )

        for column in self.primary_key:

            if column not in self.columns:
                raise ValueError(
                    f"Undefined primary key: {column}"
                )

            definition = self.columns[column]

            if not definition.required:
                raise ValueError(
                    f"Primary key must be required: {column}"
                )

            if definition.nullable:
                raise ValueError(
                    f"Primary key cannot be nullable: {column}"
                )

        return self


def load_contract(
    path: str | Path
) -> DatasetContract:

    path = Path(path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.is_file():
        raise FileNotFoundError(
            f"Contract not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig"
    ) as file:

        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Contract must contain a YAML mapping."
        )

    return DatasetContract.model_validate(data)


def load_industry_contract(
    industry: str
) -> DatasetContract:

    import re

    if not re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        industry
    ):
        raise ValueError(
            "Invalid industry identifier."
        )

    path = (
        PROJECT_ROOT
        / "configs"
        / "contracts"
        / f"{industry}.yaml"
    )

    return load_contract(path)
