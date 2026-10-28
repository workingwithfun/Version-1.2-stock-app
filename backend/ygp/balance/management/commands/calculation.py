from balance.models import GrowthSummary, MCAPData, MetricSummary


def calculate_dynamic_valuation(company_symbol, expected_yoy):
    mcap = MCAPData.objects.filter(company=company_symbol).first()
    if not mcap or not mcap.share_price or not mcap.industry_pe:
        return None

    # Fetch EPS from your metrics table (10Y trimmean or median)
    eps_row = (
        MetricSummary.objects.filter(file_name=company_symbol.name, base_type="EPS", summary_type="pct_change")
        .first()
    )

    if not eps_row or eps_row.trailing is None:
        return None

    trailing_eps = float(eps_row.trailing)  # last trailing EPS

    # Project EPS for 6 years based on YOY growth (dynamic)
    projected_eps = trailing_eps
    for _ in range(6):
        projected_eps *= (1 + expected_yoy / 100)

    # Target price = projected EPS * industry PE
    target_price = projected_eps * mcap.industry_pe

    # Discount backward to entry price (today)
    entry_price = target_price / ((1 + expected_yoy / 100) ** 6)

    valuation = "Undervalued" if mcap.share_price < entry_price else "Overvalued"

    return {
        "symbol": company_symbol.symbol,
        "company_name": company_symbol.name,
        "share_price": mcap.share_price,
        "industry_pe": mcap.industry_pe,
        "trailing_eps": trailing_eps,
        "target_price": round(target_price, 2),
        "entry_price": round(entry_price, 2),
        "valuation": valuation,
        "expected_yoy": expected_yoy,
    }

