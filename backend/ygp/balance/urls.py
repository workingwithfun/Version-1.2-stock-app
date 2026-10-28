from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BalanceSheetEntryViewSet,
   
    RecalculateAllCompaniesAPIView,
    upload_balance_file,
    
    equities_with_mcap_filtered,
    error_logs_api,
    industry_valuation_stats,
    #upload_quarterly_file, 
    import_equity_l,
    equities_list,
    import_mcap_csv,
    equities_with_mcap,
    import_mapping,
    start_screener_downloads,
    get_screener_logs,
    YearlyMetricsAPIView,
    company_list_api,
    CompanySymbolViewSet,
    update_mapping,
    add_mapping,
    delete_mapping,
    import_nifty_index,   
    screener_download_status,
    screener_excel_recalculation_logs,
    start_screener_excel_recalculation,
    screener_excel_recalculation_status,

)

router = DefaultRouter()
router.register(r"balance-entries", BalanceSheetEntryViewSet, basename="balanceentry")

# urls.py
router.register(r'company-symbols', CompanySymbolViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("upload/yearly/", upload_balance_file),
    #path("upload/quarterly/", upload_quarterly_file, name="upload_quarterly_file"),  # 👈 new
    path("import_equity_l/", import_equity_l, name="import_equity_l"),
    path("equities/", equities_list, name="equities_list"),  # 👈 NEW endpoint
    path("import-mcap/", import_mcap_csv, name="import_mcap_csv"),
    path("equities-with-mcap/", equities_with_mcap, name="equities_with_mcap"),
    path("import-mapping/", import_mapping, name="import_mapping"),
    path("start-screener-downloads/", start_screener_downloads, name="start_screener_downloads"),
    path("yearly-metrics/", YearlyMetricsAPIView.as_view(), name="yearly-metrics"),
    path("screener_logs/", get_screener_logs, name="screener_logs"),   
    path("companies/", company_list_api, name="company_list_api"),
    path('error-logs/', error_logs_api, name='error_logs_api'),
    path("metrics/calculate/", YearlyMetricsAPIView.as_view(), name="calculate-single-company"),
    path("metrics/calculate-all/", RecalculateAllCompaniesAPIView.as_view(), name="calculate- all-companies"),
    path("update-mapping/<str:symbol>/", update_mapping, name="update_mapping"),
    path("delete-mapping/<str:symbol>/", delete_mapping, name="delete_mapping"),
    path("import-nifty-index/", import_nifty_index, name="import-nifty-index"),
    path("add-mapping/", add_mapping, name="add_mapping"),
    path("equities-with-mcap-filtered/", equities_with_mcap_filtered),
    path("industry-valuation-stats/", industry_valuation_stats,name="industry-valuation-stats"),
    path(
        "screener-download-status/",
        screener_download_status,
        name="screener_download_status",
    ),
    path(
        "recalculate-screener-excels/",
        start_screener_excel_recalculation,
        name="start_screener_excel_recalculation",
    ),
    path(
        "recalculate-screener-excels-status/",
        screener_excel_recalculation_status,
        name="screener_excel_recalculation_status",
    ),
    path(
        "recalculation-logs/",
        screener_excel_recalculation_logs,
        name="screener-excel-recalculation-logs",
    ),
    ]
