
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def save_correlation_heatmap(
    df,
    output_path,
    method="pearson",
    excluded_columns=None,
    max_columns=20
):

    excluded_columns = set(
        excluded_columns or []
    )

    numeric = df.select_dtypes(
        include=["integer", "floating"]
    )

    columns = [

        column

        for column in numeric.columns

        if str(column) not in excluded_columns

        and numeric[column].nunique(dropna=True) > 2

    ][:max_columns]

    if len(columns) < 2:

        raise ValueError(
            "At least two eligible numeric columns required."
        )

    correlation = numeric[columns].replace(
        [np.inf, -np.inf],
        np.nan
    ).corr(method=method, min_periods=10)

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    size = max(8, len(columns) * 0.7)

    fig, ax = plt.subplots(
        figsize=(size, size)
    )

    try:

        sns.heatmap(

            correlation,

            mask=correlation.isna(),

            annot=len(columns) <= 15,

            fmt=".2f",

            cmap="vlag",

            center=0,

            vmin=-1,
            vmax=1,

            square=True,

            linewidths=0.5,

            ax=ax

        )

        ax.set_title(
            f"DecisionIQ | {method.title()} Correlation",
            fontsize=15,
            pad=20
        )

        fig.tight_layout()

        fig.savefig(
            output_path,
            dpi=200,
            bbox_inches="tight"
        )

    finally:

        plt.close(fig)

    return output_path

