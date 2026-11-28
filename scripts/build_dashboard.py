
import json
import re

from pathlib import Path

from decisioniq.utils.config import PROJECT_ROOT


DASHBOARD = PROJECT_ROOT / "dashboard"
ASSETS = DASHBOARD / "assets"
REPORTS = PROJECT_ROOT / "reports"


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def sanitize(value):

    private_keys = {
        "archived_path",
        "absolute_path",
        "local_path",
        "error_message"
    }

    if isinstance(value, dict):

        return {
            key: sanitize(item)
            for key, item in value.items()
            if key not in private_keys
        }

    if isinstance(value, list):

        return [
            sanitize(item)
            for item in value
        ]

    return value


def safe_script(source):

    return re.sub(
        r"</script",
        lambda _: r"<\/script",
        source,
        flags=re.IGNORECASE
    )


def load_reports():

    reports = {}

    for industry in [
        "manufacturing",
        "retail",
        "banking"
    ]:

        path = (
            REPORTS
            / "profiling"
            / f"{industry}_unified.json"
        )

        if not path.exists():

            print(f"Missing report: {industry}")
            continue

        report = sanitize(read_json(path))

        source = report.get("source", {})

        report["source"] = {
            key: source[key]
            for key in [
                "file_name",
                "file_hash"
            ]
            if key in source
        }

        reports[industry] = report

        print(
            f"Loaded {industry}: "
            f"{report['dataset']['row_count']:,} records"
        )

    if not reports:

        raise RuntimeError(
            "No unified profiling reports found."
        )

    return reports


def main():

    reports = load_reports()

    benchmark_path = (
        REPORTS
        / "benchmarks"
        / "cross_industry_profiling.json"
    )

    benchmark = (
        sanitize(read_json(benchmark_path))
        if benchmark_path.exists()
        else None
    )

    payload = json.dumps(
        {
            "reports": reports,
            "benchmark": benchmark
        },
        ensure_ascii=True,
        allow_nan=False
    )

    payload = (
        payload
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    template = (
        DASHBOARD
        / "templates"
        / "profiling.html"
    ).read_text(encoding="utf-8")

    replacements = {
        "__DECISIONIQ_DATA__": payload,

        "__STUDIO_CSS__": (
            ASSETS / "studio.css"
        ).read_text(encoding="utf-8"),

        "__ECHARTS_JS__": safe_script(
            (ASSETS / "echarts.min.js")
            .read_text(encoding="utf-8")
        ),

        "__LUCIDE_JS__": safe_script(
            (ASSETS / "lucide.min.js")
            .read_text(encoding="utf-8")
        ),

        "__STUDIO_JS__": safe_script(
            (ASSETS / "studio.js")
            .read_text(encoding="utf-8")
        )
    }

    for placeholder, content in replacements.items():

        if template.count(placeholder) != 1:

            raise ValueError(
                f"Invalid placeholder: {placeholder}"
            )

        template = template.replace(
            placeholder,
            content,
            1
        )

    output = DASHBOARD / "index.html"

    temporary = output.with_suffix(".tmp")

    temporary.write_text(
        template,
        encoding="utf-8"
    )

    temporary.replace(output)

    print("\n" + "=" * 55)
    print("DECISIONIQ INTELLIGENCE STUDIO")
    print("=" * 55)

    print(f"Industries loaded: {len(reports)}")

    print(
        f"Dashboard size: "
        f"{output.stat().st_size / 1024 ** 2:.2f} MiB"
    )

    print("Offline assets: Embedded")
    print("Dashboard generated successfully.")
    print(f"Location: {output}")


if __name__ == "__main__":
    main()
