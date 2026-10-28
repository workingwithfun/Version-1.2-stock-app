from balance.models import (
    BalanceSheetEntry,
    BalanceSheetYearValue,
    CompanySymbol,
)
import datetime
import logging
import re
from .import_utils import resolve_company_from_filename
import pandas as pd
from django.db import transaction

logger = logging.getLogger(__name__)

MAX_HISTORY_YEARS = 11
DB_BATCH_SIZE = 1000
HEADER_ROW_INDEX = 2  # Excel row 3

TARGET_KEYWORDS = {
    "sales": "Sales",
    "netprofit": "Net profit",
    "eps": "EPS",
    "opm": "OPM",
    "returnonequity": "ROE",
    "returnoncapitalemp": "ROCE",
    "returnoncapitalemployed": "ROCE",
}
PERCENTAGE_FIELDS = {
    "OPM",
    "Return on Equity",
    "Return on Capital Emp",
    "Return on Capital Employed",
}
# ==========================================================
# 1. GENERAL HELPERS
# ==========================================================

def normalize_text(value):
    """Normalize text for reliable comparisons."""
    if value is None or pd.isna(value):
        return ""

    return re.sub(r"[^a-z]", "", str(value).strip().lower())


def clean_excel_value(value):
    """Convert blank Excel cells into None."""
    if value is None or pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in {"", "nan", "none", "nat"}:
        return None

    return value


