# balance/serializers.py
from rest_framework import serializers
from balance.models import BalanceSheetEntry, BalanceSheetYearValue
from .models import BalanceSheetYearValue, CompanySymbol, Equity, MCAPData, StockAnalysis, ValueAnalysis10Y, ValueAnalysis5Y
class BalanceSheetEntrySerializer(serializers.ModelSerializer):
    aging_days = serializers.ReadOnlyField()
    aging_months = serializers.ReadOnlyField()
    aging_years = serializers.ReadOnlyField()
    reminder = serializers.ReadOnlyField()
    years = serializers.SerializerMethodField()

    class Meta:
        model = BalanceSheetEntry
        fields = [
            "id",
            "file_name",
            "type",
            "trailing",
            "audit_date",
            "aging_days",
            "aging_months",
            "aging_years",
            "reminder",
            "years",
        ]

    def get_years(self, obj):
        """
        Returns:
        {
            2016: "12.5",
            2017: "14.2",
            2025: "18.0"
        }
        """
        return {
            y.year: y.value
            for y in obj.year_values.all()
        }

    def get_aging_days(self, obj):
        return obj.aging_days

    def get_aging_months(self, obj):
        return obj.aging_months

    def get_aging_years(self, obj):
        return obj.aging_years

    def get_reminder(self, obj):
        return obj.reminder

class BalanceSheetYearValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceSheetYearValue
        fields = ['year', 'value']




class CompanySymbolSerializer(serializers.ModelSerializer):
    isin_number = serializers.SerializerMethodField()

    class Meta:
        model = CompanySymbol
        fields = [
            "name",
            "company_name",
            "symbol",
            "sector",
            "sub_sector_1",
            "sub_sector_2",
            "industry",
            "isin_number",
        ]

    def get_isin_number(self, obj):
        equity = Equity.objects.filter(company=obj).first()
        return equity.isin_number if equity else None


# serializers.py
from rest_framework import serializers
from .models import ErrorLog

class ErrorLogSerializer(serializers.ModelSerializer):
    error_type_display = serializers.CharField(source='get_error_type_display', read_only=True)
    
    class Meta:
        model = ErrorLog
        fields = ['id', 'equity_symbol', 'company_name', 'source', 'created_at', 'error_type', 'error_type_display']


class MCAPDataSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    symbol = serializers.CharField(source="company.symbol", read_only=True)
    sector = serializers.CharField(source="company.sector", read_only=True)
    sub_sector_1 = serializers.CharField(source="company.sub_sector_1", read_only=True)
    sub_sector_2 = serializers.CharField(source="company.sub_sector_2", read_only=True)
    industry = serializers.CharField(source="company.industry", read_only=True)

    class Meta:
        model = MCAPData
        fields = [
            "company_name",
            "symbol",
            "sector",
            "sub_sector_1",
            "sub_sector_2",
            "industry",
            "issue_size",
            "share_price",
            "market_cap",
            "eps_y24",
            "eps_trailing",
            "industry_name",
            "stock_pe",
            "ttm_pe",
            "industry_pe",
            "nifty_index",
        ]

from rest_framework import serializers

class CompanyInfoSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    symbol = serializers.CharField()
    isin_number = serializers.CharField()
    sector = serializers.CharField(allow_null=True)
    sub_sector_1 = serializers.CharField(allow_null=True)
    sub_sector_2 = serializers.CharField(allow_null=True)
    industry = serializers.CharField(allow_null=True)
from rest_framework import serializers

class SummaryConditionsSerializer(serializers.Serializer):
    valuation = serializers.CharField(allow_null=True)
    value_analysis_conclusion = serializers.CharField(allow_null=True)
    target_price_for_entry = serializers.DictField()
    stock_pe_vs_industry_pe = serializers.CharField(allow_null=True)
    growth_analysis = serializers.DictField()

    @staticmethod
    def from_queryset(qs):
        data = {
            "valuation": None,
            "value_analysis_conclusion": None,
            "target_price_for_entry": {
                "status": None,
                "value": None,
            },
            "stock_pe_vs_industry_pe": None,
            "growth_analysis": {},
        }

        PARAM_REVERSE_MAP = {
            "VALUATION": "valuation",
            "VALUATION_CONCLUSION": "value_analysis_conclusion",
            "TARGET_ENTRY": "target_price_for_entry",
            "PE_COMPARISON": "stock_pe_vs_industry_pe",
            "SALES": "sales_growth",
            "OPM": "opm_growth",
            "NPM": "npm_growth",
            "EPS": "eps_growth",
            "ROE": "roe_growth",
        }

        for row in qs:
            param = row.parameter

            if param in ["VALUATION", "VALUATION_CONCLUSION", "PE_COMPARISON"]:
                data[PARAM_REVERSE_MAP[param]] = row.result

            elif param == "TARGET_ENTRY":
                data["target_price_for_entry"]["status"] = row.result
                data["target_price_for_entry"]["value"] = None  # value not stored in DB

            elif param in ["SALES", "OPM", "NPM", "EPS", "ROE"]:
                data["growth_analysis"][PARAM_REVERSE_MAP[param]] = {
                    "trimmean": row.trimmean,
                    "median": row.median,
                    "average": row.average,
                }

        return data

