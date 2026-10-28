import os
import datetime
from django.core.management.base import BaseCommand
import pandas as pd
from balance.models import QuarterlyBalanceSheetEntry

TARGET_KEYWORDS = {
    "Sales": "Sales",
    "OPM": "OPM",
    "Net profit": "Net profit",
}

# mapping Excel column titles → model fields
QUARTER_MAP = {
    "Jun-22": "jun_22",
    "Sep-22": "sep_22",
    "Dec-22": "dec_22",
    "Mar-23": "mar_23",
    "Jun-23": "jun_23",
    "Sep-23": "sep_23",
    "Dec-23": "dec_23",
    "Mar-24": "mar_24",
    "Jun-24": "jun_24",
    "Sep-24": "sep_24",
}


class Command(BaseCommand):
    help = "Import quarterly rows from Excel files into QuarterlyBalanceSheetEntry"

    def add_arguments(self, parser):
        parser.add_argument("folder", type=str, help="Folder with Excel files")

    def handle(self, *args, **options):
        folder = options["folder"]
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder}"))
            return

        files = sorted([f for f in os.listdir(folder) if f.lower().endswith((".xlsx", ".xls"))])
        if not files:
            self.stdout.write(self.style.ERROR("No Excel files found"))
            return

        created_objs = []
        total_inserted = 0
        BATCH = 500

        for fname in files:
            path = os.path.join(folder, fname)
            mtime = os.path.getmtime(path) 
            audit_date = datetime.date.fromtimestamp(mtime)

            try:  
                df = pd.read_excel(path, dtype=str, keep_default_na=False, sheet_name="Quarters", header=2)
                print(df.columns.tolist()) 

                # Clean column names: strip spaces, remove invisible chars 
                df.columns = (
                       df.columns
                       .str.strip()
                       .str.replace("\u200b", "")    # invisible zero-width space
                       .str.replace("\n", "")
                       .str.replace(r"[^\w\-]", "", regex=True)  # remove other non-alphanumeric chars
                   )


            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not open {fname}: {e}"))
                continue

            if "Narration" not in df.columns:
                self.stdout.write(self.style.WARNING(f"'Narration' column not found in {fname}, skipping"))
                continue

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

                        # Map quarters safely
                        for excel_col, model_field in QUARTER_MAP.items():
                            if excel_col in df.columns:
                                cell = row[excel_col]
                                if pd.isna(cell) or str(cell).strip() == "":
                                    val = "missing"
                                else:
                                    val = str(cell).strip()
                            else:
                                val = "missing"
                            kwargs[model_field] = val

                        created_objs.append(QuarterlyBalanceSheetEntry(**kwargs))
                        break  # stop checking other keywords

            if len(created_objs) >= BATCH:
                QuarterlyBalanceSheetEntry.objects.bulk_create(created_objs)
                total_inserted += len(created_objs)
                self.stdout.write(self.style.SUCCESS(f"Inserted {total_inserted} quarterly records so far..."))
                created_objs = []

        if created_objs:
            QuarterlyBalanceSheetEntry.objects.bulk_create(created_objs)
            total_inserted += len(created_objs)

        self.stdout.write(self.style.SUCCESS(f"Quarterly import finished. Total records inserted: {total_inserted}"))
