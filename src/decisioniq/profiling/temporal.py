
import pandas as pd


class TemporalProfiler:
    """Analyze temporal coverage without modifying data."""

    def __init__(self, config=None):

        self.config = config or {}

        self.date_columns = self.config.get(
            "date_columns", []
        )

        self.dayfirst = self.config.get(
            "dayfirst", False
        )

        self.max_missing_days = self.config.get(
            "max_missing_days_reported", 100
        )

    def detect_date_columns(self, df):

        detected = []

        for column in df.columns:

            if (
                pd.api.types.is_datetime64_any_dtype(
                    df[column]
                )
                or str(column) in self.date_columns
            ):

                detected.append(column)

        return detected

    def profile_column(self, series):

        dates = pd.to_datetime(
            series,
            errors="coerce",
            dayfirst=self.dayfirst,
            utc=True
        )

        valid = dates.dropna()

        result = {
            "column_name": str(series.name),
            "total_records": len(series),
            "valid_dates": len(valid),
            "missing_dates": int(series.isna().sum()),
            "invalid_dates": int(
                (series.notna() & dates.isna()).sum()
            )
        }

        if valid.empty:

            result["status"] = "no_valid_dates"

            return result

        unique_dates = (
            valid.drop_duplicates()
            .sort_values()
            .reset_index(drop=True)
        )

        first = unique_dates.iloc[0]
        last = unique_dates.iloc[-1]

        observed_days = pd.DatetimeIndex(
            valid.dt.normalize().unique()
        ).sort_values()

        expected_days = (
            last.normalize() - first.normalize()
        ).days + 1

        missing_days = (
            expected_days - len(observed_days)
        )

        missing_examples = []

        # Avoid constructing a potentially huge date range.
        for previous, current in zip(
            observed_days[:-1],
            observed_days[1:]
        ):

            gap = (current - previous).days - 1

            remaining = (
                self.max_missing_days
                - len(missing_examples)
            )

            if remaining <= 0:
                break

            for offset in range(
                1, min(gap, remaining) + 1
            ):

                missing_examples.append(
                    (
                        previous
                        + pd.Timedelta(days=offset)
                    ).strftime("%Y-%m-%d")
                )

        intervals = (
            unique_dates.diff()
            .dropna()
            .dt.total_seconds()
        )

        frequency = None

        if len(unique_dates) >= 3:

            try:
                pd.get_option(
                    "future.infer_freq_returns_offset"
                )
            except pd.errors.OptionError:
                inferred = pd.infer_freq(
                    pd.DatetimeIndex(unique_dates)
                )
            else:
                with pd.option_context(
                    "future.infer_freq_returns_offset", True
                ):
                    inferred = pd.infer_freq(
                        pd.DatetimeIndex(unique_dates)
                    )

            frequency = getattr(
                inferred, "freqstr", inferred
            )

        daily_counts = (
            valid.dt.strftime("%Y-%m-%d")
            .value_counts()
            .sort_index()
        )

        monthly_counts = (
            valid.dt.strftime("%Y-%m")
            .value_counts()
            .sort_index()
        )

        result.update({

            "status": "profiled",

            "coverage": {
                "first_timestamp": first.isoformat(),
                "last_timestamp": last.isoformat(),
                "calendar_days": expected_days,
                "observed_days": len(observed_days),
                "unobserved_days": missing_days,
                "day_coverage_pct": round(
                    len(observed_days)
                    / expected_days * 100, 4
                ),
                "unobserved_date_examples": missing_examples,
                "examples_truncated": (
                    missing_days > len(missing_examples)
                )
            },

            "frequency": {
                "inferred_frequency": frequency,
                "unique_timestamps": len(unique_dates),
                "repeated_timestamp_records": (
                    len(valid) - len(unique_dates)
                ),
                "median_interval_seconds": (
                    float(intervals.median())
                    if not intervals.empty else None
                ),
                "maximum_interval_seconds": (
                    float(intervals.max())
                    if not intervals.empty else None
                ),
                "regular_intervals": (
                    bool(intervals.nunique() == 1)
                    if len(intervals) >= 2 else None
                )
            },

            "volume": {
                "average_records_per_observed_day": round(
                    len(valid) / len(observed_days), 4
                ),
                "maximum_daily_records": int(
                    daily_counts.max()
                ),
                "minimum_observed_daily_records": int(
                    daily_counts.min()
                ),
                "monthly_records": {
                    str(month): int(count)
                    for month, count
                    in monthly_counts.items()
                }
            },

            "interpretation_warning": (
                "Unobserved days do not necessarily "
                "indicate missing data. Repeated "
                "timestamps may be valid business events."
            )
        })

        return result

    def profile(self, df):

        if df.empty:
            raise ValueError(
                "Cannot profile an empty dataset."
            )

        if not df.columns.is_unique:
            raise ValueError(
                "Duplicate column names detected."
            )

        date_columns = self.detect_date_columns(df)

        return {
            "date_columns_detected": len(date_columns),

            "date_columns": list(
                map(str, date_columns)
            ),

            "unmapped_date_columns": sorted(
                set(self.date_columns)
                - set(map(str, df.columns))
            ),

            "columns": [
                self.profile_column(df[column])
                for column in date_columns
            ]
        }
