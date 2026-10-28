"""from django.contrib import admin   # ✅ must be imported
from .models import BalanceSheetEntry, BalanceSheetYearValue, QuarterlyBalanceSheetEntry



class BalanceSheetYearValueInline(admin.TabularInline):
    model = BalanceSheetYearValue
    extra = 0

@admin.register(BalanceSheetEntry)
class BalanceSheetEntryAdmin(admin.ModelAdmin):
    list_display = (
        'file_name',
        'type',
        'trailing',
        'audit_date',      # if you want this
        'aging_days',      # model property
        'aging_months',
        'aging_years',
        'reminder',
        'created_at',
    )
    list_filter = ('type',)
    search_fields = ('file_name', 'type', 'y24')

@admin.register(QuarterlyBalanceSheetEntry)
class QuarterlyBalanceSheetEntryAdmin(admin.ModelAdmin):

    list_filter = ('type',)
    search_fields = ('file_name', 'type')

    def get_list_display(self, request):

        base_fields = [
            'file_name',
            'type',
        ]

        # Get latest 10 distinct quarters across records
        from .models import QuarterlyBalanceSheetValue

        latest_quarters = (
            QuarterlyBalanceSheetValue.objects
            .order_by('-quarter_date')
            .values_list('quarter_date', flat=True)
            .distinct()[:10]
        )

        dynamic_fields = []

        for q_date in latest_quarters:
            label = q_date.strftime("%b_%y").lower()

            # attach dynamic method
            setattr(
                self,
                f'col_{label}',
                self.make_quarter_column(q_date)
            )

            dynamic_fields.append(f'col_{label}')

        return base_fields + dynamic_fields + [
            'audit_date',
            'aging_days',
            'aging_months',
            'aging_years',
            'reminder',
            'created_at',
        ]

    def make_quarter_column(self, quarter_date):

        def column(obj):
            value = obj.quarter_values.filter(
                quarter_date=quarter_date
            ).first()
            return value.value if value else "-"

        column.short_description = quarter_date.strftime("%b_%y")
        return column


from .models import Equity

@admin.register(Equity)
class EquityAdmin(admin.ModelAdmin):
    list_display = ("name_of_company", "symbol", "series", "date_of_listing", "isin_number")
    search_fields = ("name_of_company", "symbol", "isin_number")


from django.contrib import admin
from .models import MCAPData

@admin.register(MCAPData)
class MCAPDataAdmin(admin.ModelAdmin):
    list_display = ["company", "issue_size", "market_cap", "stock_pe", "ttm_pe"]


    def changelist_view(self, request, extra_context=None):
        # Auto-refresh all items in DB whenever page loads
        for item in MCAPData.objects.all():
            item.refresh_pe_values()
        return super().changelist_view(request, extra_context)
"""