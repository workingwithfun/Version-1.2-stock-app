# balance/models.py
import re
from django.db import models
import datetime


class CompanySymbol(models.Model):
    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True, null=True)  # new column
    symbol = models.CharField(max_length=50,  unique=True)
    sector = models.CharField(max_length=255, blank=True, null=True)
    sub_sector_1 = models.CharField(max_length=255, blank=True, null=True)
    sub_sector_2 = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class BalanceSheetEntry(models.Model):
    TYPE_CHOICES = (
        ('Sales', 'Sales'),
        ('OPM', 'OPM'),
        ('Net profit', 'Net profit'),
        ('EPS', 'EPS'),
        ('ROE', 'ROE'),
        ('ROCE', 'ROCE'),
    )

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    file_name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)

    trailing = models.CharField(max_length=200, blank=True, null=True)
    audit_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "type", "audit_date"],
                name="uniq_company_type_audit"
            )]
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["audit_date"]),
            models.Index(fields=["type"]),
            models.Index(fields=["file_name"]),
            models.Index(fields=["company", "audit_date"]),
        ]
            
    # ======================
    # Aging calculations
    # ======================
    @property
    def aging_days(self):
        if not self.audit_date:
            return None
        return (datetime.date.today() - self.audit_date).days

    @property
    def aging_months(self):
        if not self.audit_date:
            return None
        today = datetime.date.today()
        months = (today.year - self.audit_date.year) * 12 + (today.month - self.audit_date.month)
        day_fraction = (today.day - self.audit_date.day) / 30.0
        return round(months + day_fraction, 1)

    @property
    def aging_years(self):
        if not self.audit_date:
            return None
        days = (datetime.date.today() - self.audit_date).days
        return round(days / 365.25, 2)

    @property
    def reminder(self):
        return "New file required" if self.aging_years and self.aging_years >= 1 else "No action required"

    # ======================
    # EPS helpers
    # ======================
    def _clean_numeric(self, v):
        if v is None:
            return None
        v = str(v).strip().replace(",", "")
        v = v.rstrip("%")
        v = re.sub(r"[^0-9eE\.\-]", "", v)
        try:
            return float(v)
        except Exception:
            return None

    def enforce_year_limit(self, max_years=11):
        qs = self.year_values.order_by("year")
        excess = qs.count() - max_years
        if excess > 0:
            qs[:excess].delete()

    def __str__(self):
        return f"{self.file_name} — {self.type}"


class BalanceSheetYearValue(models.Model):
    entry = models.ForeignKey(
        BalanceSheetEntry,
        related_name="year_values",
        on_delete=models.CASCADE
    )

    year = models.IntegerField()
    value = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        unique_together = ('entry', 'year')       # unique year per entry
        ordering = ['year']   
        indexes = [
            models.Index(fields=["entry"]),
            models.Index(fields=["year"]),
            models.Index(fields=["entry", "year"]),
        ]     # order by entry's type, then year

    def __str__(self):
        return f"{self.entry.file_name} — {self.entry.type} — {self.year}"



from django.db import models

class Equity(models.Model):
    name_of_company = models.CharField(max_length=255)
    equity_symbol = models.CharField(
    max_length=20,
    null=True,
    blank=True
)


    company = models.ForeignKey(
    CompanySymbol,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)

    series = models.CharField(max_length=10)
    date_of_listing = models.DateField()
    isin_number = models.CharField(max_length=20, unique=True)

    @property
    def symbol(self):
        """
        Always show latest CompanySymbol.symbol if mapped,
        otherwise fallback to stored equity_symbol
        """
        return self.company.symbol if self.company else self.equity_symbol
    
    def __str__(self):
        return f"{self.name_of_company} ({self.symbol})"

from django.db import models
import statistics

import re
from django.db import models

