
from decisioniq.validation import (
    load_industry_contract
)


def main():

    industries = [
        "manufacturing",
        "retail",
        "banking"
    ]

    print("=" * 65)
    print("DECISIONIQ DATA CONTRACT INTELLIGENCE")
    print("=" * 65)

    for industry in industries:

        contract = load_industry_contract(
            industry
        )

        required = sum(
            column.required
            for column in contract.columns.values()
        )

        non_nullable = sum(
            not column.nullable
            for column in contract.columns.values()
        )

        constrained = sum(
            column.minimum is not None
            or column.maximum is not None
            or column.allowed_values is not None
            or column.pattern is not None
            for column in contract.columns.values()
        )

        print(f"\nIndustry: {industry.upper()}")
        print("-" * 50)

        print("Dataset:", contract.name)

        print("Version:", contract.version)

        print("Grain:", contract.grain)

        print(
            "Defined columns:",
            len(contract.columns)
        )

        print(
            "Required columns:",
            required
        )

        print(
            "Non-nullable columns:",
            non_nullable
        )

        print(
            "Constrained columns:",
            constrained
        )

        print(
            "Primary key:",
            contract.primary_key
            or "Not defined"
        )

        print("Contract status: VALID")

    print("\nAll industry contracts loaded.")


if __name__ == "__main__":
    main()
