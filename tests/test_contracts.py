
import pytest

from pydantic import ValidationError

from decisioniq.validation import (
    ColumnContract,
    DatasetContract,
    load_contract,
    load_industry_contract
)


def test_manufacturing_contract():

    contract = load_industry_contract(
        "manufacturing"
    )

    assert len(contract.columns) == 14

    assert contract.primary_key == ["UDI"]


def test_retail_contract():

    contract = load_industry_contract(
        "retail"
    )

    assert len(contract.columns) == 8

    assert contract.primary_key == []


def test_banking_contract():

    contract = load_industry_contract(
        "banking"
    )

    assert len(contract.columns) == 17


def test_invalid_numeric_range():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="numeric",
            minimum=100,
            maximum=10
        )


def test_unknown_data_type():

    with pytest.raises(ValidationError):

        ColumnContract(dtype="invalid")


def test_unknown_severity():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="numeric",
            severity="urgent"
        )


def test_missing_contract(tmp_path):

    with pytest.raises(FileNotFoundError):

        load_contract(
            tmp_path / "missing.yaml"
        )


def test_invalid_primary_key():

    with pytest.raises(ValidationError):

        DatasetContract(
            name="Test",
            industry="test",
            grain="One observation",
            primary_key=["id"],
            columns={
                "sales": ColumnContract(
                    dtype="numeric"
                )
            }
        )


def test_nullable_primary_key():

    with pytest.raises(ValidationError):

        DatasetContract(
            name="Test",
            industry="test",
            grain="One observation",
            primary_key=["id"],
            columns={
                "id": ColumnContract(
                    dtype="integer",
                    nullable=True
                )
            }
        )


def test_invalid_row_limits():

    with pytest.raises(ValidationError):

        DatasetContract(
            name="Test",
            industry="test",
            grain="One observation",
            minimum_rows=100,
            maximum_rows=10,
            columns={
                "id": ColumnContract(
                    dtype="integer"
                )
            }
        )


def test_retail_returns_permitted():

    contract = load_industry_contract(
        "retail"
    )

    assert (
        contract.columns["Quantity"].minimum
        is None
    )


def test_retail_missing_customer_allowed():

    contract = load_industry_contract(
        "retail"
    )

    assert contract.columns[
        "Customer ID"
    ].nullable is True


def test_banking_negative_balance_allowed():

    contract = load_industry_contract(
        "banking"
    )

    assert (
        contract.columns["balance"].minimum
        is None
    )


def test_banking_pdays_sentinel():

    contract = load_industry_contract(
        "banking"
    )

    assert contract.columns[
        "pdays"
    ].minimum == -1


def test_invalid_allowed_values():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="string",
            allowed_values=[]
        )


def test_unknown_contract_field():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="numeric",
            unexpected_field=True
        )


def test_invalid_regex():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="string",
            pattern="["
        )


def test_invalid_industry_path():

    with pytest.raises(ValueError):

        load_industry_contract(
            "../private"
        )


def test_contract_serialization():

    contract = load_industry_contract(
        "manufacturing"
    )

    output = contract.model_dump_json()

    assert "manufacturing" in output


def test_numeric_constraint_on_string():

    with pytest.raises(ValidationError):

        ColumnContract(
            dtype="string",
            minimum=0
        )