class MCAPData(models.Model):
    NIFTY_CHOICES = [
        ("NONE", "Not assigned"),
        ("NIFTY50", "Nifty 50"),
        ("NIFTY100", "Nifty 100"),
        ("NIFTY200", "Nifty 200"),
        ("NIFTY500", "Nifty 500"),
        ("NIFTY750", "Nifty 750"),
    ]

    # FOREIGN KEY NOW USED INSTEAD OF symbol
    company = models.OneToOneField(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="mcap"
      
    )


    issue_size = models.BigIntegerField()
    share_price = models.FloatField()
    market_cap = models.BigIntegerField()
    last_updated = models.DateField(auto_now=True)
    nifty_index = models.CharField(max_length=20, choices=NIFTY_CHOICES, default="NONE")
    company_size = models.CharField(max_length=50, null=True, blank=True)

    eps_y24 = models.FloatField(null=True, blank=True)
    eps_trailing = models.FloatField(null=True, blank=True)

    industry_name = models.CharField(max_length=255, null=True, blank=True)

    stock_pe = models.FloatField(null=True, blank=True)
    ttm_pe = models.FloatField(null=True, blank=True)
    industry_pe = models.FloatField(null=True, blank=True)

    # -------------------------
    # NORMALIZATION HELPERS
    # -------------------------
    def normalized_company_symbol(self):
        if self.company:
            return re.sub(r"[^a-z0-9]", "", self.company.symbol.lower())
        return ""

    def normalized_company_name(self):
        if self.company:
            return re.sub(r"[^a-z0-9]", "", self.company.name.lower())
        return ""

    # -------------------------
    # MAIN PE CALCULATION
    # -------------------------
    
    def update_pe_values(self, skip_industry=False, eps_entries=None,eps_by_company_id=None):
        import logging
        import math
        import re
        import statistics
    
        from .models import BalanceSheetEntry
    
        logger = logging.getLogger(__name__)
    
        if not self.company:
            logger.error("MCAPData has no company assigned. Cannot compute P/E.")
            return None, None, None, None, None, None
    
        company = self.company

        if eps_by_company_id is not None:
            eps_entry = eps_by_company_id.get(company.id)
        else:
            if eps_entries is None:
                eps_entries = list(
                    BalanceSheetEntry.objects
                    .filter(type="EPS")
                    .prefetch_related("year_values")
                )
        
            eps_entry = next(
                (
                    entry for entry in eps_entries
                    if entry.company_id == company.id
                ),
                None,
            )
        # Prefer an exact CompanySymbol foreign-key match.
        eps_entry = next(
            (
                entry for entry in eps_entries
                if entry.company_id == company.id
            ),
            None,
        )
    
        # Fallback only when no FK match exists.
        if eps_entry is None:
            def normalize(value):
                return re.sub(r"[^a-z0-9]", "", (value or "").casefold())
    
            target = normalize(company.symbol)
    
            matches = [
                entry for entry in eps_entries
                if target
                and normalize(entry.file_name).startswith(target)
            ]
    
            if len(matches) == 1:
                eps_entry = matches[0]
    
        industry_name = (company.industry or "").strip() or None
    
        if eps_entry is None:
            return None, None, None, None, None, industry_name
    
        def clean_num(value):
            if value is None:
                return None
    
            value = str(value).strip()
    
            if value.casefold() in ("", "-", "na", "n/a", "missing"):
                return None
    
            value = value.replace(",", "")
            if value.startswith("(") and value.endswith(")"):
                value = "-" + value[1:-1]
    
            value = re.sub(r"[^0-9eE.+-]", "", value)
    
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
    
            return number if math.isfinite(number) else None
    
        # Get the latest annual EPS value dynamically.
        year_values = list(eps_entry.year_values.all())
    
        latest_year_value = (
            max(year_values, key=lambda item: item.year).value
            if year_values
            else None
        )
    
        eps_y24 = clean_num(latest_year_value)
        eps_trailing = clean_num(eps_entry.trailing)
    
        # Avoid division by zero and invalid numeric values.
        share_price = clean_num(self.share_price)
    
        stock_pe = (
            round(share_price / eps_y24, 2)
            if share_price is not None and eps_y24 not in (None, 0)
            else None
        )
    
        ttm_pe = (
            round(share_price / eps_trailing, 2)
            if share_price is not None and eps_trailing not in (None, 0)
            else None
        )
    
        industry_pe = None
    
        if industry_name and not skip_industry:
            pe_values = list(
                MCAPData.objects.filter(
                    company__industry__iexact=industry_name,
                    ttm_pe__isnull=False,
                )
                .exclude(ttm_pe__lte=0)
                .values_list("ttm_pe", flat=True)
            )
    
            valid_values = [
                value for value in pe_values
                if math.isfinite(value)
            ]
    
            if valid_values:
                industry_pe = round(statistics.median(valid_values), 2)
    
        return (
            stock_pe,
            ttm_pe,
            industry_pe,
            eps_y24,
            eps_trailing,
            industry_name,
        )
    
    def compute_company_size(self):
         """
         Computes company size based on market cap in rupees.
         """
         mc = self.market_cap or 0  # in rupees
     
         LARGE_CAP = 50000 * 10_000_000  # 50,000 Cr
         MID_CAP_MIN = 10000 * 10_000_000  # 10,000 Cr
     
         if mc > LARGE_CAP:
             return "Large Cap - >50,000 CR"
         elif mc >= MID_CAP_MIN:
             return "Mid Cap - 10,000 to 50,000 CR"
         else:
             return "Small Cap - <10,000 CR"
     
       
    
    def refresh_pe_values(
        self,
        skip_industry=False,
        save=True,
        eps_entries=None,
        eps_by_company_id=None,
    ):
        (
            stock_pe,
            ttm_pe,
            industry_pe,
            eps_y24,
            eps_trailing,
            industry_name,
        ) = self.update_pe_values(
            skip_industry=skip_industry,
            eps_entries=eps_entries,
            eps_by_company_id=eps_by_company_id,
        )
    
        self.stock_pe = stock_pe
        self.ttm_pe = ttm_pe
        self.eps_y24 = eps_y24
        self.eps_trailing = eps_trailing
        self.industry_name = industry_name
        self.company_size = self.compute_company_size()
    
        if not skip_industry:
            self.industry_pe = industry_pe
    
        if save:
            self.save()
    def __str__(self):
        if self.company:
            return f"{self.company.symbol} - PE: {self.industry_pe}"
        return "MCAP (Unlinked)"

