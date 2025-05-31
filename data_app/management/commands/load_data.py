import pandas as pd
from django.core.management.base import BaseCommand
from data_app.models import IEXMarketData

class Command(BaseCommand):
    help = 'Load IEX market data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        df = pd.read_csv(csv_file)
        for _, row in df.iterrows():
            IEXMarketData.objects.create(
                product=row['Product'],
                mcv=row['MCV'],
                mcp=row['MCP'],
                timestamp=row['Timestamp']
            )
        self.stdout.write(self.style.SUCCESS('Data loaded successfully.'))