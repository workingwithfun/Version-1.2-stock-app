from collections import defaultdict
from locale import normalize
import math
from numpy import mean, median
from rest_framework.response import Response
from rest_framework.request import Request  # if you need request type hinting

from balance.models import BalanceSheetEntry, BalanceSheetStats, CompanySymbol, ErrorLog, GrowthSummary, GrowthSummary_YOY_10, GrowthSummary_YOY_100, GrowthSummary_YOY_125, GrowthSummary_YOY_150, GrowthSummary_YOY_175, GrowthSummary_YOY_20, GrowthSummary_YOY_200, GrowthSummary_YOY_225, GrowthSummary_YOY_250, GrowthSummary_YOY_40, GrowthSummary_YOY_50, GrowthSummary_YOY_75, GrowthSummary_YOY_90, MCAPData, MetricSummary, StockAnalysis, StockAnalysis_YOY_10, StockAnalysis_YOY_100, StockAnalysis_YOY_125, StockAnalysis_YOY_150, StockAnalysis_YOY_175, StockAnalysis_YOY_20, StockAnalysis_YOY_200, StockAnalysis_YOY_225, StockAnalysis_YOY_250, StockAnalysis_YOY_40, StockAnalysis_YOY_50, StockAnalysis_YOY_75, StockAnalysis_YOY_90, Summary, Summary_YOY_10, Summary_YOY_100, Summary_YOY_125, Summary_YOY_150, Summary_YOY_175, Summary_YOY_20, Summary_YOY_200, Summary_YOY_225, Summary_YOY_250, Summary_YOY_40, Summary_YOY_50, Summary_YOY_75, Summary_YOY_90, ValueAnalysis10Y, ValueAnalysis10Y_YOY_10, ValueAnalysis10Y_YOY_100, ValueAnalysis10Y_YOY_125, ValueAnalysis10Y_YOY_150, ValueAnalysis10Y_YOY_175, ValueAnalysis10Y_YOY_20, ValueAnalysis10Y_YOY_200, ValueAnalysis10Y_YOY_225, ValueAnalysis10Y_YOY_250, ValueAnalysis10Y_YOY_40, ValueAnalysis10Y_YOY_50, ValueAnalysis10Y_YOY_75, ValueAnalysis10Y_YOY_90, ValueAnalysis5Y, ValueAnalysis5Y_YOY_10, ValueAnalysis5Y_YOY_100, ValueAnalysis5Y_YOY_125, ValueAnalysis5Y_YOY_150, ValueAnalysis5Y_YOY_175, ValueAnalysis5Y_YOY_20, ValueAnalysis5Y_YOY_200, ValueAnalysis5Y_YOY_225, ValueAnalysis5Y_YOY_250, ValueAnalysis5Y_YOY_40, ValueAnalysis5Y_YOY_50, ValueAnalysis5Y_YOY_75, ValueAnalysis5Y_YOY_90
from balance.serializers import CompanySymbolSerializer
import numpy as np

import re
from django.db.models import Prefetch
from balance.models import BalanceSheetYearValue

MAX_HISTORY_YEARS = 11


def build_year_map(entry):
    """Return {year: numeric_value} from related dynamic year records."""
    if not entry:
        return {}

    result = {}

    for item in entry.year_values.all():
        value = item.value

        if value in (None, "", "missing"):
            result[item.year] = None
            continue

        try:
            result[item.year] = float(
                str(value).strip().replace(",", "").rstrip("%")
            )
        except (TypeError, ValueError):
            result[item.year] = None

    return result


def get_metric_values(entry, years):
    """Return metric values in the requested year order."""
    year_map = build_year_map(entry)
    return [year_map.get(year) for year in years]
def normalize_percentage_metric(value, metric=None, year=None):
    """
    Preserve values already stored in percentage points.
    Example: 0.50 stays 0.50; -44.75 stays -44.75.
    """
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number

def normalize_key(value: str) -> str:
    if not value:
        return ""
    return re.sub(r'[^a-z0-9]', '', value.lower())

def filter_entries(entries, **kwargs):
    result = entries
    for key, value in kwargs.items():
        result = [e for e in result if getattr(e, key) == value]
    return result

# expected return 30
def log_calc_error(company_symbol, error_type, message=None):

    ErrorLog.objects.get_or_create(
        error_type=error_type,
        equity_symbol=company_symbol.symbol if company_symbol else None,
        defaults={
            "company_name": company_symbol.name if company_symbol else None,
            "source": "CALCULATION_ENGINE",
        }
    )

