
from collections import defaultdict
from math import isfinite
from statistics import median

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from balance.models import MCAPData, BalanceSheetEntry


class Command(BaseCommand):
    help = "Recalculate EPS, P/E, company size, and industry P/E for all MCAP records."

    def handle(self, *args, **options):
        batch_size = 500
        today = timezone.localdate()

        eps_entries = list(
            BalanceSheetEntry.objects
            .filter(type="EPS")
            .prefetch_related("year_values")
        )

        eps_by_company_id = {}
        for entry in eps_entries:
            if entry.company_id is not None:
                eps_by_company_id.setdefault(entry.company_id, entry)

        records = list(
            MCAPData.objects.select_related("company").all()
        )

        self.stdout.write(f"Processing {len(records)} MCAP records...")

        for obj in records:
            obj.refresh_pe_values(
                skip_industry=True,
                save=False,
                eps_entries=eps_entries,
                eps_by_company_id=eps_by_company_id,
            )
            obj.company_size = obj.compute_company_size()
            obj.last_updated = today

            if obj.company:
                obj.industry_name = (
                    (obj.company.industry or "").strip() or None
                )

        fields = [
            "stock_pe",
            "ttm_pe",
            "eps_y24",
            "eps_trailing",
            "industry_name",
            "company_size",
            "last_updated",
        ]

        with transaction.atomic():
            for start in range(0, len(records), batch_size):
                MCAPData.objects.bulk_update(
                    records[start:start + batch_size],
                    fields=fields,
                    batch_size=batch_size,
                )

        # Compute industry medians from the updated TTM P/E values.
        industry_values = defaultdict(list)

        for obj in records:
            industry = " ".join(
                (obj.company.industry or "").casefold().split()
            ) if obj.company else ""

            if not industry or obj.ttm_pe is None:
                continue

            try:
                pe = float(obj.ttm_pe)
            except (TypeError, ValueError):
                continue

            if isfinite(pe) and pe > 0:
                industry_values[industry].append(pe)

        industry_medians = {
            industry: round(median(values), 2)
            for industry, values in industry_values.items()
        }

        for obj in records:
            industry = " ".join(
                (obj.company.industry or "").casefold().split()
            ) if obj.company else ""

            obj.industry_pe = industry_medians.get(industry)

        with transaction.atomic():
            for start in range(0, len(records), batch_size):
                MCAPData.objects.bulk_update(
                    records[start:start + batch_size],
                    fields=["industry_pe"],
                    batch_size=batch_size,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(records)} MCAP records."
            )
        )