class ScreenerDownloadLog(models.Model):
    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    file_name = models.CharField(max_length=255)
    file_path = models.TextField()
    download_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.file_name} - {self.status}"

class MetricSummary(models.Model):
    TYPE_CHOICES = (
        ("Sales", "Sales"),
        ("OPM", "OPM"),
        ("Net profit", "Net profit"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
        ("ROCE", "ROCE"),
        ("NPM", "NPM"),
    )

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="metric_summaries",
        null=True,
        blank=True,
    )

    file_name = models.CharField(max_length=255)
    base_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    summary_type = models.CharField(
        max_length=50,
        default="pct_change",
    )

    def __str__(self):
        return f"{self.file_name} — {self.base_type} — % Change"


class MetricSummaryYearValue(models.Model):
    summary = models.ForeignKey(
        MetricSummary,
        on_delete=models.CASCADE,
        related_name="year_values",
    )

    # Examples: "2015", "2016", "2025", "Trailing"
    period = models.CharField(max_length=20)

    # Stores the calculated percentage in the same format as before
    value = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["summary", "period"],
                name="uniq_metric_summary_period",
            )
        ]
        ordering = ["period"]

    def __str__(self):
        return f"{self.summary.file_name} — {self.summary.base_type} — {self.period}"

from django.db import models

class BalanceSheetStats(models.Model):
    TYPE_CHOICES = (
        ('Sales', 'Sales'),
        ('OPM', 'OPM'),
        ('Net profit', 'Net profit'),
        ('EPS', 'EPS'),
        ('ROE', 'ROE'),
        ('ROCE', 'ROCE'),
    )

    SUMMARY_TYPE_CHOICES = (
        ('statistical', 'Statistical'),
        ('pct', 'Percentage'),
    )

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="balance_sheet_stats",
        null=False,     # TEMP until backfill
        blank=False
    )
    file_name = models.CharField(max_length=255)
    base_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPE_CHOICES, default='statistical')

    # ---- 10 YEAR SUMMARY ----
    ten_year_avg = models.FloatField(null=True, blank=True)
    ten_year_median = models.FloatField(null=True, blank=True)
    ten_year_trimmean = models.FloatField(null=True, blank=True)

    # ---- 5 YEAR SUMMARY ----
    five_year_avg = models.FloatField(null=True, blank=True)
    five_year_median = models.FloatField(null=True, blank=True)
    five_year_trimmean = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.file_name} — {self.base_type} — {self.summary_type} Stats"

from django.db import models
#expected return 30
class ValueAnalysis10Y(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y",
        db_index=True,
        null=True,
        blank=True     
    )


    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y",
        db_index=True,
        null=True,
        blank=True     
    )


    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("roe", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary",
        db_index=True,
        null=True,
        blank=True     
    )
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"