YOY_TABLE_MAP = {
    30: {
        "metric_summary": MetricSummary,
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y,
        "value_5y": ValueAnalysis5Y,
        "growth": GrowthSummary,
        "stock": StockAnalysis,
        "summary": Summary,
    },
    10: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_10,
        "value_5y": ValueAnalysis5Y_YOY_10,
        "growth": GrowthSummary_YOY_10,
        "stock": StockAnalysis_YOY_10,
        "summary": Summary_YOY_10,
    },

    20: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_20,
        "value_5y": ValueAnalysis5Y_YOY_20,
        "growth": GrowthSummary_YOY_20,
        "stock": StockAnalysis_YOY_20,
        "summary": Summary_YOY_20,
    },
    40: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_40,
        "value_5y": ValueAnalysis5Y_YOY_40,
        "growth": GrowthSummary_YOY_40,
        "stock": StockAnalysis_YOY_40,
        "summary": Summary_YOY_40,
    },
    50: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_50,
        "value_5y": ValueAnalysis5Y_YOY_50,
        "growth": GrowthSummary_YOY_50,
        "stock": StockAnalysis_YOY_50,
        "summary": Summary_YOY_50,
    },
    75: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_75,
        "value_5y": ValueAnalysis5Y_YOY_75,
        "growth": GrowthSummary_YOY_75,
        "stock": StockAnalysis_YOY_75,
        "summary": Summary_YOY_75,
    },
    
    90: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,

        "value_10y": ValueAnalysis10Y_YOY_90,
        "value_5y": ValueAnalysis5Y_YOY_90,
        "growth": GrowthSummary_YOY_90,
        "stock": StockAnalysis_YOY_90,
        "summary": Summary_YOY_90,
    },
    100: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_100,
        "value_5y": ValueAnalysis5Y_YOY_100,
        "growth": GrowthSummary_YOY_100,
        "stock": StockAnalysis_YOY_100,
        "summary": Summary_YOY_100,
    },
    125: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_125,
        "value_5y": ValueAnalysis5Y_YOY_125,
        "growth": GrowthSummary_YOY_125,
        "stock": StockAnalysis_YOY_125,
        "summary": Summary_YOY_125,
    },
    150: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_150,
        "value_5y": ValueAnalysis5Y_YOY_150,
        "growth": GrowthSummary_YOY_150,
        "stock": StockAnalysis_YOY_150,
        "summary": Summary_YOY_150,
    },
    175: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_175,
        "value_5y": ValueAnalysis5Y_YOY_175,
        "growth": GrowthSummary_YOY_175,
        "stock": StockAnalysis_YOY_175,
        "summary": Summary_YOY_175,
    },
    200: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_200,
        "value_5y": ValueAnalysis5Y_YOY_200,
        "growth": GrowthSummary_YOY_200,
        "stock": StockAnalysis_YOY_200,
        "summary": Summary_YOY_200,
    },
    225: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_225,
        "value_5y": ValueAnalysis5Y_YOY_225,
        "growth": GrowthSummary_YOY_225,
        "stock": StockAnalysis_YOY_225,
        "summary": Summary_YOY_225,
    },
    250: {
        "metric_summary": MetricSummary,          # shared
        "balance_stats": BalanceSheetStats,
        "value_10y": ValueAnalysis10Y_YOY_250,
        "value_5y": ValueAnalysis5Y_YOY_250,
        "growth": GrowthSummary_YOY_250,
        "stock": StockAnalysis_YOY_250,
        "summary": Summary_YOY_250,
    },
}

from django.db import transaction
from django.db.models import Prefetch
from balance.models import (
    BalanceSheetEntry,
    BalanceSheetYearValue,
    BalanceSheetStats,
    CompanySymbol,
    ErrorLog,
    GrowthSummary,
    MCAPData,
    MetricSummary,
    MetricSummaryYearValue,
    StockAnalysis,
    Summary,
    ValueAnalysis10Y,
    ValueAnalysis5Y,
)

import math
import numpy as np


