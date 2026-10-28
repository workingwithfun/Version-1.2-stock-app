# app/management/commands/populate_yearly_matrix.py

from django.core.management.base import BaseCommand
from models import BalanceSheetEntry, YearlyMetricsMatrix
import numpy as np
from django.utils import timezone

class Command(BaseCommand):
    help = "Populate precomputed yearly metrics matrix for all companies"

    def safe_mean(self, arr):
        arr = [v for v in arr if v is not None]
        return float(np.mean(arr)) if arr else None

    def safe_median(self, arr):
        arr = [v for v in arr if v is not None]
        return float(np.median(arr)) if arr else None

    def safe_trimmean(self, arr, proportion=0.1):
        arr = [v for v in arr if v is not None]
        n = len(arr)
        if n == 0:
            return None
        trim = int(n * proportion)
        sorted_arr = sorted(arr)
        trimmed = sorted_arr[trim:n-trim] if n > 2 * trim else sorted_arr
        return float(np.mean(trimmed)) if trimmed else None

    def calc_pct_change(self, values):
        pct=[]
        for i in range(len(values)):
            if i==0 or values[i] is None or values[i-1] is None or values[i-1]==0:
                pct.append(None)
            else:
                pct.append((values[i]-values[i-1])/abs(values[i-1]))
        return pct

    def calc_trailing_pct(self, last_val,trailing_val):
        last_val_safe = 0 if last_val is None else last_val
        trailing_val_safe = 0 if trailing_val is None else trailing_val
        return (trailing_val_safe-last_val_safe)/abs(last_val_safe) if last_val_safe!=0 else 0

    def handle(self, *args, **options):
        companies = BalanceSheetEntry.objects.values_list('file_name', flat=True).distinct()
        year_fields = ["y15","y16","y17","y18","y19","y20","y21","y22","y23","y24"]
        METRICS = ["Sales","OPM","Net profit","EPS","ROC"]

        for company in companies:
            entries = BalanceSheetEntry.objects.filter(file_name__istartswith=company)
            print(f"Processing {company}...")

            for metric in METRICS:
                metric_entry = entries.filter(type=metric).first()
                if not metric_entry:
                    continue

                values=[]
                for yf in year_fields:
                    val = getattr(metric_entry,yf)
                    try:
                        if val in [None,"","missing"]:
                            val_float=None
                        elif isinstance(val,str) and val.endswith("%"):
                            val_float=float(val.rstrip("%"))
                        else:
                            val_float=float(val)
                    except:
                        val_float=None
                    values.append(val_float)

                trailing_val = metric_entry.trailing
                try:
                    if trailing_val in [None,""]:
                        trailing_val=None
                    elif isinstance(trailing_val,str) and trailing_val.endswith("%"):
                        trailing_val=float(trailing_val.rstrip("%"))
                    else:
                        trailing_val=float(trailing_val)
                except:
                    trailing_val=None

                values_with_trailing = values + [trailing_val]
                pct_values = self.calc_pct_change(values)
                last_val_metric = next((v for v in reversed(values) if v is not None), None)
                trailing_pct = self.calc_trailing_pct(last_val_metric,trailing_val)
                pct_values_with_trailing = pct_values + [trailing_pct]

                stats_values = [0 if v is None else v for v in values_with_trailing]
                stats_values_5y = stats_values[-6:]
                pct_clean = [v for v in pct_values_with_trailing if v is not None]
                pct_clean_5y = pct_clean[-6:]

                pct_stats_10y = {
                    "average": self.safe_mean(pct_clean),
                    "median": self.safe_median(pct_clean),
                    "trimmean": self.safe_trimmean(pct_clean),
                }
                pct_stats_5y = {
                    "average": self.safe_mean(pct_clean_5y),
                    "median": self.safe_median(pct_clean_5y),
                    "trimmean": self.safe_trimmean(pct_clean_5y),
                }

                stats_10y = {
                    "average": self.safe_mean(stats_values),
                    "median": self.safe_median(stats_values),
                    "trimmean": self.safe_trimmean(stats_values),
                }
                stats_5y = {
                    "average": self.safe_mean(stats_values_5y),
                    "median": self.safe_median(stats_values_5y),
                    "trimmean": self.safe_trimmean(stats_values_5y),
                }

                # save to DB
                YearlyMetricsMatrix.objects.update_or_create(
                    company=company,
                    metric=metric,
                    defaults={
                        "values": values_with_trailing,
                        "pct_values": pct_values_with_trailing,
                        "stats_5y": stats_5y,
                        "stats_10y": stats_10y,
                        "pct_stats_5y": pct_stats_5y,
                        "pct_stats_10y": pct_stats_10y,
                        "last_updated": timezone.now(),
                    }
                )
            print(f"Finished {company}")
        print("All companies processed.")