def detect_year_columns_from_headers(headers):
    """
    Return {year: column_index}.

    Examples:
        2015       -> 2015
        2025       -> 2025
        Mar-25     -> 2025
        March 2025 -> 2025
        Mar-15     -> 2015
    """
    year_columns = {}

    for index, header in enumerate(headers):
        if header is None or pd.isna(header):
            continue

        text = str(header).strip()
        if not text:
            continue

        # Match four-digit years first.
        match = re.search(
            r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)",
            text,
        )

        if match:
            year_columns[int(match.group(1))] = index
            continue

        # Match month-year headings, including Mar-25 and March 25.
        match = re.search(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
            r"[a-z]*[\s./_-]*(\d{2})\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            short_year = int(match.group(1))
            year = (
                2000 + short_year
                if short_year <= 69
                else 1900 + short_year
            )
            year_columns[year] = index
            continue

        # Accept a standalone two-digit year, such as 15 or 25.
        if re.fullmatch(r"\d{2}", text):
            short_year = int(text)
            year = (
                2000 + short_year
                if short_year <= 69
                else 1900 + short_year
            )
            year_columns[year] = index

    return year_columns


def detect_trailing_column_from_headers(headers):
    """Find the Trailing or TTM column."""
    for index, header in enumerate(headers):
        normalized = normalize_text(header)

        if normalized in {"trailing", "ttm"}:
            return index

    return None





def match_metric(narration):
    normalized = normalize_text(narration)

    # Match complete normalized labels, not arbitrary substrings.
    metric_type = TARGET_KEYWORDS.get(normalized)

    if metric_type:
        return metric_type, normalized

    return None, None

# ==========================================================
# 2. MAIN EXCEL PARSER
# ==========================================================

@transaction.atomic
def parse_balance_file(file_obj, fname, audit_date):
    print(
        f"\n========== PARSER STARTED: {fname} ==========",
        flush=True,
    )

    # ------------------------------------------------------
    # STEP 1: Resolve company
    # ------------------------------------------------------
    company = resolve_company_from_filename(fname)

    if not company:
        logger.error("No company mapping found for %s", fname)
        return 0

    print(
        f"[1] Company: {company}; audit date: {audit_date}",
        flush=True,
    )

    # ------------------------------------------------------
    # STEP 2: Configure metrics by worksheet
    # ------------------------------------------------------
    allowed_metrics_by_sheet = {
        "profitloss": {"Sales", "Net profit", "EPS", "OPM"},
        "balancesheet": {"ROE", "ROCE"},
    }

    percentage_metrics = {"OPM", "ROE", "ROCE"}

    existing_entries = {
        entry.type: entry
        for entry in BalanceSheetEntry.objects.filter(
            company=company,
            audit_date=audit_date,
        )
    }

    entries_to_create = {}
    entries_to_update = {}
    pending_year_rows = []
    latest_year = None

    # ------------------------------------------------------
    # STEP 3: Formatting helpers
    # ------------------------------------------------------
    def format_value(raw_value, metric_type):
        """
        Store OPM and ROE as percentage points.
        Example: 0.0516 -> 5.16
                 5.16   -> 5.16
                 5.16%  -> 5.16
        """
        value = clean_excel_value(raw_value)
    
        if value is None:
            return None
    
        value = value.strip()
    
        if metric_type in {"OPM", "ROE"}:
            has_percent_sign = value.endswith("%")
    
            try:
                number = float(value.replace(",", "").replace("%", "").strip())
            except (ValueError, TypeError):
                return value
    
            # Excel values already written as percentages should not be scaled.
            # Decimal ratios without a % sign need conversion.
            if not has_percent_sign and -1 < number < 1 and number != 0:
                number *= 100
    
            return str(number)
    
        # Preserve the original behavior for all other metrics.
        return value
    # ------------------------------------------------------
    # STEP 4: Read the correct worksheets and match rows
    # ------------------------------------------------------
    print("[2] Opening Excel workbook...", flush=True)

    with pd.ExcelFile(file_obj) as workbook:
        print("[3] Worksheets:", workbook.sheet_names, flush=True)

        for sheet_name in workbook.sheet_names:
            normalized_sheet = normalize_text(sheet_name)
            allowed_metrics = allowed_metrics_by_sheet.get(
                normalized_sheet
            )

            # Ignore worksheets unrelated to the six target metrics.
            if allowed_metrics is None:
                continue

            print(
                f"[4] Reading worksheet: {sheet_name}",
                flush=True,
            )

            df_full = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                header=None,
                dtype=str,
            )

            if len(df_full) <= HEADER_ROW_INDEX:
                continue

            headers = [
                str(value).strip() if pd.notna(value) else ""
                for value in df_full.iloc[HEADER_ROW_INDEX].tolist()
            ]

            narration_positions = [
                index
                for index, header in enumerate(headers)
                if normalize_text(header) == "narration"
            ]

            if not narration_positions:
                print(
                    f"[SKIP] Narration not found in {sheet_name}",
                    flush=True,
                )
                continue

            narration_idx = narration_positions[0]
            year_columns = detect_year_columns_from_headers(headers)
            trailing_idx = detect_trailing_column_from_headers(headers)

            if not year_columns:
                print(
                    f"[SKIP] No annual columns in {sheet_name}",
                    flush=True,
                )
                continue

            sheet_latest_year = max(year_columns)
            latest_year = (
                sheet_latest_year
                if latest_year is None
                else max(latest_year, sheet_latest_year)
            )

            data_df = df_full.iloc[
                HEADER_ROW_INDEX + 1:
            ].reset_index(drop=True)

            matched_in_sheet = set()

            for row_number, row in enumerate(
                data_df.itertuples(index=False, name=None),
                start=HEADER_ROW_INDEX + 2,
            ):
                if narration_idx >= len(row):
                    continue

                narration = clean_excel_value(row[narration_idx])

                if narration is None:
                    continue

                metric_type, matched_keyword = match_metric(narration)

                if metric_type not in allowed_metrics:
                    continue

                # A metric must be imported only once per worksheet.
                # This prevents duplicate narration rows from silently
                # overwriting previously collected annual values.
                if metric_type in matched_in_sheet:
                    print(
                        f"[WARNING] Duplicate metric {metric_type} "
                        f"in {sheet_name}, Excel row {row_number}; "
                        "skipping duplicate row.",
                        flush=True,
                    )
                    continue

                matched_in_sheet.add(metric_type)

                trailing_value = None

                if trailing_idx is not None and trailing_idx < len(row):
                    trailing_value = format_value(
                        row[trailing_idx],
                        metric_type,
                    )

                entry = existing_entries.get(metric_type)

                if entry is None:
                    entry = BalanceSheetEntry(
                        company=company,
                        type=metric_type,
                        audit_date=audit_date,
                        file_name=fname,
                        trailing=trailing_value,
                    )

                    entries_to_create[metric_type] = entry
                    existing_entries[metric_type] = entry

                else:
                    changed = False

                    if entry.file_name != fname:
                        entry.file_name = fname
                        changed = True

                    if (
                        trailing_value is not None
                        and entry.trailing != trailing_value
                    ):
                        entry.trailing = trailing_value
                        changed = True

                    if changed and entry.pk:
                        entries_to_update[entry.pk] = entry

                pending_year_rows.append(
                    (
                        metric_type,
                        matched_keyword,
                        row,
                        year_columns.copy(),
                    )
                )

                print(
                    f"[MATCH] {sheet_name} | {narration} "
                    f"-> {metric_type} | Excel row {row_number}",
                    flush=True,
                )

            print(
                f"[5] Metrics matched in {sheet_name}: "
                f"{sorted(matched_in_sheet)}",
                flush=True,
            )

    if latest_year is None:
        logger.error("No annual columns detected for %s", fname)
        return 0

    # ------------------------------------------------------
    # STEP 5: Save metric entries
    # ------------------------------------------------------
    if entries_to_create:
        BalanceSheetEntry.objects.bulk_create(
            list(entries_to_create.values()),
            batch_size=DB_BATCH_SIZE,
        )

    if entries_to_update:
        BalanceSheetEntry.objects.bulk_update(
            list(entries_to_update.values()),
            ["file_name", "trailing"],
            batch_size=DB_BATCH_SIZE,
        )

    entries_by_type = {
        entry.type: entry
        for entry in BalanceSheetEntry.objects.filter(
            company=company,
            audit_date=audit_date,
            type__in=list(existing_entries.keys()),
        )
    }

    print(
        f"[6] Entries available in database: "
        f"{len(entries_by_type)}",
        flush=True,
    )

    # ------------------------------------------------------
    # STEP 6: Collect annual values
    # ------------------------------------------------------
    values_by_type_year = {}

    for metric_type, matched_keyword, row, year_columns in pending_year_rows:
        for year, column_idx in year_columns.items():
            if column_idx >= len(row):
                continue

            value = format_value(row[column_idx], metric_type)
            if metric_type in {"OPM", "ROE", "ROCE"}:
                print(
                    f"[PERCENTAGE IMPORT DEBUG] "
                    f"Company={company} | "
                    f"Metric={metric_type} | "
                    f"Year={year} | "
                    f"Raw Excel cell={row[column_idx]!r} | "
                    f"Saved value={value!r}",
                    flush=True,
                )
            if value is None:
                continue

            key = (metric_type, year)

            # Duplicate keys should never silently overwrite data.
            if key in values_by_type_year:
                print(
                    f"[WARNING] Duplicate annual value for "
                    f"{metric_type} {year}; keeping first value.",
                    flush=True,
                )
                continue

            values_by_type_year[key] = value

    print(
        f"[7] Annual values collected: {len(values_by_type_year)}",
        flush=True,
    )

    # ------------------------------------------------------
    # STEP 7: Load existing annual records
    # ------------------------------------------------------
    entry_ids = [
        entry.pk
        for entry in entries_by_type.values()
        if entry.pk is not None
    ]

    existing_year_values = {
        (item.entry_id, item.year): item
        for item in BalanceSheetYearValue.objects.filter(
            entry_id__in=entry_ids,
        )
    }

    year_values_to_create = {}
    year_values_to_update = {}

    # ------------------------------------------------------
    # STEP 8: Prepare annual database changes
    # ------------------------------------------------------
    for (metric_type, year), value in values_by_type_year.items():
        entry = entries_by_type.get(metric_type)

        if entry is None:
            continue

        key = (entry.pk, year)
        existing_value = existing_year_values.get(key)

        if existing_value is not None:
            if existing_value.value != value:
                existing_value.value = value
                year_values_to_update[key] = existing_value
        else:
            year_values_to_create[key] = BalanceSheetYearValue(
                entry=entry,
                year=year,
                value=value,
            )

    # ------------------------------------------------------
    # STEP 9: Write annual values
    # ------------------------------------------------------
    if year_values_to_create:
        BalanceSheetYearValue.objects.bulk_create(
            list(year_values_to_create.values()),
            batch_size=DB_BATCH_SIZE,
        )

    if year_values_to_update:
        BalanceSheetYearValue.objects.bulk_update(
            list(year_values_to_update.values()),
            ["value"],
            batch_size=DB_BATCH_SIZE,
        )

    print(
        f"[8] Annual values created: {len(year_values_to_create)}",
        flush=True,
    )
    print(
        f"[9] Annual values updated: {len(year_values_to_update)}",
        flush=True,
    )

    # ------------------------------------------------------
    # STEP 10: Retain latest 11 years
    # ------------------------------------------------------
    cutoff_year = latest_year - MAX_HISTORY_YEARS + 1

    if entry_ids:
        deleted_count, _ = BalanceSheetYearValue.objects.filter(
            entry_id__in=entry_ids,
            year__lt=cutoff_year,
        ).delete()
    else:
        deleted_count = 0

    print(
        f"[10] Retained years from {cutoff_year}; "
        f"old records deleted: {deleted_count}",
        flush=True,
    )
    
    # ------------------------------------------------------
    # STEP 10B: Refresh MCAP EPS after importing a yearly sheet
    # ------------------------------------------------------
    from balance.models import MCAPData

    mcap = MCAPData.objects.filter(company=company).first()

    if mcap is not None:
        # Find the latest available annual EPS across the company's
        # saved EPS entries, prioritizing the newest financial year.
        eps_year_values = (
            BalanceSheetYearValue.objects
            .filter(
                entry__company=company,
                entry__type="EPS",
            )
            .select_related("entry")
            .order_by(
                "-year",
                "-entry__audit_date",
                "-entry__created_at",
            )
        )

        latest_annual_eps = None

        for year_value in eps_year_values:
            latest_annual_eps = year_value.entry._clean_numeric(
                year_value.value
            )
            if latest_annual_eps is not None:
                print(
                    f"[MCAP EPS] {company.symbol}: "
                    f"Annual EPS={latest_annual_eps}, "
                    f"Year={year_value.year}",
                    flush=True,
                )
                break

        # Find the latest non-empty trailing EPS from the saved
        # EPS entries, prioritizing the newest audit date.
        eps_entries = (
            BalanceSheetEntry.objects
            .filter(company=company, type="EPS")
            .order_by("-audit_date", "-created_at")
        )

        latest_trailing_eps = None

        for eps_entry in eps_entries:
            latest_trailing_eps = eps_entry._clean_numeric(
                eps_entry.trailing
            )
            if latest_trailing_eps is not None:
                print(
                    f"[MCAP EPS] {company.symbol}: "
                    f"Trailing EPS={latest_trailing_eps}",
                    flush=True,
                )
                break

        changed_fields = []

        # Do not erase existing values if the imported data
        # does not contain a valid replacement.
        if latest_annual_eps is not None:
            if mcap.eps_y24 != latest_annual_eps:
                mcap.eps_y24 = latest_annual_eps
                changed_fields.append("eps_y24")

        if latest_trailing_eps is not None:
            if mcap.eps_trailing != latest_trailing_eps:
                mcap.eps_trailing = latest_trailing_eps
                changed_fields.append("eps_trailing")

        # Recalculate P/E ratios using the refreshed EPS values.
        try:
            share_price = float(mcap.share_price)
        except (TypeError, ValueError):
            share_price = None

        if share_price is not None and math.isfinite(share_price):
            new_stock_pe = (
                round(share_price / mcap.eps_y24, 2)
                if mcap.eps_y24 is not None
                and math.isfinite(mcap.eps_y24)
                and mcap.eps_y24 != 0
                else None
            )

            new_ttm_pe = (
                round(share_price / mcap.eps_trailing, 2)
                if mcap.eps_trailing is not None
                and math.isfinite(mcap.eps_trailing)
                and mcap.eps_trailing != 0
                else None
            )

            if mcap.stock_pe != new_stock_pe:
                mcap.stock_pe = new_stock_pe
                changed_fields.append("stock_pe")

            if mcap.ttm_pe != new_ttm_pe:
                mcap.ttm_pe = new_ttm_pe
                changed_fields.append("ttm_pe")

        if changed_fields:
            mcap.save(update_fields=changed_fields)

        print(
            f"[MCAP EPS] {company.symbol}: "
            f"Updated fields={changed_fields or 'no changes'}",
            flush=True,
        )

    # ------------------------------------------------------
    # STEP 11: Final result
    # ------------------------------------------------------
    result_count = (
        len(entries_to_create)
        + len(entries_to_update)
        + len(year_values_to_create)
        + len(year_values_to_update)
    )

    logger.info(
        "Import completed: file=%s, company=%s, "
        "entries_created=%s, entries_updated=%s, "
        "annual_created=%s, annual_updated=%s, latest_year=%s",
        fname,
        company,
        len(entries_to_create),
        len(entries_to_update),
        len(year_values_to_create),
        len(year_values_to_update),
        latest_year,
    )

    print(
        f"========== IMPORT FINISHED: {fname} ==========",
        flush=True,
    )

    return result_count