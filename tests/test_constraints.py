
import json

import numpy as np
import pandas as pd
import pytest

from decisioniq.validation import (
    ColumnContract,
    DatasetContract,
    ConstraintValidator,
    load_industry_contract
)


def make_contract(**kwargs):

    return DatasetContract(
        name="Constraint test",
        industry="test",
        grain="One observation",
        columns={
            "value": ColumnContract(**kwargs)
        }
    )


def validate(values, **kwargs):

    contract = make_contract(**kwargs)

    df = pd.DataFrame({
        "value": values
    })

    return ConstraintValidator(
        contract
    ).validate(
        df,
        include_row_positions=True
    )


def test_valid_range():

    result = validate(
        [1, 5, 10],
        dtype="numeric",
        minimum=1,
        maximum=10
    )

    assert result["status"] == "passed"


def test_minimum_violation():

    result = validate(
        [-1, 0, 10],
        dtype="numeric",
        minimum=0
    )

    assert result["summary"]["affected_rows"] == 1


def test_maximum_violation():

    result = validate(
        [10, 20, 30],
        dtype="numeric",
        maximum=20
    )

    assert result["summary"]["affected_rows"] == 1


def test_inclusive_boundaries():

    result = validate(
        [0, 100],
        dtype="numeric",
        minimum=0,
        maximum=100
    )

    assert result["status"] == "passed"


def test_allowed_categories():

    result = validate(
        ["L", "M", "H"],
        dtype="string",
        allowed_values=["L", "M", "H"]
    )

    assert result["status"] == "passed"


def test_invalid_category():

    result = validate(
        ["L", "X", "H"],
        dtype="string",
        allowed_values=["L", "M", "H"]
    )

    assert result["summary"]["affected_rows"] == 1


def test_numeric_allowed_values():

    result = validate(
        [0, 1, 2],
        dtype="integer",
        allowed_values=[0, 1]
    )

    assert result["summary"]["affected_rows"] == 1


def test_numeric_strings():

    result = validate(
        ["0", "1"],
        dtype="integer",
        allowed_values=[0, 1]
    )

    assert result["status"] == "passed"


def test_valid_regex():

    result = validate(
        ["AB123", "CD456"],
        dtype="string",
        pattern=r"[A-Z]{2}\d{3}"
    )

    assert result["status"] == "passed"


def test_invalid_regex_value():

    result = validate(
        ["AB123", "wrong"],
        dtype="string",
        pattern=r"[A-Z]{2}\d{3}"
    )

    assert result["summary"]["affected_rows"] == 1


def test_regex_fullmatch():

    result = validate(
        ["AB123extra"],
        dtype="string",
        pattern=r"[A-Z]{2}\d{3}"
    )

    assert result["status"] == "failed"


def test_blank_strings():

    result = validate(
        ["A", "", "   "],
        dtype="string",
        allow_blank=False
    )

    assert result["summary"]["affected_rows"] == 2


def test_missing_not_blank():

    result = validate(
        ["A", None],
        dtype="string",
        allow_blank=False
    )

    assert result["status"] == "passed"


def test_duplicate_values():

    result = validate(
        [1, 1, 2, 3],
        dtype="integer",
        unique=True
    )

    assert result["summary"]["affected_rows"] == 2


def test_numeric_duplicate_normalization():

    result = validate(
        [1, "1", 2],
        dtype="integer",
        unique=True
    )

    assert result["summary"]["affected_rows"] == 2


def test_nullable_uniqueness():

    result = validate(
        [1, None, None, 2],
        dtype="numeric",
        unique=True
    )

    assert result["status"] == "passed"


def test_missing_values_excluded():

    result = validate(
        [1, None, 3],
        dtype="numeric",
        minimum=0
    )

    assert result["status"] == "passed"

    assert result["checks"][0]["evaluated_rows"] == 2


def test_invalid_type_excluded():

    result = validate(
        [1, "invalid", 3],
        dtype="numeric",
        minimum=0
    )

    assert result["checks"][0]["excluded_rows"] == 1

    assert result["summary"]["affected_rows"] == 0