# serializers.py
class GrowthSummarySerializer(serializers.Serializer):
    parameter = serializers.CharField()
    five_y = serializers.DictField(source="5y")
    ten_y = serializers.DictField(source="10y")
    total_average = serializers.DictField()

    @staticmethod
    def from_queryset(qs):
        from collections import defaultdict

        grouped = defaultdict(lambda: {
            "parameter": None,
            "5y": {
                "trimmean": None,
                "median": None,
                "average": None,
            },
            "10y": {
                "trimmean": None,
                "median": None,
                "average": None,
            },
            "total_average": {
                "trimmean": None,
                "median": None,
                "average": None,
            },
        })

        for row in qs:
            metric = row.metric              # e.g. "Revenue"
            method = row.calc_type           # trimmean / median / average

            grouped[metric]["parameter"] = metric

            if hasattr(row, "five_year") and row.five_year is not None:
                grouped[metric]["5y"][method] = row.five_year

            if hasattr(row, "ten_year") and row.ten_year is not None:
                grouped[metric]["10y"][method] = row.ten_year

            if hasattr(row, "total_average") and row.total_average is not None:
                grouped[metric]["total_average"][method] = row.total_average

        return list(grouped.values())

from rest_framework import serializers

class FinalAnalysisTableSerializer(serializers.ModelSerializer):
    Analysis_Tenure = serializers.SerializerMethodField()
    Method = serializers.SerializerMethodField()
    Recommendation = serializers.CharField(source="recommendation")
    Target_Price_for_Entry = serializers.FloatField(
        source="target_price_entry", allow_null=True
    )
    Average_Tenure_wise = serializers.FloatField(
        source="average_tenure", allow_null=True
    )

    class Meta:
        model = StockAnalysis
        fields = [
            "Analysis_Tenure",
            "Method",
            "Recommendation",
            "Target_Price_for_Entry",
            "Average_Tenure_wise",
        ]

    # ---------- MAPPINGS ----------

    TENURE_REVERSE_MAP = {
        "10Y": "10 Year Analysis",
        "5Y": "5 Year Analysis",
        "CONCLUSION": "Value Analysis Conclusion",
        "TARGET": "Target",
    }

    METHOD_REVERSE_MAP = {
        "trimmean": "Trim Mean",
        "median": "Median",
        "average": "Average",
    }

    def get_Analysis_Tenure(self, obj):
        return self.TENURE_REVERSE_MAP.get(obj.analysis_tenure)

    def get_Method(self, obj):
        if obj.method is None:
            return None
        return self.METHOD_REVERSE_MAP.get(obj.method)

class YearlyMetricRowSerializer(serializers.Serializer):
    parameter = serializers.CharField()
    key = serializers.CharField()
    values = serializers.ListField(child=serializers.FloatField(), allow_empty=True)
    stats = serializers.DictField()
    pct_values = serializers.ListField(child=serializers.FloatField(), allow_empty=True)
    pct_stats = serializers.DictField()


class YearlyMetricsTableSerializer(serializers.Serializer):
    years = serializers.ListField(child=serializers.IntegerField())
    rows = YearlyMetricRowSerializer(many=True)


class ValueAnalysis10YSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValueAnalysis10Y
        fields = [
            "year",
            "eps",
            "target_eps",
            "target_price",
            "yoy_return",
            "forecasted_return",
            "holding_period",
        ]


class ValueAnalysis5YSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValueAnalysis5Y
        fields = [
            "year",
            "eps",
            "target_eps",
            "target_price",
            "yoy_return",
            "forecasted_return",
            "holding_period",
        ]

class EquityWithMCAPSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    valuation = serializers.CharField(allow_null=True)

    # Company fields
    company_name = serializers.CharField(allow_null=True)
    sector = serializers.CharField(allow_null=True)
    sub_sector_1 = serializers.CharField(allow_null=True)
    sub_sector_2 = serializers.CharField(allow_null=True)
    industry = serializers.CharField(allow_null=True)

    # Market data
    share_price = serializers.FloatField(allow_null=True)
    market_cap = serializers.FloatField(allow_null=True)
    company_size = serializers.FloatField(allow_null=True)
    # Target price
    target_price = serializers.FloatField(allow_null=True)
