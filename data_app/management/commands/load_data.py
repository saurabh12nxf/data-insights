import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from data_app.models import IEXMarketData, LoadData, GenerationData
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Load data from CSV file into IEXMarketData, LoadData, or GenerationData.'

    def add_arguments(self, parser):
        parser.add_argument('model', type=str, help="Model to load: 'iex', 'load', or 'generation'")
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        model = kwargs['model'].lower()
        csv_file = kwargs['csv_file']
        df = pd.read_csv(csv_file)

        if model == 'iex':
            required_cols = ['Product', 'PurchaseBids', 'SellBids', 'MCV', 'MCP', 'Timestamp']
            for col in required_cols:
                if col not in df.columns:
                    raise CommandError(f"Missing required column: {col}")
            for _, row in df.iterrows():
                IEXMarketData.objects.create(
                    product=row['Product'],
                    purchase_bids=row['PurchaseBids'],
                    sell_bids=row['SellBids'],
                    mcv=row['MCV'],
                    mcp=row['MCP'],
                    timestamp=parse_datetime(str(row['Timestamp']))
                )
            self.stdout.write(self.style.SUCCESS('IEXMarketData loaded successfully.'))

        elif model == 'load':
            required_cols = ['Block', 'Value', 'Date']
            for col in required_cols:
                if col not in df.columns:
                    raise CommandError(f"Missing required column: {col}")
            for _, row in df.iterrows():
                LoadData.objects.create(
                    block=row['Block'],
                    value=row['Value'],
                    date=row['Date']
                )
            self.stdout.write(self.style.SUCCESS('LoadData loaded successfully.'))

        elif model == 'generation':
            required_cols = ['Generator', 'Block', 'Value', 'Date']
            for col in required_cols:
                if col not in df.columns:
                    raise CommandError(f"Missing required column: {col}")
            for _, row in df.iterrows():
                GenerationData.objects.create(
                    generator=row['Generator'],
                    block=row['Block'],
                    value=row['Value'],
                    date=row['Date']
                )
            self.stdout.write(self.style.SUCCESS('GenerationData loaded successfully.'))

        else:
            raise CommandError("Model must be one of: 'iex', 'load', 'generation'")