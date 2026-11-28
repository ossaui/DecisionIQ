
import json

import numpy as np
import pandas as pd
import pytest

from decisioniq.validation import (
    ColumnContract,
    DatasetContract,
    SchemaValidator
)


@pytest.fixture
def contract():

    return DatasetContract(
        name="Test transactions",
        industry="test",
        grain="One transaction per ID",

        primary_key=["id"],

        columns={
            "id": ColumnContract(
                dtype="integer",
                nullable=False,
                unique=True,
                severity="critical"
            ),

            "amount": ColumnContract(
                dtype="numeric",
                nullable=False
            ),

            "customer": ColumnContract(
                dtype="string",
                nullable=True
            )
        }
    )


@pytest.fixture
def valid_df():

    return pd.DataFrame({
        "id": [1, 2, 3],
        "amount": [100.5, 200.0, 300.0],
        "customer": ["A", "B", "C"]
    })


def test_valid_dataset(contract, valid_df):

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "passed"

    assert result["summary"]["total_issues"] == 0


def test_missing_required_column(
    contract, valid_df
):

    df = valid_df.drop(columns=["amount"])

    result = SchemaValidator(
        contract
    ).validate(df)

    assert result["status"] == "failed"

    assert (
        "amount"
        in result["schema_drift"]["missing_required"]
    )


def test_unexpected_column_allowed(
    contract, valid_df
):

    valid_df["extra"] = 1

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "passed"

    assert (
        "extra"
        in result["schema_drift"]["unexpected_columns"]
    )


def test_unexpected_column_rejected(
    contract, valid_df
):

    contract.allow_extra_columns = False

    valid_df["extra"] = 1

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "failed"


def test_nullable_column(
    contract, valid_df
):

    valid_df.loc[0, "customer"] = None

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "passed"


def test_non_nullable_column(
    contract, valid_df
):

    valid_df.loc[0, "amount"] = np.nan

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "failed"

    assert result["summary"]["affected_rows"] == 1


def test_invalid_numeric_value(
    contract, valid_df
):

    valid_df["amount"] = [
        100, "invalid", 300
    ]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert any(
        issue["rule"] == "data_type_violation"
        for issue in result["issues"]
    )


def test_infinite_numeric_value(
    contract, valid_df
):

    valid_df.loc[0, "amount"] = np.inf

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["summary"]["affected_rows"] == 1


def test_fractional_integer(
    contract, valid_df
):

    valid_df["id"] = [1.5, 2.0, 3.0]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "failed"


def test_numeric_string(
    contract, valid_df
):

    valid_df["amount"] = [
        "100.5", "200", "300"
    ]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "passed"


def test_boolean_not_numeric(
    contract, valid_df
):

    valid_df["amount"] = [
        True, 200, 300
    ]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["status"] == "failed"


def test_duplicate_primary_key(
    contract, valid_df
):

    valid_df["id"] = [1, 1, 3]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["primary_key"]["status"] == "failed"

    assert result["summary"]["affected_rows"] == 2


def test_missing_primary_key(
    contract, valid_df
):

    valid_df.loc[0, "id"] = np.nan

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["primary_key"]["status"] == "failed"

    assert result["summary"]["affected_rows"] == 1


def test_empty_dataframe(
    contract, valid_df
):

    result = SchemaValidator(
        contract
    ).validate(valid_df.iloc[:0])

    assert result["status"] == "failed"


def test_invalid_input(contract):

    with pytest.raises(TypeError):

        SchemaValidator(contract).validate(
            [1, 2, 3]
        )


def test_dataframe_not_modified(
    contract, valid_df
):

    original = valid_df.copy(deep=True)

    SchemaValidator(contract).validate(
        valid_df
    )

    pd.testing.assert_frame_equal(
        original,
        valid_df
    )


def test_json_serialization(
    contract, valid_df
):

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    json.dumps(
        result,
        allow_nan=False
    )


def test_duplicate_column_names(
    contract, valid_df
):

    df = pd.concat(
        [valid_df, valid_df[["amount"]]],
        axis=1
    )

    result = SchemaValidator(
        contract
    ).validate(df)

    assert result["status"] == "failed"

    assert (
        "amount"
        in result["schema_drift"]["duplicate_columns"]
    )


def test_affected_rows_not_double_counted(
    contract, valid_df
):

    valid_df.loc[0, "amount"] = np.nan

    valid_df.loc[0, "id"] = np.nan

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["summary"]["affected_rows"] == 1


def test_duplicate_dataframe_index(
    contract, valid_df
):

    valid_df.index = [0, 0, 0]

    valid_df["amount"] = [
        100, "invalid", 300
    ]

    result = SchemaValidator(
        contract
    ).validate(valid_df)

    assert result["summary"]["affected_rows"] == 1


def test_valid_datetime():

    definition = ColumnContract(
        dtype="datetime"
    )

    series = pd.Series([
        "2026-01-01",
        "2026-02-01"
    ])

    mask = SchemaValidator.validate_type(
        series,
        definition
    )

    assert not mask.any()


def test_invalid_datetime():

    definition = ColumnContract(
        dtype="datetime"
    )

    series = pd.Series([
        "2026-01-01",
        "not-a-date"
    ])

    mask = SchemaValidator.validate_type(
        series,
        definition
    )

    assert int(mask.sum()) == 1


def test_numeric_not_datetime():

    definition = ColumnContract(
        dtype="datetime"
    )

    series = pd.Series([123456])

    mask = SchemaValidator.validate_type(
        series,
        definition
    )

    assert mask.all()


def test_composite_primary_key():

    contract = DatasetContract(
        name="Invoice lines",
        industry="retail",
        grain="Invoice and line number",

        primary_key=["invoice", "line"],

        columns={
            "invoice": ColumnContract(
                dtype="string",
                nullable=False
            ),

            "line": ColumnContract(
                dtype="integer",
                nullable=False
            )
        }
    )

    df = pd.DataFrame({
        "invoice": ["A", "A", "A"],
        "line": [1, 2, 2]
    })

    result = SchemaValidator(
        contract
    ).validate(df)

    assert result["primary_key"]["status"] == "failed"

    assert result["summary"]["affected_rows"] == 2


def test_optional_column():

    contract = DatasetContract(
        name="Optional fields",
        industry="test",
        grain="One observation",

        columns={
            "id": ColumnContract(
                dtype="integer"
            ),

            "description": ColumnContract(
                dtype="string",
                required=False
            )
        }
    )

    result = SchemaValidator(
        contract
    ).validate(
        pd.DataFrame({"id": [1, 2]})
    )

    assert result["status"] == "passed"

    assert (
        result["summary"]["missing_optional_columns"]
        == 1
    )