def calculate_metrics_engine(company_symbol, expected_return, models=None):
        expected_return = int(expected_return)
        models = YOY_TABLE_MAP[expected_return]
        MetricSummary     = models["metric_summary"]
        BalanceSheetStats = models["balance_stats"]
        ValueAnalysis10Y  = models["value_10y"]
        ValueAnalysis5Y   = models["value_5y"]
        GrowthSummary     = models["growth"]
        StockAnalysis     = models["stock"]
        Summary           = models["summary"]

        company_id = company_symbol.id
        # ---------------- CLEAN PREVIOUS CALCULATIONS ----------------
        ValueAnalysis10Y.objects.filter(company_id=company_id).delete()
        ValueAnalysis5Y.objects.filter(company_id=company_id).delete()
        MetricSummary.objects.filter(company_id=company_id).delete()
        BalanceSheetStats.objects.filter(company_id=company_id).delete()
        GrowthSummary.objects.filter(company_id=company_id).delete()
        StockAnalysis.objects.filter(company_id=company_id).delete()
        Summary.objects.filter(company_id=company_id).delete()
        entries_map = defaultdict(list)
        for e in BalanceSheetEntry.objects.filter(company_id__in=[company_id]):
            file_key = normalize_key(e.file_name)
            entries_map[file_key].append(e)
        
        entries = list(
            BalanceSheetEntry.objects
            .filter(company_id=company_id)
            .only("type", "y15","y16","y17","y18","y19","y20","y21","y22","y23","y24","trailing")
        )
        if not entries:
           raise ValueError(f"No balance sheet data for {company_symbol.name}")

        if not company_symbol:
            return {"error": "Invalid symbol"}
        
        company_data = CompanySymbolSerializer(company_symbol).data
        year_fields = ["y15","y16","y17","y18","y19","y20","y21","y22","y23","y24"]
        years = list(range(2015,2025)) + ["Trailing"]
        METRICS = ["Sales","OPM","Net profit","EPS","ROE"]
        rows = []

        # --- Safe stat helpers ---
        def safe_mean(arr):
            arr = [v for v in arr if v is not None]
            return float(np.mean(arr)) if arr else None

        def safe_median(arr):
            arr = [v for v in arr if v is not None]
            return float(np.median(arr)) if arr else None

        def safe_trimmean(arr, proportion=0.1):
            arr = [v for v in arr if v is not None]
            n = len(arr)
            if n==0:
                return None
            trim = int(n*proportion)
            sorted_arr = sorted(arr)
            trimmed = sorted_arr[trim:n-trim] if n>2*trim else sorted_arr
            return float(np.mean(trimmed)) if trimmed else None
        # --- % change helpers ---
        def calc_pct_change(values):
            pct=[]
            for i in range(len(values)):
                if i==0 or values[i] is None or values[i-1] is None or values[i-1]==0:
                    pct.append(None)
                else:
                    pct.append((values[i]-values[i-1])/abs(values[i-1]))
            return pct

        def calc_trailing_pct(last_val,trailing_val):
            last_val_safe = 0 if last_val is None else last_val
            trailing_val_safe = 0 if trailing_val is None else trailing_val
            return (trailing_val_safe-last_val_safe)/abs(last_val_safe) if last_val_safe!=0 else 0
      
        def parse_value(val):
            """Parse both numeric and % values from DB."""
            if val in [None, "", "missing"]:
                return None
            if isinstance(val, str) and val.strip().endswith("%"):
                try:
                    return float(val.strip().replace("%", ""))
                except:
                    return None
            try:
                return float(val)
            except:
                return None
        
        def normalize_input_percentage(val):
            if val in [None, "", "missing"]:
                return None
        
            s = str(val).strip()
        
            # If string ends with %, convert to float (percentage number)
            if s.endswith("%"):
                try:
                    return float(s.rstrip("%"))
                except:
                    return None
        
            # Otherwise, just convert to float AS IS (no scaling)
            try:
                return float(s)
            except:
                return None
        
        def pct_to_str(val):
            if val is None:
                return None
            return f"{round(val * 100, 2)}%"
        
        metric_summary_bulk = []
        balance_stat_bulk = []

        for metric in METRICS:
            #metric_entry = entries.filter(type=metric).first()
            filtered = filter_entries(entries, type=metric)
            metric_entry = filtered[0] if filtered else None

            if metric_entry:
                values=[]
                for yf in year_fields:
                    val = getattr(metric_entry,yf)
                    try:
                        val_float = normalize_input_percentage(val)

                    except:
                        val_float=None
                    values.append(val_float)

                trailing_val = metric_entry.trailing
                try:
                    if trailing_val in [None,""]:
                        trailing_val=None
                    trailing_val = normalize_input_percentage(trailing_val)

                except:
                    trailing_val=None

                values_with_trailing = values + [trailing_val]

                pct_values = calc_pct_change(values)
                last_val_metric = next((v for v in reversed(values) if v is not None), None)
                trailing_pct = calc_trailing_pct(last_val_metric,trailing_val)
                pct_values_with_trailing = pct_values + [trailing_pct]
                pct_last5_with_trailing = pct_values_with_trailing[-6:]

                # --- Absolute stats (replace None with 0 for stats calculation) ---
                stats_values = [0 if v is None else v for v in values_with_trailing]  # always 11 values

                # Last 5 years + trailing
                stats_values_5y = stats_values[-6:]  # last 5 + trailing

                # pct stats: ignore None
                pct_clean = [v for v in pct_values_with_trailing if v is not None]
                pct_clean_5y = [v for v in pct_last5_with_trailing if v is not None] # last 5 + trailing

                pct_stats_10y = {
                    "average": safe_mean(pct_clean),
                    "median": safe_median(pct_clean),
                    "trimmean": safe_trimmean(pct_clean),
                }
                pct_stats_5y = {
                    "average": safe_mean(pct_clean_5y),
                    "median": safe_median(pct_clean_5y),
                    "trimmean": safe_trimmean(pct_clean_5y),
                }

                rows.append({
                    "key": metric,
                    "trailing": trailing_val,
                    "values": values_with_trailing,
                    "pct_values": pct_values_with_trailing,
                    "stats":{
                        "10y":{
                            "average": safe_mean(stats_values),
                            "median": safe_median(stats_values),
                            "trimmean": safe_trimmean(stats_values),
                        },
                        "5y":{
                            "average": safe_mean(stats_values_5y),
                            "median": safe_median(stats_values_5y),
                            "trimmean": safe_trimmean(stats_values_5y),
                        },
                    },
                    "pct_stats":{
                        "10y": pct_stats_10y,
                        "5y": pct_stats_5y,
                    }
                })

                # --- NPM after Net Profit ---
                if metric == "Net profit":
                    filtered_sales = filter_entries(entries, type="Sales")
                    sales_entry = filtered_sales[0] if filtered_sales else None
               
                    if sales_entry:
                        npm_values=[]
                        for yf in year_fields:
                            try:
                                net_val = getattr(metric_entry,yf)
                                sales_val = getattr(sales_entry,yf)
                                net_val=float(net_val) if net_val not in [None,"","missing"] else None
                                sales_val=float(sales_val) if sales_val not in [None,"","missing"] else None
                                npm_values.append((net_val/sales_val*100) if sales_val not in [None,0] and net_val is not None else None)
                            except:
                                npm_values.append(None)

                        net_trailing = float(metric_entry.trailing) if metric_entry.trailing not in [None,""] else None
                        sales_trailing = float(sales_entry.trailing) if sales_entry.trailing not in [None,""] else None
                        trailing_val_npm = (net_trailing/sales_trailing*100) if net_trailing is not None and sales_trailing not in [None,0] else None

                        npm_values_with_trailing = npm_values + [trailing_val_npm]

                        npm_pct_values = calc_pct_change(npm_values)
                        last_val_npm = next((v for v in reversed(npm_values) if v is not None), None)
                        trailing_pct_npm = calc_trailing_pct(last_val_npm,trailing_val_npm)
                        npm_pct_values_with_trailing = npm_pct_values + [trailing_pct_npm]

                        stats_npm = [0 if v is None else v for v in npm_values_with_trailing]
                        stats_npm_5y = stats_npm[-6:]

                        pct_clean_npm = [v for v in npm_pct_values_with_trailing if v is not None]
                        pct_clean_5y_npm = pct_clean_npm[-6:]

                        rows.append({
                            "key": "NPM",
                            "trailing": trailing_val_npm,
                            "values": npm_values_with_trailing,
                            "pct_values": npm_pct_values_with_trailing,
                            "stats":{
                                "10y":{
                                    "average": safe_mean(stats_npm),
                                    "median": safe_median(stats_npm),
                                    "trimmean": safe_trimmean(stats_npm),
                                },
                                "5y":{
                                    "average": safe_mean(stats_npm_5y),
                                    "median": safe_median(stats_npm_5y),
                                    "trimmean": safe_trimmean(stats_npm_5y),
                                },
                            },
                            "pct_stats":{
                                "10y":{
                                    "average": safe_mean(pct_clean_npm),
                                    "median": safe_median(pct_clean_npm),
                                    "trimmean": safe_trimmean(pct_clean_npm),
                                },
                                "5y":{
                                    "average": safe_mean(pct_clean_5y_npm),
                                    "median": safe_median(pct_clean_5y_npm),
                                    "trimmean": safe_trimmean(pct_clean_5y_npm),
                                },
                            }
                        })

            else:  # metric not found
                rows.append({
                    "key": metric,
                    "trailing": None,
                    "values": [None]*11,
                    "pct_values": [None]*11,
                    "stats":{
                        "10y":{"average":None,"median":None,"trimmean":None},
                        "5y":{"average":None,"median":None,"trimmean":None},
                    },
                    "pct_stats":{
                        "10y":{"average":None,"median":None,"trimmean":None},
                        "5y":{"average":None,"median":None,"trimmean":None},
                    }
                })
                    # ---- SAVE ABSOLUTE SUMMARY ----
       
            metric_summary_bulk.append(
            MetricSummary(
                company_id=company_id,
                file_name=company_symbol.name,
                base_type=metric,
                summary_type="pct_change",
                y15=pct_to_str(pct_values_with_trailing[0]),
                y16=pct_to_str(pct_values_with_trailing[1]),
                y17=pct_to_str(pct_values_with_trailing[2]),
                y18=pct_to_str(pct_values_with_trailing[3]),
                y19=pct_to_str(pct_values_with_trailing[4]),
                y20=pct_to_str(pct_values_with_trailing[5]),
                y21=pct_to_str(pct_values_with_trailing[6]),
                y22=pct_to_str(pct_values_with_trailing[7]),
                y23=pct_to_str(pct_values_with_trailing[8]),
                y24=pct_to_str(pct_values_with_trailing[9]),
                trailing=pct_to_str(pct_values_with_trailing[10]),
            )
        )
        
            # --- SAVE ABSOLUTE / STATISTICAL SUMMARY ---
            balance_stat_bulk.append(
            BalanceSheetStats(
                company_id=company_id,
                file_name=company_symbol.name,
                base_type=metric,
                summary_type='statistical',
                ten_year_avg=safe_mean(stats_values),
                ten_year_median=safe_median(stats_values),
                ten_year_trimmean=safe_trimmean(stats_values),
                five_year_avg=safe_mean(stats_values_5y),
                five_year_median=safe_median(stats_values_5y),
                five_year_trimmean=safe_trimmean(stats_values_5y),
            )
        )
        
            balance_stat_bulk.append(
            BalanceSheetStats(
                company_id=company_id,
                file_name=company_symbol.name,
                base_type=metric,
                summary_type='pct',
                ten_year_avg=safe_mean(pct_clean) * 100 if safe_mean(pct_clean) is not None else None,
                ten_year_median=safe_median(pct_clean) * 100 if safe_median(pct_clean) is not None else None,
                ten_year_trimmean=safe_trimmean(pct_clean) * 100 if safe_trimmean(pct_clean) is not None else None,
                five_year_avg=safe_mean(pct_clean_5y) * 100 if safe_mean(pct_clean_5y) is not None else None,
                five_year_median=safe_median(pct_clean_5y) * 100 if safe_median(pct_clean_5y) is not None else None,
                five_year_trimmean=safe_trimmean(pct_clean_5y) * 100 if safe_trimmean(pct_clean_5y) is not None else None,
            )
        )
        
            if metric == "Net profit":
               filtered_sales = filter_entries(entries, type="Sales")
               sales_entry = filtered_sales[0] if filtered_sales else None
               
           
               if sales_entry:
                   npm_values = []
                   for yf in year_fields:
                       try:
                           net_val = getattr(metric_entry, yf)
                           sales_val = getattr(sales_entry, yf)
           
                           net_val = float(net_val) if net_val not in [None, "", "missing"] else None
                           sales_val = float(sales_val) if sales_val not in [None, "", "missing"] else None
           
                           npm_values.append(
                               (net_val / sales_val * 100)
                               if sales_val not in [None, 0] and net_val is not None else None
                           )
                       except:
                           npm_values.append(None)
           
                   # trailing
                   net_trailing = float(metric_entry.trailing) if metric_entry.trailing not in [None, ""] else None
                   sales_trailing = float(sales_entry.trailing) if sales_entry.trailing not in [None, ""] else None
           
                   trailing_val_npm = (
                       net_trailing / sales_trailing * 100
                       if net_trailing is not None and sales_trailing not in [None, 0]
                       else None
                   )
           
                   npm_values_with_trailing = npm_values + [trailing_val_npm]
           
                   # PCT CHANGE for NPM
                   npm_pct = calc_pct_change(npm_values)
                   last_val_npm = next((v for v in reversed(npm_values) if v is not None), None)
                   trailing_pct_npm = calc_trailing_pct(last_val_npm, trailing_val_npm)
           
                   npm_pct_with_trailing = npm_pct + [trailing_pct_npm]
           
                   # SAVE NPM AS PERCENT DATA
                   metric_summary_bulk.append(
                       MetricSummary(
        company_id=company_id,
        file_name=company_symbol.name,
        base_type="NPM",
        summary_type="pct_change",
        y15=pct_to_str(npm_pct_with_trailing[0]),
        y16=pct_to_str(npm_pct_with_trailing[1]),
        y17=pct_to_str(npm_pct_with_trailing[2]),
        y18=pct_to_str(npm_pct_with_trailing[3]),
        y19=pct_to_str(npm_pct_with_trailing[4]),
        y20=pct_to_str(npm_pct_with_trailing[5]),
        y21=pct_to_str(npm_pct_with_trailing[6]),
        y22=pct_to_str(npm_pct_with_trailing[7]),
        y23=pct_to_str(npm_pct_with_trailing[8]),
        y24=pct_to_str(npm_pct_with_trailing[9]),
        trailing=pct_to_str(npm_pct_with_trailing[10]),
    )
                   )
                   
                   balance_stat_bulk.append(
                       BalanceSheetStats(
                           company_id=company_id,
                           file_name=company_symbol.name,
                           base_type="NPM",
                           summary_type="pct",
                           ten_year_avg=safe_mean(pct_clean_npm) * 100 if safe_mean(pct_clean_npm) is not None else None,
                           ten_year_median=safe_median(pct_clean_npm) * 100 if safe_median(pct_clean_npm) is not None else None,
                           ten_year_trimmean=safe_trimmean(pct_clean_npm) * 100 if safe_trimmean(pct_clean_npm) is not None else None,
                           five_year_avg=safe_mean(pct_clean_5y_npm) * 100 if safe_mean(pct_clean_5y_npm) is not None else None,
                           five_year_median=safe_median(pct_clean_5y_npm) * 100 if safe_median(pct_clean_5y_npm) is not None else None,
                           five_year_trimmean=safe_trimmean(pct_clean_5y_npm) * 100 if safe_trimmean(pct_clean_5y_npm) is not None else None,
                       )
                   )

        MetricSummary.objects.bulk_create(metric_summary_bulk)
        BalanceSheetStats.objects.bulk_create(balance_stat_bulk)
                 
        # ---- Value Analysis ----
        value_analysis_trimmean = []
        value_analysis_10y_bulk = []

        eps_row = next((r for r in rows if r["key"] == "EPS"), None)        
        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_trimmean_pct = eps_row["pct_stats"]["10y"]["trimmean"] or 0
        
            # Find the last numeric year from 'years' list (ignoring 'Trailing')
            last_year = max(y for y in years if isinstance(y, int))
        
            eps = trailing_eps
            target_eps_list = []
        
            # Step 1: Calculate Target EPS for each year
            for i in range(1, 7):  # 6-year projection
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"  # e.g., Mar-26
                target_eps = eps * (1 + eps_trimmean_pct)
        
                target_eps_list.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None, 
                    "Forecasted_return": None, # will fill later
                    "YOY_return": None     # new column
                })
        
                eps = target_eps
        
            # ✅ Step 2: Fetch industry P/E using symbol
            
            mcap_data = MCAPData.objects.filter(company=company_symbol).first()