@transaction.atomic
def calculate_metrics_engine(company_symbol, expected_return, models=None):

    print(
        "🚀 ENGINE START:",
        getattr(company_symbol, "symbol", None),
        expected_return,
        flush=True,
    )

    if not company_symbol:
        return {"error": "Invalid company symbol"}

    try:
        expected_return = int(float(expected_return))
    except (TypeError, ValueError):
        return {"error": "Invalid expected_return"}

    models = YOY_TABLE_MAP.get(expected_return)
    if models is None:
        raise ValueError(f"YOY_TABLE_MAP missing key {expected_return}")

    ValueAnalysis10Y = models["value_10y"]
    ValueAnalysis5Y = models["value_5y"]
    BalanceSheetStats = models["balance_stats"]
    GrowthSummary = models["growth"]
    StockAnalysis = models["stock"]
    Summary = models["summary"]

    company_id = company_symbol.id

    try:
        # -----------------------------------------------------
        # 1. Load source data
        # -----------------------------------------------------
        entries = list(
            BalanceSheetEntry.objects.filter(company_id=company_id)
            .prefetch_related(
                Prefetch(
                    "year_values",
                    queryset=BalanceSheetYearValue.objects.order_by("year"),
                )
            )
        )

        if not entries:
            raise ValueError(
                f"No balance sheet data for {company_symbol.name}"
            )

        available_years = sorted({
            yv.year
            for entry in entries
            for yv in entry.year_values.all()
            if yv.year is not None
        })

        YEARS = available_years[-MAX_HISTORY_YEARS:]
        if not YEARS:
            raise ValueError("No yearly balance-sheet values are available.")

        last_year = max(YEARS)
        years = [str(year) for year in YEARS] + ["Trailing"]
        company_data = CompanySymbolSerializer(company_symbol).data

        print("Available years:", available_years, flush=True)
        print("Years used:", YEARS, flush=True)

        # -----------------------------------------------------
        # 2. Helpers
        # -----------------------------------------------------
        def parse_value(value):
            if value is None:
                return None

            if isinstance(value, str):
                value = value.strip()
                if value.lower() in ("", "missing", "none", "null", "-"):
                    return None
                value = value.replace(",", "").rstrip("%").strip()

            try:
                number = float(value)
                return number if math.isfinite(number) else None
            except (TypeError, ValueError):
                return None

        def safe_mean(values):
            clean = [
                float(v) for v in values
                if v is not None and math.isfinite(float(v))
            ]
            return float(np.mean(clean)) if clean else None

        def safe_median(values):
            clean = [
                float(v) for v in values
                if v is not None and math.isfinite(float(v))
            ]
            return float(np.median(clean)) if clean else None

        def safe_trimmean(values, proportion=0.1):
            clean = sorted(
                float(v) for v in values
                if v is not None and math.isfinite(float(v))
            )
            if not clean:
                return None

            trim = int(len(clean) * proportion)
            trimmed = (
                clean[trim:len(clean) - trim]
                if len(clean) > 2 * trim
                else clean
            )
            return float(np.mean(trimmed)) if trimmed else None

        def calc_pct_change(values):
            result = []
            for i, value in enumerate(values):
                previous = values[i - 1] if i > 0 else None
                if value is None or previous in (None, 0):
                    result.append(None)
                else:
                    result.append((value - previous) / abs(previous))
            return result

        def calc_trailing_pct(last_value, trailing_value):
            if last_value in (None, 0) or trailing_value is None:
                return None
            return (trailing_value - last_value) / abs(last_value)

        def pct_to_str(value):
            return None if value is None else f"{round(value * 100, 2)}%"

        def to_percentage(value):
            return None if value is None else round(float(value) * 100, 2)

        def build_year_map(entry):
            result = {}
            if entry:
                for item in entry.year_values.all():
                    result[item.year] = parse_value(item.value)
            return result

        def get_entry(metric):
            return next(
                (entry for entry in entries if entry.type == metric),
                None,
            )

        def finite_values(values):
            result = []
        
            for value in values:
                parsed = parse_value(value)
                if parsed is not None:
                    result.append(parsed)
        
            return result
        
        
        def calculate_stats(values):
            clean = finite_values(values)
        
            if not clean:
                return {
                    "average": None,
                    "median": None,
                    "trimmean": None,
                }
        
            ordered = sorted(clean)
            trim_count = int(len(ordered) * 0.10)
        
            if trim_count > 0 and len(ordered) > 2 * trim_count:
                trimmed = ordered[trim_count:-trim_count]
            else:
                trimmed = ordered
        
            return {
                "average": float(np.mean(clean)),
                "median": float(np.median(clean)),
                "trimmean": float(np.mean(trimmed)),
            }
        # -----------------------------------------------------
        # 3. Upsert dynamic metric summaries
        # -----------------------------------------------------
        def save_metric_summary(metric, pct_values, trailing_pct):
            """
            Keep one summary per company/metric/summary type.
            Update its periods in place and remove obsolete periods.
            """

            summary_qs = MetricSummary.objects.filter(
                company_id=company_id,
                base_type=metric,
                summary_type="pct_change",
            ).order_by("id")

            summary_record = summary_qs.first()

            if summary_record:
                # Clean up duplicates created by previous runs.
                duplicate_ids = list(
                    summary_qs.exclude(pk=summary_record.pk)
                    .values_list("pk", flat=True)
                )

                if duplicate_ids:
                    MetricSummary.objects.filter(
                        pk__in=duplicate_ids
                    ).delete()

                summary_record.file_name = company_symbol.name
                summary_record.save(update_fields=["file_name"])
            else:
                summary_record = MetricSummary.objects.create(
                    company_id=company_id,
                    file_name=company_symbol.name,
                    base_type=metric,
                    summary_type="pct_change",
                )

            period_values = {
                str(year): pct_to_str(value)
                for year, value in zip(YEARS, pct_values)
            }
            period_values["Trailing"] = pct_to_str(trailing_pct)

            # Update existing period values.
            existing = {
                item.period: item
                for item in MetricSummaryYearValue.objects.filter(
                    summary=summary_record
                )
            }

            to_create = []
            to_update = []

            for period, value in period_values.items():
                item = existing.get(period)

                if item:
                    if item.value != value:
                        item.value = value
                        to_update.append(item)
                else:
                    to_create.append(
                        MetricSummaryYearValue(
                            summary=summary_record,
                            period=period,
                            value=value,
                        )
                    )

            if to_update:
                MetricSummaryYearValue.objects.bulk_update(
                    to_update, ["value"], batch_size=500
                )

            if to_create:
                MetricSummaryYearValue.objects.bulk_create(
                    to_create, batch_size=500
                )

            # Remove periods no longer present in the source data.
            MetricSummaryYearValue.objects.filter(
                summary=summary_record
            ).exclude(
                period__in=list(period_values.keys())
            ).delete()

            return summary_record

        # -----------------------------------------------------
        # 4. Replace previous calculation outputs
        # -----------------------------------------------------
        # These tables are recalculated as a complete set.
        ValueAnalysis10Y.objects.filter(company_id=company_id).delete()
        ValueAnalysis5Y.objects.filter(company_id=company_id).delete()
        BalanceSheetStats.objects.filter(company_id=company_id).delete()
        GrowthSummary.objects.filter(company_id=company_id).delete()
        StockAnalysis.objects.filter(company_id=company_id).delete()
        Summary.objects.filter(company_id=company_id).delete()

        METRICS = ["Sales", "OPM", "Net profit", "EPS", "ROE"]
        metric_entries = {
            metric: get_entry(metric) for metric in METRICS
        }

        rows = []
        balance_stat_bulk = []

        # -----------------------------------------------------
        # 5. Calculate metrics and percentages
        # -----------------------------------------------------
        
        def finite_values(items):
            """Return finite numeric observations, excluding missing values."""
            result = []

            for item in items:
                number = parse_value(item)
                if number is not None:
                    result.append(number)

            return result

        def select_statistics_window(annual_values, trailing, years_count):
            """
            Select annual observations plus TTM.

            10-year window: latest 9 annual observations + TTM.
            5-year window:  latest 4 annual observations + TTM.

            Select the latest annual observations chronologically,
            then exclude missing/non-finite observations.
            """
            annual_count = years_count - 1
            selected_annual = finite_values(annual_values[-annual_count:])
            selected_trailing = parse_value(trailing)

            if selected_trailing is not None:
                return selected_annual + [selected_trailing]

            return selected_annual

                # -----------------------------------------------------
        # 5. Calculate metrics and percentages
        # -----------------------------------------------------

        def finite_values(items):
            """Remove missing and non-finite values without changing valid values."""
            result = []

            for item in items:
                if item is None:
                    continue

                try:
                    number = float(item)
                except (TypeError, ValueError):
                    continue

                if math.isfinite(number):
                    result.append(number)

            return result

        for metric in METRICS:
            entry = metric_entries[metric]

            # Get annual values in chronological order and the TTM value.
            if entry:
                year_map = build_year_map(entry)
                all_values = [year_map.get(year) for year in YEARS]
                trailing_value = parse_value(entry.trailing)
            else:
                all_values = [None] * len(YEARS)
                trailing_value = None

            # Keep percentage metrics in percentage points.
            if metric in ("OPM", "ROE"):
                all_values = [
                    normalize_percentage_metric(value, metric=metric, year=year)
                    if value is not None else None
                    for year, value in zip(YEARS, all_values)
                ]

                if trailing_value is not None:
                    trailing_value = normalize_percentage_metric(
                        trailing_value,
                        metric=metric,
                        year="Trailing",
                    )

            # Preserve your existing ROE TTM rule.
            if metric == "ROE" and trailing_value is None:
                trailing_value = 0.0

            # -------------------------------------------------
            # ABSOLUTE STATISTICS
            #
            # 10Y = latest 10 annual values + TTM
            # 5Y  = latest 5 annual values + TTM
            #
            # This applies to ALL metrics, including ROE.
            # -------------------------------------------------

            annual_10y = all_values[-10:]
            annual_5y = all_values[-5:]

            stats_values_10y = finite_values(
                annual_10y + [trailing_value]
            )
            stats_values_5y = finite_values(
                annual_5y + [trailing_value]
            )

            stats_10y = calculate_stats(stats_values_10y)
            stats_5y = calculate_stats(stats_values_5y)

            # -------------------------------------------------
            # PERCENTAGE CHANGES
            # -------------------------------------------------

            # Calculate changes using the full annual history.
            all_pct_changes = calc_pct_change(all_values)

            # Find the latest available annual value.
            last_annual_value = next(
                (
                    float(value)
                    for value in reversed(all_values)
                    if value is not None
                    and math.isfinite(float(value))
                ),
                None,
            )

            # Compare TTM with the latest available annual value.
            trailing_pct = calc_trailing_pct(
                last_annual_value,
                trailing_value,
            )

            # Use the latest 10 or 5 annual-change positions,
            # then append the TTM percentage change.
            pct_stats_values_10y = finite_values(
                all_pct_changes[-10:] + [trailing_pct]
            )
            pct_stats_values_5y = finite_values(
                all_pct_changes[-5:] + [trailing_pct]
            )

            pct_stats_10y = calculate_stats(pct_stats_values_10y)
            pct_stats_5y = calculate_stats(pct_stats_values_5y)

            # Include TTM in the displayed values.
            values_with_trailing = all_values + [trailing_value]
            pct_values_with_trailing = all_pct_changes + [trailing_pct]

            # Debug output to verify exactly what is calculated.
            print(
                f"[{metric} STATISTICS]",
                {
                    "years": YEARS,
                    "annual_values": all_values,
                    "trailing_value": trailing_value,
                    "absolute_10y_inputs": stats_values_10y,
                    "absolute_10y_count": len(stats_values_10y),
                    "absolute_5y_inputs": stats_values_5y,
                    "absolute_5y_count": len(stats_values_5y),
                    "absolute_10y": stats_10y,
                    "absolute_5y": stats_5y,
                    "annual_pct_changes": all_pct_changes,
                    "trailing_pct": trailing_pct,
                    "pct_10y_inputs": pct_stats_values_10y,
                    "pct_5y_inputs": pct_stats_values_5y,
                    "pct_10y": pct_stats_10y,
                    "pct_5y": pct_stats_5y,
                },
                flush=True,
            )

            # -------------------------------------------------
            # BUILD RESPONSE ROW
            # -------------------------------------------------

            rows.append({
                "key": metric,
                "trailing": trailing_value,
                "values": all_values,
                "values_with_trailing": values_with_trailing,
                "pct_values": pct_values_with_trailing,
                "stats": {
                    "10y": stats_10y,
                    "5y": stats_5y,
                },
                "pct_stats": {
                    "10y": pct_stats_10y,
                    "5y": pct_stats_5y,
                },
            })

            # -------------------------------------------------
            # SAVE PERCENTAGE-CHANGE SUMMARY
            # -------------------------------------------------

            save_metric_summary(
                metric=metric,
                pct_values=all_pct_changes,
                trailing_pct=trailing_pct,
            )

            # -------------------------------------------------
            # PREPARE DATABASE STATISTICS
            # -------------------------------------------------

            balance_stat_bulk.extend([
                BalanceSheetStats(
                    company=company_symbol,
                    file_name=company_symbol.name,
                    base_type=metric,
                    summary_type="statistical",
                    ten_year_avg=stats_10y["average"],
                    ten_year_median=stats_10y["median"],
                    ten_year_trimmean=stats_10y["trimmean"],
                    five_year_avg=stats_5y["average"],
                    five_year_median=stats_5y["median"],
                    five_year_trimmean=stats_5y["trimmean"],
                ),
                BalanceSheetStats(
                    company=company_symbol,
                    file_name=company_symbol.name,
                    base_type=metric,
                    summary_type="pct",
                    ten_year_avg=to_percentage(
                        pct_stats_10y["average"]
                    ),
                    ten_year_median=to_percentage(
                        pct_stats_10y["median"]
                    ),
                    ten_year_trimmean=to_percentage(
                        pct_stats_10y["trimmean"]
                    ),
                    five_year_avg=to_percentage(
                        pct_stats_5y["average"]
                    ),
                    five_year_median=to_percentage(
                        pct_stats_5y["median"]
                    ),
                    five_year_trimmean=to_percentage(
                        pct_stats_5y["trimmean"]
                    ),
                ),
            ])

        # Save the recalculated statistics to the database.
        if balance_stat_bulk:
            BalanceSheetStats.objects.bulk_create(
                balance_stat_bulk,
                batch_size=500,
            )

        # -----------------------------------------------------
        # 6. Net Profit Margin (NPM)
        # -----------------------------------------------------
                # -----------------------------------------------------
        # 6. Net Profit Margin (NPM)
        # -----------------------------------------------------
        npm_row = None
        net_profit_entry = metric_entries.get("Net profit")
        sales_entry = metric_entries.get("Sales")

        if net_profit_entry and sales_entry:
            net_profit_map = build_year_map(net_profit_entry)
            sales_map = build_year_map(sales_entry)

            # Calculate annual NPM values.
            npm_values = []

            for year in YEARS:
                net_profit = net_profit_map.get(year)
                sales = sales_map.get(year)

                if net_profit is None or sales in (None, 0):
                    npm_values.append(None)
                else:
                    npm_values.append(
                        (net_profit / sales) * 100
                    )

            # Calculate trailing NPM.
            net_profit_trailing = parse_value(
                net_profit_entry.trailing
            )
            sales_trailing = parse_value(
                sales_entry.trailing
            )

            npm_trailing = (
                (net_profit_trailing / sales_trailing) * 100
                if net_profit_trailing is not None
                and sales_trailing not in (None, 0)
                else None
            )

            # Calculate annual NPM changes.
            npm_pct = calc_pct_change(npm_values)

            last_npm = next(
                (
                    value for value in reversed(npm_values)
                    if value is not None
                ),
                None,
            )

            npm_trailing_pct = calc_trailing_pct(
                last_npm,
                npm_trailing,
            )

            npm_pct_with_trailing = (
                npm_pct + [npm_trailing_pct]
            )

            # Absolute NPM statistics include annual values and TTM.
            npm_values_with_trailing = (
                npm_values + [npm_trailing]
            )

            npm_stats_values = [
                value for value in npm_values_with_trailing
                if value is not None
            ]

            npm_stats_values_5y = [
                value for value in npm_values_with_trailing[-6:]
                if value is not None
            ]

            npm_stats_10y = calculate_stats(npm_stats_values)
            npm_stats_5y = calculate_stats(npm_stats_values_5y)

            # NPM percentage-change statistics.
            
            # Keep the original period windows when calculating statistics.
            # Ignore missing percentage changes without shifting the window.
            npm_pct_stats_10y = calculate_stats(
                npm_pct_with_trailing
            )
            
            npm_pct_stats_5y = calculate_stats(
                npm_pct_with_trailing[-6:]
            )
            

            # NPM row.
            npm_row = {
                "key": "NPM",
                "trailing": npm_trailing,
                "values": npm_values,
                "values_with_trailing": npm_values_with_trailing,
                "pct_values": npm_pct_with_trailing,
                "stats": {
                    "10y": npm_stats_10y,
                    "5y": npm_stats_5y,
                },
                "pct_stats": {
                    "10y": npm_pct_stats_10y,
                    "5y": npm_pct_stats_5y,
                },
            }

            rows.append(npm_row)

            # NPM change row.
            # Calculate NPM change statistics using the actual available changes.
            npm_pct_clean = [
                float(value)
                for value in npm_pct_with_trailing
                if value is not None and math.isfinite(float(value))
            ]
            
            # Use the latest five annual changes for the 5-year statistics.
            # Exclude TTM here so it does not count as a sixth annual year.
            npm_pct_clean_5y = [
                float(value)
                for value in npm_pct[-5:]
                if value is not None and math.isfinite(float(value))
            ]
            
            npm_change_stats_10y = calculate_stats(npm_pct_clean)
            npm_change_stats_5y = calculate_stats(npm_pct_clean_5y)

            npm_change_row = {
                "key": "NPM change",
                "trailing": npm_trailing_pct,
                "values": npm_pct,
                "values_with_trailing": npm_pct_with_trailing,
                "pct_values": npm_pct_with_trailing,
                "stats": {
                    "10y": npm_change_stats_10y,
                    "5y": npm_change_stats_5y,
                },
                "pct_stats": {
                    "10y": npm_change_stats_10y,
                    "5y": npm_change_stats_5y,
                },
            }

            rows.append(npm_change_row)

            # Maintain the required display order.
            row_order = [
                "Sales",
                "OPM",
                "Net profit",
                "NPM",
                "NPM change",
                "EPS",
                "ROE",
            ]

            row_order_map = {
                key: index for index, key in enumerate(row_order)
            }

            rows.sort(
                key=lambda row: row_order_map.get(
                    row["key"],
                    len(row_order_map),
                )
            )

            # Persist annual and trailing NPM percentage changes.
            save_metric_summary(
                metric="NPM",
                pct_values=npm_pct,
                trailing_pct=npm_trailing_pct,
            )

            # Save NPM statistics.
            BalanceSheetStats.objects.bulk_create(
                [
                    BalanceSheetStats(
                        company=company_symbol,
                        file_name=company_symbol.name,
                        base_type="NPM",
                        summary_type="statistical",
                        ten_year_avg=npm_stats_10y["average"],
                        ten_year_median=npm_stats_10y["median"],
                        ten_year_trimmean=npm_stats_10y["trimmean"],
                        five_year_avg=npm_stats_5y["average"],
                        five_year_median=npm_stats_5y["median"],
                        five_year_trimmean=npm_stats_5y["trimmean"],
                    ),
                    BalanceSheetStats(
                        company=company_symbol,
                        file_name=company_symbol.name,
                        base_type="NPM",
                        summary_type="pct",
                        ten_year_avg=to_percentage(
                            npm_pct_stats_10y["average"]
                        ),
                        ten_year_median=to_percentage(
                            npm_pct_stats_10y["median"]
                        ),
                        ten_year_trimmean=to_percentage(
                            npm_pct_stats_10y["trimmean"]
                        ),
                        five_year_avg=to_percentage(
                            npm_pct_stats_5y["average"]
                        ),
                        five_year_median=to_percentage(
                            npm_pct_stats_5y["median"]
                        ),
                        five_year_trimmean=to_percentage(
                            npm_pct_stats_5y["trimmean"]
                        ),
                    ),
                ],
                batch_size=500,
            )
        # -----------------------------------------------------
        # 7. EPS projections
        # -----------------------------------------------------
        eps_row = next(
            (row for row in rows if row["key"] == "EPS"), None
        )

        mcap_data = MCAPData.objects.filter(
            company=company_symbol
        ).first()

        industry_pe = (
            parse_value(mcap_data.industry_pe)
            if mcap_data and mcap_data.industry_pe
            else None
        )
        share_price = (
            parse_value(mcap_data.share_price)
            if mcap_data and mcap_data.share_price
            else None
        )

        def create_projection(growth_rate, tenure):
            trailing_eps = (
                parse_value(eps_row["trailing"]) if eps_row else None
            )
            if trailing_eps is None:
                trailing_eps = 0.0

            growth_rate = growth_rate or 0.0
            projection = []
            eps = trailing_eps

            for i in range(1, 7):
                target_eps = eps * (1 + growth_rate)
                projection.append({
                    "year": f"Mar-{str(last_year + i)[-2:]}",
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None,
                })
                eps = target_eps

            if (
                projection
                and industry_pe is not None
                and share_price is not None
            ):
                projection[-1]["target_price"] = (
                    projection[-1]["target_eps"] * industry_pe
                )
                discount_factor = 1 + expected_return / 100

                for i in reversed(range(len(projection) - 1)):
                    projection[i]["target_price"] = (
                        projection[i + 1]["target_price"] / discount_factor
                        if discount_factor != 0 else None
                    )

                for item in projection:
                    target_price = item["target_price"]
                    if target_price is not None and share_price not in (None, 0):
                        item["YOY_return"] = (
                            (target_price - share_price) / share_price
                        ) * 100

            return projection

        def growth_rate_for(row, period, method):
            if not row:
                return 0.0
            value = row["pct_stats"][period].get(method)
            return value if value is not None else 0.0

        value_analysis_trimmean = (
            create_projection(growth_rate_for(eps_row, "10y", "trimmean"), "10y")
            if eps_row else []
        )
        value_analysis_median = (
            create_projection(growth_rate_for(eps_row, "10y", "median"), "10y")
            if eps_row else []
        )
        value_analysis_average = (
            create_projection(growth_rate_for(eps_row, "10y", "average"), "10y")
            if eps_row else []
        )
        value_analysis_trimmean_5y = (
            create_projection(growth_rate_for(eps_row, "5y", "trimmean"), "5y")
            if eps_row else []
        )
        value_analysis_median_5y = (
            create_projection(growth_rate_for(eps_row, "5y", "median"), "5y")
            if eps_row else []
        )
        value_analysis_average_5y = (
            create_projection(growth_rate_for(eps_row, "5y", "average"), "5y")
            if eps_row else []
        )

        # -----------------------------------------------------
        # 8. Save valuation projections
        # -----------------------------------------------------
        projection_sets_10y = [
            (value_analysis_trimmean, "trimmean_10y"),
            (value_analysis_median, "median_10y"),
            (value_analysis_average, "average_10y"),
        ]
        projection_sets_5y = [
            (value_analysis_trimmean_5y, "trimmean_5y"),
            (value_analysis_median_5y, "median_5y"),
            (value_analysis_average_5y, "average_5y"),
        ]

        value_analysis_10y_bulk = [
            ValueAnalysis10Y(
                company_id=company_id,
                stats_type=stats_type,
                year=item["year"],
                holding_period=item["holding_period"],
                eps=item["eps"],
                target_eps=item["target_eps"],
                target_price=item["target_price"],
                yoy_return=item["YOY_return"],
            )
            for projection, stats_type in projection_sets_10y
            for item in projection
        ]

        value_analysis_5y_bulk = [
            ValueAnalysis5Y(
                company_id=company_id,
                stats_type=stats_type,
                year=item["year"],
                holding_period=item["holding_period"],
                eps=item["eps"],
                target_eps=item["target_eps"],
                target_price=item["target_price"],
                yoy_return=item["YOY_return"],
            )
            for projection, stats_type in projection_sets_5y
            for item in projection
        ]

        if value_analysis_10y_bulk:
            ValueAnalysis10Y.objects.bulk_create(
                value_analysis_10y_bulk, batch_size=500
            )
        if value_analysis_5y_bulk:
            ValueAnalysis5Y.objects.bulk_create(
                value_analysis_5y_bulk, batch_size=500
            )

        # -----------------------------------------------------
        # 9. Growth summary
        # -----------------------------------------------------
        growth_summary = []
        growth_bulk = []

        for metric_row in rows:
            pct_stats = metric_row["pct_stats"]
            row_values = [
                pct_stats["5y"]["trimmean"],
                pct_stats["5y"]["median"],
                pct_stats["5y"]["average"],
                pct_stats["10y"]["trimmean"],
                pct_stats["10y"]["median"],
                pct_stats["10y"]["average"],
            ]
            clean = [v for v in row_values if v is not None]

            total_average = {
                "trimmean": safe_trimmean(clean),
                "median": safe_median(clean),
                "average": safe_mean(clean),
            }

            growth_summary.append({
                "parameter": metric_row["key"],
                "5y": pct_stats["5y"],
                "10y": pct_stats["10y"],
                "total_average": total_average,
            })

        for item in growth_summary:
            for calc_type in ("trimmean", "median", "average"):
                growth_bulk.append(
                    GrowthSummary(
                        company_id=company_id,
                        metric=item["parameter"],
                        calc_type=calc_type,
                        five_year=to_percentage(item["5y"].get(calc_type)),
                        ten_year=to_percentage(item["10y"].get(calc_type)),
                        total_average=to_percentage(
                            item["total_average"].get(calc_type)
                        ),
                    )
                )

        if growth_bulk:
            GrowthSummary.objects.bulk_create(growth_bulk, batch_size=500)

        # -----------------------------------------------------
        # 10. Recommendations and entry prices
        # -----------------------------------------------------
        def get_recommendation(price, target_price):
            if price is None or target_price is None:
                return "Data not available"
            if price < target_price:
                return "Recommended to buy at current stock price"
            return "Recommended to wait until target price entry is achieved"

        final_analysis_table = []
        market_price = share_price

        tenure_method_map = {
            "10 Year Analysis": {
                "Trim Mean": value_analysis_trimmean,
                "Median": value_analysis_median,
                "Average": value_analysis_average,
            },
            "5 Year Analysis": {
                "Trim Mean": value_analysis_trimmean_5y,
                "Median": value_analysis_median_5y,
                "Average": value_analysis_average_5y,
            },
        }

        for tenure, methods in tenure_method_map.items():
            tenure_target_prices = []
            tenure_rows = []

            for method_name, projection in methods.items():
                target_price_entry = None

                if projection:
                    first_target_price = projection[0].get("target_price")
                    if first_target_price is not None:
                        discount_factor = 1 + expected_return / 100
                        if discount_factor != 0:
                            target_price_entry = (
                                first_target_price / discount_factor
                            )

                tenure_rows.append({
                    "Analysis Tenure": tenure,
                    "Method": method_name,
                    "Recommendation": get_recommendation(
                        market_price, target_price_entry
                    ),
                    "Target Price for Entry": target_price_entry,
                })
                tenure_target_prices.append(target_price_entry)

            valid_prices = [
                float(price) for price in tenure_target_prices
                if price is not None and math.isfinite(float(price))
            ]
            average_tenure_value = (
                float(np.median(valid_prices)) if valid_prices else None
            )

            for item in tenure_rows:
                item["Average Tenure-wise"] = average_tenure_value
                final_analysis_table.append(item)

        target_prices = [
            float(item["Target Price for Entry"])
            for item in final_analysis_table
            if item.get("Target Price for Entry") is not None
            and math.isfinite(float(item["Target Price for Entry"]))
        ]
        average_tenure_values = [
            float(item["Average Tenure-wise"])
            for item in final_analysis_table
            if item.get("Average Tenure-wise") is not None
            and math.isfinite(float(item["Average Tenure-wise"]))
        ]

        median_target_price_entry = (
            float(np.median(target_prices)) if target_prices else None
        )
        mean_average_tenure = (
            float(np.mean(average_tenure_values))
            if average_tenure_values else None
        )

        if median_target_price_entry is None or share_price is None:
            conclusion_recommendation = "Data not available"
        elif share_price < median_target_price_entry:
            conclusion_recommendation = "Recommended to buy at current stock price"
        else:
            conclusion_recommendation = "Recommended to wait until target price entry is achieved"

        final_analysis_table.append({
            "Analysis Tenure": "Value Analysis Conclusion",
            "Method": None,
            "Recommendation": conclusion_recommendation,
            "Target Price for Entry": median_target_price_entry,
            "Average Tenure-wise": mean_average_tenure,
        })

        target_avg_value = (
            (median_target_price_entry + mean_average_tenure) / 2
            if median_target_price_entry is not None
            and mean_average_tenure is not None
            else None
        )

        if target_avg_value not in (None, 0):
            for projection, stats_type in projection_sets_10y:
                for item in projection:
                    if item.get("target_price") is not None:
                        forecasted_return = (
                            (item["target_price"] - target_avg_value)
                            / target_avg_value
                        ) * 100
                        ValueAnalysis10Y.objects.filter(
                            company_id=company_id,
                            stats_type=stats_type,
                            year=item["year"],
                        ).update(forecasted_return=forecasted_return)

            for projection, stats_type in projection_sets_5y:
                for item in projection:
                    if item.get("target_price") is not None:
                        forecasted_return = (
                            (item["target_price"] - target_avg_value)
                            / target_avg_value
                        ) * 100
                        ValueAnalysis5Y.objects.filter(
                            company_id=company_id,
                            stats_type=stats_type,
                            year=item["year"],
                        ).update(forecasted_return=forecasted_return)

        final_analysis_table.append({
            "Analysis Tenure": "Target",
            "Method": None,
            "Recommendation": target_avg_value,
            "Target Price for Entry": None,
            "Average Tenure-wise": None,
        })

        tenure_map = {
            "5 Year Analysis": "5Y",
            "10 Year Analysis": "10Y",
            "Value Analysis Conclusion": "CONCLUSION",
            "Target": "TARGET",
        }
        method_map = {
            "Trim Mean": "trimmean",
            "Median": "median",
            "Average": "average",
        }

        stock_bulk = [
            StockAnalysis(
                company_id=company_id,
                analysis_tenure=tenure_map.get(item.get("Analysis Tenure")),
                method=method_map.get(item.get("Method"))
                if item.get("Method") else None,
                recommendation=item.get("Recommendation"),
                target_price_entry=item.get("Target Price for Entry"),
                average_tenure=item.get("Average Tenure-wise"),
            )
            for item in final_analysis_table
        ]
        if stock_bulk:
            StockAnalysis.objects.bulk_create(stock_bulk, batch_size=500)

        # -----------------------------------------------------
        # 11. Final summary conditions
        # -----------------------------------------------------
        def pos_neg(condition):
            return "Positive" if condition else "Negative"

        valuation_status = "Data not available"
        if (
            share_price is not None
            and median_target_price_entry is not None
            and mcap_data
            and mcap_data.stock_pe is not None
            and mcap_data.industry_pe is not None
        ):
            valuation_status = (
                "Undervalued"
                if share_price < median_target_price_entry
                and mcap_data.stock_pe < mcap_data.industry_pe
                else "Overvalued"
            )

        value_analysis_conclusion_status = pos_neg(
            conclusion_recommendation
            == "Recommended to buy at current stock price"
        )

        target_price_entry_status = "Data not available"
        if share_price is not None and median_target_price_entry is not None:
            target_price_entry_status = pos_neg(
                share_price < median_target_price_entry
            )

        pe_comparison_status = "Data not available"
        if (
            mcap_data
            and mcap_data.stock_pe is not None
            and mcap_data.industry_pe is not None
        ):
            pe_comparison_status = pos_neg(
                mcap_data.stock_pe < mcap_data.industry_pe
            )

        growth_thresholds = {
            "Sales": 15,
            "EPS": 15,
            "ROE": 15,
            "OPM": 5,
            "NPM": 5,
        }
        growth_conditions = {}

        for item in growth_summary:
            metric = item["parameter"]
            if metric not in growth_thresholds:
                continue

            threshold = growth_thresholds[metric]
            total_average = item["total_average"]

            def build_growth_obj(value):
                return {
                    "status": pos_neg(
                        value is not None and value * 100 > threshold
                    ),
                    "value": round(value * 100, 2)
                    if value is not None else None,
                }

            growth_conditions[metric] = {
                "trimmean": build_growth_obj(total_average.get("trimmean")),
                "median": build_growth_obj(total_average.get("median")),
                "average": build_growth_obj(total_average.get("average")),
            }

        summary_conditions = {
            "valuation": valuation_status,
            "value_analysis_conclusion": value_analysis_conclusion_status,
            "target_price_for_entry": {
                "status": target_price_entry_status,
                "value": median_target_price_entry,
            },
            "stock_pe_vs_industry_pe": pe_comparison_status,
            "growth_analysis": {
                "sales_growth": growth_conditions.get("Sales"),
                "opm_growth": growth_conditions.get("OPM"),
                "npm_growth": growth_conditions.get("NPM"),
                "eps_growth": growth_conditions.get("EPS"),
                "roe_growth": growth_conditions.get("ROE"),
            },
        }

        parameter_map = {
            "Sales": "SALES",
            "OPM": "OPM",
            "NPM": "NPM",
            "EPS": "EPS",
            "ROE": "ROE",
        }

        summary_bulk = [
            Summary(
                company_id=company_id,
                parameter="VALUATION",
                result=valuation_status,
            ),
            Summary(
                company_id=company_id,
                parameter="VALUATION_CONCLUSION",
                result=value_analysis_conclusion_status,
            ),
            Summary(
                company_id=company_id,
                parameter="TARGET_ENTRY",
                result=target_price_entry_status,
            ),
            Summary(
                company_id=company_id,
                parameter="PE_COMPARISON",
                result=pe_comparison_status,
            ),
        ]

        for metric, values in growth_conditions.items():
            summary_bulk.append(
                Summary(
                    company_id=company_id,
                    parameter=parameter_map[metric],
                    trimmean=values["trimmean"]["status"],
                    median=values["median"]["status"],
                    average=values["average"]["status"],
                )
            )

        if summary_bulk:
            Summary.objects.bulk_create(summary_bulk, batch_size=500)

        # -----------------------------------------------------
        # 12. Success log and response
        # -----------------------------------------------------
        ErrorLog.objects.create(
            error_type="CALCULATION_SUCCESS",
            equity_symbol=company_symbol.symbol,
            company_name=company_symbol.name,
            source=f"YOY_{expected_return}",
        )

        return {
            "company_info": company_data,
            "years": years,
            "rows": rows,
            "summary_conditions": summary_conditions,
            "value_analysis_trimmean": value_analysis_trimmean,
            "value_analysis_median": value_analysis_median,
            "value_analysis_average": value_analysis_average,
            "value_analysis_trimmean_5y": value_analysis_trimmean_5y,
            "value_analysis_median_5y": value_analysis_median_5y,
            "value_analysis_average_5y": value_analysis_average_5y,
            "growth_summary": growth_summary,
            "final_analysis_table": final_analysis_table,
        }

    except Exception as exc:
        # Roll back all database changes from this failed calculation.
        transaction.set_rollback(True)

        print(
            "🔥 Calculation crashed:",
            repr(exc),
            flush=True,
        )

        # Safely inspect rows even if the error occurred before rows
        # was initialized.
        current_rows = locals().get("rows", [])

        print(
            "FINAL ENGINE ROW KEYS:",
            [row.get("key") for row in current_rows],
            flush=True,
        )

        print(
            "NPM ROW:",
            next(
                (
                    row for row in current_rows
                    if row.get("key") == "NPM"
                ),
                None,
            ),
            flush=True,
        )

        import traceback
        traceback.print_exc()

        return {
            "error": "Calculation failed",
            "details": str(exc),
        }