def test_infinity_excluded():

    result = validate(
        [1, np.inf, 3],
        dtype="numeric",
        maximum=100
    )

    assert result["checks"][0]["excluded_rows"] == 1


def test_no_constraints():

    result = validate(
        [1, 2, 3],
        dtype="numeric"
    )

    assert result["status"] == "not_applicable"


def test_all_missing():

    result = validate(
        [None, None],
        dtype="numeric",
        minimum=0
    )

    assert result["status"] == "not_evaluable"


def test_missing_column():

    contract = make_contract(
        dtype="numeric",
        minimum=0
    )

    result = ConstraintValidator(
        contract
    ).validate(
        pd.DataFrame({"other": [1, 2]})
    )

    assert result["status"] == "not_evaluable"


def test_multiple_violations_same_row():

    result = validate(
        [-1, 1],
        dtype="integer",
        minimum=0,
        allowed_values=[0, 1]
    )

    assert result["summary"]["failed_checks"] == 2

    assert result["summary"]["affected_rows"] == 1


def test_row_positions():

    result = validate(
        [1, -1, 3, -2],
        dtype="numeric",
        minimum=0
    )

    assert result["affected_row_positions"] == [1, 3]


def test_positions_excluded_by_default():

    contract = make_contract(
        dtype="numeric",
        minimum=0
    )

    result = ConstraintValidator(
        contract
    ).validate(
        pd.DataFrame({"value": [-1, 2]})
    )

    assert "affected_row_positions" not in result


def test_duplicate_dataframe_index():

    contract = make_contract(
        dtype="numeric",
        minimum=0
    )

    df = pd.DataFrame(
        {"value": [1, -1, 2]},
        index=[0, 0, 0]
    )

    result = ConstraintValidator(
        contract
    ).validate(
        df,
        include_row_positions=True
    )

    assert result["affected_row_positions"] == [1]


def test_dataframe_not_modified():

    contract = make_contract(
        dtype="numeric",
        minimum=0
    )

    df = pd.DataFrame({
        "value": [1, -1, 2]
    })

    original = df.copy(deep=True)

    ConstraintValidator(contract).validate(df)

    pd.testing.assert_frame_equal(
        df,
        original
    )


def test_json_serialization():

    result = validate(
        [1, -1],
        dtype="numeric",
        minimum=0
    )

    json.dumps(
        result,
        allow_nan=False
    )


def test_retail_negative_quantity():

    contract = load_industry_contract("retail")

    df = pd.DataFrame({
        "Quantity": [-2, 1, 5]
    })

    result = ConstraintValidator(
        contract
    ).validate(df)

    assert not any(
        issue["column"] == "Quantity"
        for issue in result["issues"]
    )


def test_banking_negative_balance():

    contract = load_industry_contract("banking")

    df = pd.DataFrame({
        "balance": [-500, 0, 1000],
        "pdays": [-1, 0, 10]
    })

    result = ConstraintValidator(
        contract
    ).validate(df)

    assert result["summary"]["affected_rows"] == 0


def test_manufacturing_invalid_failure():

    contract = load_industry_contract(
        "manufacturing"
    )

    df = pd.DataFrame({
        "Machine failure": [0, 1, 2]
    })

    result = ConstraintValidator(
        contract
    ).validate(df)

    assert result["summary"]["affected_rows"] == 1


def test_invalid_input():

    contract = make_contract(
        dtype="numeric"
    )

    with pytest.raises(TypeError):

        ConstraintValidator(contract).validate(
            [1, 2, 3]
        )


def test_duplicate_column_names():

    contract = make_contract(
        dtype="numeric",
        minimum=0
    )

    df = pd.DataFrame(
        [[1, -1]],
        columns=["value", "value"]
    )

    result = ConstraintValidator(
        contract
    ).validate(df)

    assert result["status"] == "not_evaluable"