# expected_return is already a function argument

            industry_pe = mcap_data.industry_pe if mcap_data and mcap_data.industry_pe else None
 
            share_price = mcap_data.share_price if mcap_data and mcap_data.share_price else None
        
            # ✅ Step 4: Calculate Target Stock Price
            if industry_pe and share_price:
                # Last year = EPS × PE
                target_eps_list[-1]["target_price"] = target_eps_list[-1]["target_eps"] * industry_pe
        
                # Discount backwards for earlier years
                for j in reversed(range(len(target_eps_list) - 1)):
                    target_eps_list[j]["target_price"] = (
                        target_eps_list[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
        
                # ✅ Step 5: Calculate YOY return
                for row in target_eps_list:
                    if row["target_price"]:
                        row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )    
            else:
                # Fallback: still return EPS projections, but prices = "-" and no returns
                for row in target_eps_list:
                    row["target_price"] = None
                    row["YOY_return"] = None
            # ✅ Step 6: Calculate Forecasted Return
          
            value_analysis_trimmean = target_eps_list
            # ✅ SAVE EACH ROW TO DB
            for row in target_eps_list:
                value_analysis_10y_bulk.append(
                    ValueAnalysis10Y(
                        company_id=company_id,
                        stats_type="trimmean_10y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
            
        value_analysis_median = []        
        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_median_pct = eps_row["pct_stats"]["10y"]["median"] or 0  # ✅ use median here
        
            last_year = max(y for y in years if isinstance(y, int))
            eps = trailing_eps
            target_eps_list_median = []
        
            for i in range(1, 7):
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"
                target_eps = eps * (1 + eps_median_pct)
        
                target_eps_list_median.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None
                })
                eps = target_eps
        
            if industry_pe and share_price:
                target_eps_list_median[-1]["target_price"] = target_eps_list_median[-1]["target_eps"] * industry_pe
                for j in reversed(range(len(target_eps_list_median) - 1)):
                    target_eps_list_median[j]["target_price"] = (
                        target_eps_list_median[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
                for row in target_eps_list_median:
                    if row["target_price"]:
                        row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )
                        
            else:
                for row in target_eps_list_median:
                    row["target_price"] = None
                    row["YOY_return"] = None
        
            value_analysis_median = target_eps_list_median
        
            # ✅ SAVE EACH ROW TO DB
            for row in target_eps_list_median:
                value_analysis_10y_bulk.append(
                    ValueAnalysis10Y(
                        company_id=company_id,
                        stats_type="median_10y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
            
        # ---- Value Analysis (Average - 10 Year) ----
        value_analysis_average = []
        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_average_pct = eps_row["pct_stats"]["10y"]["average"] or 0  # ✅ use average here
        
            last_year = max(y for y in years if isinstance(y, int))
            eps = trailing_eps
            target_eps_list_avg = []
        
            for i in range(1, 7):
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"
                target_eps = eps * (1 + eps_average_pct)
        
                target_eps_list_avg.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None
                })
                eps = target_eps
        
            if industry_pe and share_price:
                target_eps_list_avg[-1]["target_price"] = target_eps_list_avg[-1]["target_eps"] * industry_pe
                for j in reversed(range(len(target_eps_list_avg) - 1)):
                    target_eps_list_avg[j]["target_price"] = (
                        target_eps_list_avg[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
                for row in target_eps_list_avg:
                    if row["target_price"]:
                       row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )
            else:
                for row in target_eps_list_avg:
                    row["target_price"] = None
                    row["YOY_return"] = None
        
            value_analysis_average = target_eps_list_avg
        
             # ✅ SAVE EACH ROW TO DB
            for row in target_eps_list_avg:

                value_analysis_10y_bulk.append(
                    ValueAnalysis10Y(
                        company_id=company_id,
                        stats_type="average_10y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
            ValueAnalysis10Y.objects.bulk_create(value_analysis_10y_bulk)

            # ---- Value Analysis (Trim Mean - 5 Year) ----
        value_analysis_5y_bulk = []
        value_analysis_trimmean_5y = []
        

        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_trimmean_5y_pct = eps_row["pct_stats"]["5y"]["trimmean"] or 0  # ✅ use 5y trimmean
        
            last_year = max(y for y in years if isinstance(y, int))
            eps = trailing_eps
            target_eps_list_trimmean_5y = []
        
            for i in range(1, 7):
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"
                target_eps = eps * (1 + eps_trimmean_5y_pct)
        
                target_eps_list_trimmean_5y.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None
                })
                eps = target_eps
        
            if industry_pe and share_price:
                target_eps_list_trimmean_5y[-1]["target_price"] = target_eps_list_trimmean_5y[-1]["target_eps"] * industry_pe
                for j in reversed(range(len(target_eps_list_trimmean_5y) - 1)):
                    target_eps_list_trimmean_5y[j]["target_price"] = (
                        target_eps_list_trimmean_5y[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
                for row in target_eps_list_trimmean_5y:
                    if row["target_price"]:
                        row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )
            else:
                for row in target_eps_list_trimmean_5y:
                    row["target_price"] = None
                    row["YOY_return"] = None
        
            value_analysis_trimmean_5y = target_eps_list_trimmean_5y
            
            for row in target_eps_list_trimmean_5y:
                value_analysis_5y_bulk.append(
                    ValueAnalysis5Y(
                        company_id=company_id,
                        stats_type="trimmean_5y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
            
        # ---- Value Analysis (Median - 5 Year) ----
        value_analysis_median_5y = []
        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_median_5y_pct = eps_row["pct_stats"]["5y"]["median"] or 0  # ✅ use 5y median
        
            last_year = max(y for y in years if isinstance(y, int))
            eps = trailing_eps
            target_eps_list_median_5y = []
        
            for i in range(1, 7):
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"
                target_eps = eps * (1 + eps_median_5y_pct)
        
                target_eps_list_median_5y.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None
                })
                eps = target_eps
        
            if industry_pe and share_price:
                target_eps_list_median_5y[-1]["target_price"] = target_eps_list_median_5y[-1]["target_eps"] * industry_pe
                for j in reversed(range(len(target_eps_list_median_5y) - 1)):
                    target_eps_list_median_5y[j]["target_price"] = (
                        target_eps_list_median_5y[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
                for row in target_eps_list_median_5y:
                    if row["target_price"]:
                        row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )
            else:
                for row in target_eps_list_median_5y:
                    row["target_price"] = None
                    row["YOY_return"] = None
        
            value_analysis_median_5y = target_eps_list_median_5y
            
            for row in target_eps_list_median_5y:
                value_analysis_5y_bulk.append(
                    ValueAnalysis5Y(
                        company_id=company_id,
                        stats_type="median_5y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
            
        # ---- Value Analysis (Average - 5 Year) ----
        value_analysis_average_5y = []
        if eps_row:
            trailing_eps = eps_row["trailing"] or 0
            eps_average_5y_pct = eps_row["pct_stats"]["5y"]["average"] or 0  # ✅ use 5y average
        
            last_year = max(y for y in years if isinstance(y, int))
            eps = trailing_eps
            target_eps_list_avg_5y = []
        
            for i in range(1, 7):
                year_number = last_year + i
                year_label = f"Mar-{str(year_number)[-2:]}"
                target_eps = eps * (1 + eps_average_5y_pct)
        
                target_eps_list_avg_5y.append({
                    "year": year_label,
                    "eps": eps,
                    "target_eps": target_eps,
                    "holding_period": f"{i} Year",
                    "target_price": None,
                    "Forecasted_return": None,
                    "YOY_return": None
                })
                eps = target_eps
        
            if industry_pe and share_price:
                target_eps_list_avg_5y[-1]["target_price"] = target_eps_list_avg_5y[-1]["target_eps"] * industry_pe
                for j in reversed(range(len(target_eps_list_avg_5y) - 1)):
                    target_eps_list_avg_5y[j]["target_price"] = (
                        target_eps_list_avg_5y[j + 1]["target_price"] / (1 + expected_return / 100)
                    )
                for row in target_eps_list_avg_5y:
                    if row["target_price"]:
                        row["YOY_return"] = (
                            ((row["target_price"] - share_price) / share_price) * 100
                            if share_price not in [None, 0]
                            else None
                        )
            else:
                for row in target_eps_list_avg_5y:
                    row["target_price"] = None
                    row["YOY_return"] = None
        
            value_analysis_average_5y = target_eps_list_avg_5y
            for row in target_eps_list_avg_5y:
                value_analysis_5y_bulk.append(
                    ValueAnalysis5Y(
                        company_id=company_id,
                        stats_type="average_5y",
                        year=row["year"],
                        holding_period=row["holding_period"],
                        eps=row["eps"],
                        target_eps=row["target_eps"],
                        target_price=row["target_price"],
                        yoy_return=row["YOY_return"],
                    )
                )
        ValueAnalysis5Y.objects.bulk_create(value_analysis_5y_bulk)
    
        # ---- Growth Summary Table ----
        growth_summary = []
        growth_bulk = []

        for metric_row in rows:
                key = metric_row["key"]
                pct_stats = metric_row["pct_stats"]
            
                # Collect row values (5y + 10y)
                row_values = [
                    pct_stats["5y"]["trimmean"],
                    pct_stats["5y"]["median"],
                    pct_stats["5y"]["average"],
                    pct_stats["10y"]["trimmean"],
                    pct_stats["10y"]["median"],
                    pct_stats["10y"]["average"],
                ]
            
                row_values_clean = [v for v in row_values if v is not None]
            
                def safe_mean(arr):
                    return float(np.mean(arr)) if arr else None
            
                def safe_median(arr):
                    return float(np.median(arr)) if arr else None
            
                def safe_trimmean(arr, proportion=0.1):
                    arr = sorted(arr)
                    n = len(arr)
                    if n == 0:
                        return None
                    k = int(n * proportion)
                    trimmed = arr[k:n - k] if n > 2 * k else arr
                    return float(np.mean(trimmed)) if trimmed else None
            
                total_average = {
                    "trimmean": safe_trimmean(row_values_clean),  # TrimMean of the whole row
                    "median": safe_median(row_values_clean),      # Median of the whole row
                    "average": safe_mean(row_values_clean),       # Average of the whole row
                }
            
                growth_summary.append({
                    "parameter": key,
                    "5y": pct_stats["5y"],
                    "10y": pct_stats["10y"],
                    "total_average": total_average
                })
        def to_percentage(value):
            if value is None:
                return None
            return round(float(value) * 100, 2)
        
        for row in growth_summary:
            metric = row["parameter"]
        
            for calc_type in ["trimmean", "median", "average"]:
                growth_bulk.append(
                    GrowthSummary(
                        company_id=company_id,
                        metric=metric,
                        calc_type=calc_type,
                        five_year=to_percentage(row["5y"].get(calc_type)),
                        ten_year=to_percentage(row["10y"].get(calc_type)),
                        total_average=to_percentage(row["total_average"].get(calc_type)),
                    )
                )
        
        GrowthSummary.objects.bulk_create(growth_bulk)

        def get_recommendation(method, share_price, yoy_return, market_cap, target_price_entry):
            market_cap = mcap_data.market_cap if mcap_data and mcap_data.market_cap else None
            if target_price_entry is None:
                return "Data not available"
            
            if method == "Trim Mean":
                return "Recommended to buy at current stock price" if share_price < target_price_entry else "Recommended to wait until target price entry is achieved"
            elif method == "Median":
                return "Recommended to buy at current stock price" if share_price < target_price_entry else "Recommended to wait until target price entry is achieved"
            elif method == "Average":
                return "Recommended to buy at current stock price" if share_price < target_price_entry else "Recommended to wait until target price entry is achieved"
            return "N/A"
 
        final_analysis_table = []
        market_price = share_price  # fallback
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
            
            for method_name, table in methods.items():
                target_price_entry = None
                yoy_return = None
        
                if table and len(table) > 0:
                    first_row = table[0]
                    target_price_first = first_row.get("target_price")
                    yoy_return_first = first_row.get("YOY_return")
                    yoy_return = yoy_return_first if yoy_return_first is not None else 0
                    market_first = first_row.get("market_price") or market_price
        
                    # ✅ Apply your formula for ALL cases:
                    if target_price_first is not None:
                        target_price_entry = target_price_first / (1 + expected_return/100)
        
                # Recommendation based on method
                recommendation = get_recommendation(method_name, share_price, yoy_return, market_first, target_price_entry)
        
                tenure_target_prices.append(target_price_entry)
        
                tenure_rows.append({
                    "Analysis Tenure": tenure,
                    "Method": method_name,
                    "Recommendation": recommendation,
                    "Target Price for Entry": target_price_entry
                })
        
            # Compute tenure-wise median
            valid_prices = [v for v in tenure_target_prices if v is not None]
            avg_tenure_value = float(np.median(valid_prices)) if valid_prices else None
        
            for row in tenure_rows:
                row["Average Tenure-wise"] = avg_tenure_value
                final_analysis_table.append(row)

        
        def is_finite_number(x):
            return isinstance(x, (int, float)) and not math.isnan(x)
        
        target_price_entries = [
            float(r["Target Price for Entry"]) for r in final_analysis_table
            if is_finite_number(r.get("Target Price for Entry"))
        ]
        
        avg_tenure_values = [
            float(r["Average Tenure-wise"]) for r in final_analysis_table
            if is_finite_number(r.get("Average Tenure-wise"))
        ]
        
        median_target_price_entry = median(target_price_entries) if target_price_entries else None
        mean_average_tenure = mean(avg_tenure_values) if avg_tenure_values else None
        
        # Build recommendation
        if median_target_price_entry is None or share_price is None:
            conclusion_recommendation = "Data not available"
        else:
            conclusion_recommendation = (
                "Recommended to buy at current stock price"
                if float(share_price) < float(median_target_price_entry)
                else "Recommended to wait until target price entry is achieved"
            )
        
        # ✅ Append single conclusion row
        final_analysis_table.append({
            "Analysis Tenure": "Value Analysis Conclusion",
            "Method": None,
            "Recommendation": conclusion_recommendation,
            "Target Price for Entry": float(median_target_price_entry) if median_target_price_entry is not None else None,
            "Average Tenure-wise": float(mean_average_tenure) if mean_average_tenure is not None else None,
        })

        # ✅ Compute Target row
        if median_target_price_entry is not None and mean_average_tenure is not None:
            target_avg_value = (float(median_target_price_entry) + float(mean_average_tenure)) / 2
        else:
            target_avg_value = None
                
        va10y_updates = []
        va5y_updates = []

        if target_avg_value is not None:  # ensure target exists
                for row in value_analysis_trimmean:
                    if row["target_price"] is not None:

                        row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )
                        va10y_updates.append(
                            ValueAnalysis10Y(
                                company_id=company_id,
                                stats_type="trimmean_10y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],
                            )
                        )
                        
                    else:
                        row["Forecasted_return"] = None    
                for row in value_analysis_median:
                    if row["target_price"] is not None:
                       row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )
                       va10y_updates.append(
                            ValueAnalysis10Y(
                                company_id=company_id,
                                stats_type="median_10y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],
                            )
                        )
                for row in value_analysis_average:
                    if row["target_price"] is not None:
                        row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )

                        va10y_updates.append(
                            ValueAnalysis10Y(
                                company_id=company_id,
                                stats_type="average_10y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],
                            )
                        )
                
                ValueAnalysis10Y.objects.bulk_update(
                    va10y_updates,
                    ["forecasted_return"]
                )
                for row in value_analysis_trimmean_5y:
                    if row["target_price"] is not None:
                        row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )
                        va5y_updates.append(
                            ValueAnalysis5Y(
                                company_id=company_id,
                                stats_type="trimmean_5y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],)
                        )
                    
                for row in value_analysis_median_5y:
                    if row["target_price"] is not None:
                        row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )
                        va5y_updates.append(
                            ValueAnalysis5Y(
                                company_id=company_id,
                                stats_type="median_5y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],)
                        )
                for row in value_analysis_average_5y:
                    if row["target_price"] is not None:
                        row["Forecasted_return"] = (
                            ((row["target_price"] - target_avg_value) / target_avg_value) * 100
                            if target_avg_value not in [None, 0]
                            else None
                        )
                        
                        va5y_updates.append(
                            ValueAnalysis5Y(
                                company_id=company_id,
                                stats_type="average_5y",
                                year=row["year"],
                                forecasted_return=row["Forecasted_return"],)
                        )
        
                
                ValueAnalysis5Y.objects.bulk_update(
                    va5y_updates,
                    ["forecasted_return"]
                )
                    
        else:
                for row in target_eps_list:
                    row["Forecasted_return"] = None
        
        # Append single Target row
        final_analysis_table.append({
        "Analysis Tenure": "Target",
        "Method": None,
        "Recommendation": target_avg_value,  # numeric average stored here
        "Target Price for Entry": None,
        "Average Tenure-wise": None,
    })
        TENURE_MAP = {
            "5 Year Analysis": "5Y",
            "10 Year Analysis": "10Y",
            "Value Analysis Conclusion": "CONCLUSION",
            "Target": "TARGET",
        }
        
        METHOD_MAP = {
            "Trim Mean": "trimmean",
            "Median": "median",
            "Average": "average",
        }
        
        for row in final_analysis_table:

            analysis_tenure = TENURE_MAP.get(row.get("Analysis Tenure"))
            method_name = row.get("Method")
        
            method = METHOD_MAP.get(method_name) if method_name else None
        
            recommendation = row.get("Recommendation")
            target_price_entry = row.get("Target Price for Entry")
            average_tenure = row.get("Average Tenure-wise")
            
            stock_bulk = []

            for row in final_analysis_table:
                stock_bulk.append(
                    StockAnalysis(
                        company_id=company_id,
                        analysis_tenure=TENURE_MAP.get(row.get("Analysis Tenure")),
                        method=METHOD_MAP.get(row.get("Method")) if row.get("Method") else None,
                        recommendation=row.get("Recommendation"),
                        target_price_entry=row.get("Target Price for Entry"),
                        average_tenure=row.get("Average Tenure-wise"),
                    )
                )
            
            StockAnalysis.objects.bulk_create(stock_bulk)

 
        # ---------------- SUMMARY CONDITIONS ------------------------
        def pos_neg(condition):
            return "Positive" if condition else "Negative"
        
        def under_over(condition):
            return "Undervalued" if condition else "Overvalued"
        
        
        # ---------------- 1. Valuation ------------------------------
        valuation_status = "Data not available"
        
        if (
            share_price is not None
            and median_target_price_entry is not None
            and mcap_data
            and mcap_data.stock_pe is not None
            and mcap_data.industry_pe is not None
        ):
            valuation_status = under_over(
                share_price < median_target_price_entry
                and mcap_data.stock_pe < mcap_data.industry_pe
            )

        # ---------------- 2. Value Analysis Conclusion ---------------
        value_analysis_conclusion_status = pos_neg(
            conclusion_recommendation == "Recommended to buy at current stock price"
        )
 
        # ---------------- 3. Target Price for Entry ------------------
        target_price_entry_status = "Data not available"
        
        if share_price is not None and median_target_price_entry is not None:
            target_price_entry_status = pos_neg(
                share_price < median_target_price_entry
            )

        # ---------------- 4. Stock PE vs Industry PE -----------------
        pe_comparison_status = "Data not available"
        
        if mcap_data and mcap_data.stock_pe and mcap_data.industry_pe:
            pe_comparison_status = pos_neg(
                mcap_data.stock_pe < mcap_data.industry_pe
            )

        # ---------------- 5–9. Growth Conditions ---------------------
        GROWTH_THRESHOLDS = {
    "Sales": 15,   # Sales, EPS, ROC => threshold 15%
    "EPS": 15,
    "ROC": 15,
    "OPM": 5,      # OPM, NPM => threshold 5%
    "NPM": 5,
}

        def pos_neg(condition):
            return "Positive" if condition else "Negative"
        
        growth_conditions = {}
        
        for row in growth_summary:
            metric = row.get("parameter")
            if metric not in GROWTH_THRESHOLDS:
                continue
        
            threshold = GROWTH_THRESHOLDS[metric]
            total_avg = row.get("total_average", {})
        
            def build_growth_obj(val):
                # Compare the pct value (val*100) against threshold
                return {
                    "status": pos_neg(val is not None and val * 100 > threshold),
                    "value": round(val * 100, 2) if val is not None else None  # optional
                }
        
            growth_conditions[metric] = {
                "trimmean": build_growth_obj(total_avg.get("trimmean")),
                "median": build_growth_obj(total_avg.get("median")),
                "average": build_growth_obj(total_avg.get("average")),
            }
        
        # ---------------- FINAL SUMMARY OBJECT -----------------------
        summary_conditions = {
                "valuation": valuation_status,
            
                "value_analysis_conclusion": value_analysis_conclusion_status,
            
                "target_price_for_entry": {
                    "status": target_price_entry_status,
                    "value": float(median_target_price_entry)
                    if median_target_price_entry is not None else None
                },
            
                "stock_pe_vs_industry_pe": pe_comparison_status,
            
                "growth_analysis": {
                    "sales_growth": growth_conditions.get("Sales"),
                    "opm_growth": growth_conditions.get("OPM"),
                    "npm_growth": growth_conditions.get("NPM"),
                    "eps_growth": growth_conditions.get("EPS"),
                    "roc_growth": growth_conditions.get("ROC"),
                }
            }
                   
        PARAMETER_MAP = {
            "valuation": "VALUATION",
            "value_analysis_conclusion": "VALUATION_CONCLUSION",
            "target_price_for_entry": "TARGET_ENTRY",
            "stock_pe_vs_industry_pe": "PE_COMPARISON",
            "Sales": "SALES",
            "OPM": "OPM",
            "NPM": "NPM",
            "EPS": "EPS",
            "ROC": "ROC",
        }

        summary_bulk = [
            Summary(company_id=company_id, parameter="VALUATION", result=valuation_status),
            Summary(company_id=company_id, parameter="VALUATION_CONCLUSION", result=value_analysis_conclusion_status),
            Summary(company_id=company_id, parameter="TARGET_ENTRY", result=target_price_entry_status),
            Summary(company_id=company_id, parameter="PE_COMPARISON", result=pe_comparison_status),
        ]
        for metric, values in growth_conditions.items():
            summary_bulk.append(
                Summary(
                    company_id=company_id,
                    parameter=PARAMETER_MAP[metric],
                    trimmean=values["trimmean"]["status"],
                    median=values["median"]["status"],
                    average=values["average"]["status"],
                )
            )
        
        Summary.objects.bulk_create(summary_bulk)

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
                "growth_summary": growth_summary,   # ✅ NEW TABLE
                "final_analysis_table": final_analysis_table,
            }
