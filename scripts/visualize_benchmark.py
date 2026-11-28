
import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from decisioniq.utils.config import PROJECT_ROOT


def main():

    report_path = (
        PROJECT_ROOT
        / "reports/benchmarks"
        / "cross_industry_profiling.json"
    )

    report = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    datasets = [

        d for d in report["datasets"]

        if d["status"] == "PASSED"
    ]

    if not datasets:

        raise RuntimeError(
            "No successful benchmarks available."
        )

    names = [
        d["industry"].title()
        for d in datasets
    ]

    colors = [
        "#2563eb",
        "#0d9488",
        "#9333ea"
    ][:len(datasets)]

    plt.style.use("dark_background")

    fig, axes = plt.subplots(
        2, 2,
        figsize=(15, 10)
    )

    fig.patch.set_facecolor("#091322")

    for ax in axes.flat:

        ax.set_facecolor("#142438")

        ax.grid(
            axis="y",
            alpha=0.12
        )

        ax.set_axisbelow(True)

        for spine in ax.spines.values():

            spine.set_visible(False)

    fig.suptitle(
        "DecisionIQ | Cross-Industry Benchmark",
        fontsize=23,
        fontweight="bold"
    )

    # Dataset volume

    bars = axes[0, 0].bar(
        names,
        [d["rows"] for d in datasets],
        color=colors
    )

    axes[0, 0].set_title(
        "Dataset Volume"
    )

    axes[0, 0].set_ylabel("Records")

    axes[0, 0].bar_label(
        bars,
        fmt="%.0f",
        padding=4
    )

    # Execution time

    x = np.arange(len(names))

    axes[0, 1].bar(
        x - 0.18,
        [d["ingestion_seconds"] for d in datasets],
        width=0.36,
        label="Ingestion",
        color="#38bdf8"
    )

    axes[0, 1].bar(
        x + 0.18,
        [d["profiling_seconds"] for d in datasets],
        width=0.36,
        label="Profiling",
        color="#2dd4bf"
    )

    axes[0, 1].set_xticks(x, names)

    axes[0, 1].set_title(
        "Execution Performance"
    )

    axes[0, 1].set_ylabel("Seconds")

    axes[0, 1].legend()

    # Process memory

    bars = axes[1, 0].bar(
        names,
        [
            d["process_memory"][
                "peak_sampled_rss_mb"
            ]
            for d in datasets
        ],
        color=colors
    )

    axes[1, 0].set_title(
        "Peak Sampled Process Memory"
    )

    axes[1, 0].set_ylabel("RSS (MiB)")

    axes[1, 0].bar_label(
        bars,
        fmt="%.1f",
        padding=4
    )

    # Data completeness

    bars = axes[1, 1].bar(
        names,
        [
            d["quality_indicators"][
                "completeness_percentage"
            ]
            for d in datasets
        ],
        color=colors
    )

    axes[1, 1].set_title(
        "Data Completeness"
    )

    axes[1, 1].set_ylabel("Percentage")

    axes[1, 1].set_ylim(0, 110)

    axes[1, 1].bar_label(
        bars,
        fmt="%.2f%%",
        padding=4
    )

    fig.text(
        0.5, 0.02,
        (
            "Single-run benchmark | "
            "Sequential execution | "
            "Successful datasets only | "
            "Retail: first worksheet"
        ),
        ha="center",
        color="#94a3b8",
        fontsize=10
    )

    plt.tight_layout(
        rect=[0, 0.05, 1, 0.93]
    )

    output_path = (
        PROJECT_ROOT
        / "reports/benchmarks"
        / "benchmark_dashboard.png"
    )

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    plt.close(fig)

    print(f"Dashboard saved: {output_path}")


if __name__ == "__main__":
    main()