# expected return 10
class ValueAnalysis10Y_YOY_10(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_10",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_10(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_10",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_10(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("roe", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_10",
        db_index=True,
        null=True,
        blank=True
    )
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_10(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_10",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_10(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_10",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 20
class ValueAnalysis10Y_YOY_20(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_20",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_20(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_20",
        db_index=True,
        null=True,
        blank=True,
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_20(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("roe", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_20",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_20(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_20",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_20(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_20",
        db_index=True,
        null=True,
        blank=True
    )
    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"

# expected return 40
class ValueAnalysis10Y_YOY_40(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_40",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_40(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_40",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_40(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("roe", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_40",
        db_index=True,
        null=True,
        blank=True
    )
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_40(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_40",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_40(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_40",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"



# expected return 50
class ValueAnalysis10Y_YOY_50(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_50",
        db_index=True,
        null=True,
        blank=True
    )
    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_50(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_50",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_50(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("roe", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_50",
        db_index=True,
        null=True,
        blank=True
    )
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_50(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_50",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_50(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_50",
        db_index=True,
        null=True,
        blank=True
    )
    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"



# expected return 75
class ValueAnalysis10Y_YOY_75(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_75",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_75(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_75",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_75(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_75",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_75(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_75",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_75(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_75",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 90
class ValueAnalysis10Y_YOY_90(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_90",
        db_index=True,
        null=True,
        blank=True
    )
    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_90(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_90",
        db_index=True,
        null=True,
        blank=True
    )
    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_90(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_90",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_90(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_90",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_90(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_90",
        db_index=True,
        null=True,
        blank=True
    )
    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"



# expected return 100
class ValueAnalysis10Y_YOY_100(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_100",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_100(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_100",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_100(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_100",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_100(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_100",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_100(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_100",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 125
class ValueAnalysis10Y_YOY_125(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_125",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_125(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_125",
        db_index=True,
        null=True,
        blank=True
    )
    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_125(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_125",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_125(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_125",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_125(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_125",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 150
class ValueAnalysis10Y_YOY_150(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_150",
        db_index=True,
        null=True,
        blank=True
    )
    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_150(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_150",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_150(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_150",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_150(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_150",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_150(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_150",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"



# expected return 175
class ValueAnalysis10Y_YOY_175(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_175",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_175(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_175",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_175(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_175",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_175(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_175",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_175(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_175",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 200
class ValueAnalysis10Y_YOY_200(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_200",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_200(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_200",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_200(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_200",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_200(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_200",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_200(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_200",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 225
class ValueAnalysis10Y_YOY_225(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_225",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_225(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_225",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_225(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_225",
        db_index=True,
        null=True,
        blank=True
    )

    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_225(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_225",
        db_index=True,
        null=True,
        blank=True
    )

    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_225(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_225",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# expected return 250
class ValueAnalysis10Y_YOY_250(models.Model):

    STATS_CHOICES = [
        ("trimmean_10y", "Trimmean - 10 Year"),
        ("median_10y", "Median - 10 Year"),
        ("average_10y", "Average - 10 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_10y_yoy_250",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (10 Year)"
        verbose_name_plural = "Value Analysis (10 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class ValueAnalysis5Y_YOY_250(models.Model):

    STATS_CHOICES = [
        ("trimmean_5y", "Trimmean - 5 Year"),
        ("median_5y", "Median - 5 Year"),
        ("average_5y", "Average - 5 Year"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="value_analysis_5y_yoy_250",
        db_index=True,
        null=True,
        blank=True
    )

    stats_type = models.CharField(max_length=20, choices=STATS_CHOICES)

    year = models.CharField(max_length=10)
    holding_period = models.CharField(max_length=20)

    eps = models.FloatField(null=True, blank=True)
    target_eps = models.FloatField(null=True, blank=True)

    target_price = models.FloatField(null=True, blank=True)
    yoy_return = models.FloatField(null=True, blank=True)
    forecasted_return = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Value Analysis (5 Year)"
        verbose_name_plural = "Value Analysis (5 Year)"
        unique_together = ("company", "stats_type", "year")

    def __str__(self):
        return f"{self.company} - {self.stats_type} - {self.year}"


class GrowthSummary_YOY_250(models.Model):

    METRIC_CHOICES = [
        ("sales", "Sales"),
        ("opm", "OPM"),
        ("npm", "NPM"),
        ("eps", "EPS"),
        ("ROE", "ROE"),
    ]

    TYPE_CHOICES = [
        ("trimmean", "Trimmed Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="growth_summary_yoy_250",
        db_index=True,
        null=True,
        blank=True
    )
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES)
    calc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    five_year = models.FloatField(null=True, blank=True)
    ten_year = models.FloatField(null=True, blank=True)
    total_average = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "metric", "calc_type")
        verbose_name = "Growth Summary"
        verbose_name_plural = "Growth Summaries"

    def __str__(self):
        return f"{self.company} | {self.metric} | {self.calc_type}"


class StockAnalysis_YOY_250(models.Model):

    ANALYSIS_TENURE_CHOICES = [
        ("5Y", "5 Year Analysis"),
        ("10Y", "10 Year Analysis"),
        ("CONCLUSION", "Value Analysis Conclusion"),
        ("TARGET", "Target"),
    ]

    METHOD_CHOICES = [
        ("trimmean", "Trim Mean"),
        ("median", "Median"),
        ("average", "Average"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="stock_analysis_yoy_250",
        db_index=True,
        null=True,
        blank=True
    )
    analysis_tenure = models.CharField(
        max_length=20,
        choices=ANALYSIS_TENURE_CHOICES
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.TextField(
        null=True,
        blank=True
    )

    target_price_entry = models.FloatField(
        null=True,
        blank=True
    )

    average_tenure = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analysis"
        unique_together = ("company", "analysis_tenure", "method")

    def __str__(self):
        return f"{self.company} | {self.analysis_tenure} | {self.method or 'N/A'}"


class Summary_YOY_250(models.Model):

    PARAMETER_CHOICES = [
        ("VALUATION", "Valuation"),
        ("VALUATION_CONCLUSION", "Valuation Analysis Conclusion"),
        ("TARGET_ENTRY", "Target Price for Entry"),
        ("PE_COMPARISON", "Stock P/E Ratio compared to Industry P/E"),
        ("SALES", "Sales"),
        ("OPM", "OPM"),
        ("NPM", "NPM"),
        ("EPS", "EPS"),
        ("ROE", "ROE"),
    ]

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.CASCADE,
        related_name="summary_yoy_250",
        db_index=True,
        null=True,
        blank=True
    )

    parameter = models.CharField(
        max_length=50,
        choices=PARAMETER_CHOICES
    )

    # Used ONLY for first 4 rows
    result = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Used ONLY for growth metrics
    trimmean = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    median = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    average = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Summary"
        verbose_name_plural = "Summary"
        unique_together = ("company", "parameter")

    def __str__(self):
        return f"{self.company} | {self.parameter}"


# models.py

from django.db import models

class ErrorLog(models.Model):
    ERROR_TYPE_CHOICES = (
    ("MISSING_COMPANY_SYMBOL", "Missing in CompanySymbol"),
    ("MISSING_EQUITY", "Missing in Equity"),
    ("NULL_STOCK_PE", "Stock PE not calculated"),
    ("NULL_TTM_PE", "TTM PE not calculated"),
    ("NULL_INDUSTRY_PE", "Industry PE not calculated"),
    ("CALCULATION_FAILED", "Calculation failed"),
    ("CALCULATION_SUCCESS", "Calculation completed successfully"),
    ("SCREENER_DOWNLOAD_FAILED", "Screener file download failed"),
    )


    error_type = models.CharField(
        max_length=50,
        choices=ERROR_TYPE_CHOICES,
        db_index=True
    )

    equity_symbol = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True
    )

    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    source = models.CharField(
        max_length=50,
        default="Equity Import"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_logs"
        indexes = [
            models.Index(fields=["equity_symbol", "error_type"]),
        ]

    def __str__(self):
        return f"{self.error_type} - {self.equity_symbol}"



import uuid

class ExcelRecalculationLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    run_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
    )

    company = models.ForeignKey(
        CompanySymbol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="excel_recalculation_logs",
    )

    file_name = models.CharField(max_length=255)
    file_path = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
    )

    error = models.TextField(blank=True, default="")

    run_started_at = models.DateTimeField(null=True, blank=True)
    run_finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["company", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.status}"
