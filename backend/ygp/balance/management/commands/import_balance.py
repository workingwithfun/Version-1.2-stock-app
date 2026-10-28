# balance/management/commands/import_balance.py
import os
import datetime
import re
from django.core.management.base import BaseCommand
import pandas as pd
from balance.models import BalanceSheetEntry

# Narration rows we want
PERCENTAGE_FIELDS = [ 
    "Return on Equity",
    "Return on Capital Emp",
    "OPM",
]
TARGET_KEYWORDS = {
    "Sales": "Sales",
    "OPM": "OPM",
    "Net profit": "Net profit",
    "EPS": "EPS",
    "Return on Equity": "ROC",
    "Return on Capital Emp": "ROCE",
    "Return on Capital Employed": "ROCE",  # sometimes appears like this
}


def normalize_column_name(col):
    # Case 1: datetime -> convert to year
    if isinstance(col, pd.Timestamp) or hasattr(col, "year"):
        return str(col.year)[-2:]  # e.g. 2015 -> '15'

    # Case 2: string that looks like year
    if isinstance(col, str):
        # Try to extract 4-digit year
        match = re.search(r"(20\d{2}|19\d{2})", col)
        if match:
            return match.group(1)[-2:]  # keep last 2 digits
        return col.strip()

    return None


import re
import datetime
import pandas as pd


def detect_year_columns(df):
    """
    Detect annual columns with headings such as:
    2025
    25
    2025-03-31
    2025-03-31 00:00:00

    Returns:
        {year: original_column_name}
    """
    detected = {}

    for col in df.columns:
        year = None

        # Handle Python and pandas date objects.
        if isinstance(col, (datetime.datetime, datetime.date, pd.Timestamp)):
            year = col.year

        else:
            text = str(col).strip()

            # Handle a plain four-digit year.
            if re.fullmatch(r"(19|20)\d{2}", text):
                year = int(text)

            # Handle two-digit year headings, e.g. 15, 24, 25.
            elif re.fullmatch(r"\d{2}", text):
                short_year = int(text)

                if 15 <= short_year <= 99:
                    year = 2000 + short_year

            else:
                # Handle date-formatted headings such as
                # "2025-03-31 00:00:00".
                match = re.search(r"\b(19\d{2}|20\d{2})\b", text)

                if match:
                    year = int(match.group(1))

        if year is not None and 1900 <= year <= 2100:
            # Preserve the original DataFrame column name.
            detected[year] = col

    return detected
    
class Command(BaseCommand):
     print("========== command STARTED ==========", flush=True)
    help = "Import rows from Excel files into BalanceSheetEntry"

    def add_arguments(self, parser):
        parser.add_argument("folder", type=str, help="Folder with company Excel files")

    def handle(self, *args, **options):
        folder = options["folder"]
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder}"))
            return

        files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith((".xlsx", ".xls"))]
        )
        if not files:
            self.stdout.write(self.style.ERROR("No Excel files found"))
            return

        created_objs = []
        total_inserted = 0
        BATCH = 500

        for fname in files:
            path = os.path.join(folder, fname)
            mtime = os.path.getmtime(path)  # float seconds since epoch
            audit_date = datetime.date.fromtimestamp(mtime)  # convert to date
            try:
                # IMPORTANT: use header=2 because real header starts at row 3 (A3)
                  all_sheets = pd.read_excel(path, dtype=str, keep_default_na=False, sheet_name=None, header=2)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not open {fname}: {e}"))
                continue

            
            for sheet_name, df in all_sheets.items():
              if sheet_name.strip() == "Quarters":
                 self.stdout.write(self.style.NOTICE(f"Skipping sheet '{sheet_name}' in {fname}"))
                 continue
              print(f"Processing sheet: {sheet_name}")
              print("RAW COLUMNS:", list(df.columns))
              
  
              if "Narration" not in df.columns:
                  self.stdout.write(
                      self.style.WARNING(f"'Narration' column not found in {fname}, skipping")
                  )
                  continue
  
              year_cols = detect_year_columns(df)
              print("DETECTED YEAR COLS:", year_cols)
  
              trailing_col = None
              for c in df.columns:
                  if "trailing" in str(c).lower() or "ttm" in str(c).lower():
                      trailing_col = c
                      break
  
              for _, row in df.iterrows():
                  narration = str(row.get("Narration", "")).strip()
                  if not narration:
                      continue
  
                  for key, mapped_type in TARGET_KEYWORDS.items():
                      if narration.lower() == key.lower():
                          kwargs = {
                              "file_name": fname,
                              "type": mapped_type,
                              "audit_date": audit_date,
                          }
  
                          # year values
                          for yy in range(15, 25):   # 2015 → 15, up to 2024 → 24
                              colname = year_cols.get(yy)
                              if colname and colname in df.columns:
                                  val = str(row.get(colname, "")).strip()
  
                                  if not val or val.lower() == "nan":
                                      val = "missing"
                                  else:
                                      # ✅ Convert to percentage if needed
                                      if key in PERCENTAGE_FIELDS:
                                          try:
                                              num = float(val)
                                              # If it's already like "21" leave it, if "0.21" multiply by 100
                                              if num <= 1:  
                                                  num *= 100
                                              val = f"{num:.2f}%"
                                          except ValueError:
                                              pass
                              else:
                                  val = "missing"
  
                              kwargs[f"y{yy}"] = val
  
                          # trailing
                          if trailing_col:
                              tval = str(row.get(trailing_col, "")).strip()
                              if not tval or tval.lower() == "nan":
                                  tval = "missing"
                              else:
                                  if key in PERCENTAGE_FIELDS:
                                      try:
                                          num = float(tval)
                                          if num <= 1:
                                              num *= 100
                                          tval = f"{num:.2f}%"
                                      except ValueError:
                                          pass
                              kwargs["trailing"] = tval
                          else:
                              kwargs["trailing"] = "missing"
  
                          created_objs.append(BalanceSheetEntry(**kwargs))
                          break  # stop checking other keywords
  
              if len(created_objs) >= BATCH:
                  BalanceSheetEntry.objects.bulk_create(created_objs)
                  total_inserted += len(created_objs)
                  self.stdout.write(
                      self.style.SUCCESS(f"Inserted {total_inserted} records so far...")
                  )
                  created_objs = []
  
        if created_objs:
            BalanceSheetEntry.objects.bulk_create(created_objs)
            total_inserted += len(created_objs)

        self.stdout.write(
            self.style.SUCCESS(f"Import finished. Total records inserted: {total_inserted}")
        )
