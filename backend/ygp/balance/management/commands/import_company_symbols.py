import pandas as pd
from django.core.management.base import BaseCommand
from balance.models import CompanySymbol

class Command(BaseCommand):
    help = "Import company symbols from Excel file"

    def add_arguments(self, parser):
        parser.add_argument("excel_file", type=str, help="Path to the Excel file")

    def handle(self, *args, **kwargs):
        file_path = kwargs["excel_file"]
        
        # Explicitly read "Sheet1"
        df = pd.read_excel(file_path, sheet_name="Sheet1")

        for _, row in df.iterrows():
            CompanySymbol.objects.create(
                name=row["Screener File name"],
                symbol=row["SYMBOL"],
                
            )

        self.stdout.write(self.style.SUCCESS("Company symbols imported successfully!"))
