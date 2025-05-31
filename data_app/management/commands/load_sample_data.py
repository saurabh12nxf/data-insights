from django.core.management.base import BaseCommand
from data_app.models import IEXMarketData
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Loads sample data for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Number of days of data to generate')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before loading')

    def handle(self, *args, **options):
        days = options['days']
        clear = options['clear']
        
        # Clear existing data if requested
        if clear:
            IEXMarketData.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))
        
        # Generate sample data
        today = datetime.now().date()
        products = ["DAM", "RTM"]
        blocks_per_day = 96  # 15-minute blocks in a day
        
        total_records = 0
        for day_offset in range(days):
            current_date = today - timedelta(days=day_offset)
            
            for product in products:
                # Base values that will fluctuate throughout the day
                base_mcv = 1000 if product == "DAM" else 800
                base_mcp = 4.0 if product == "DAM" else 3.5
                base_purchase_bids = base_mcv * 1.2
                base_sell_bids = base_mcv * 1.1
                
                for block in range(blocks_per_day):
                    # Calculate time for this block
                    block_hour = block // 4
                    block_minute = (block % 4) * 15
                    timestamp = datetime.combine(
                        current_date, 
                        datetime.min.time()
                    ).replace(hour=block_hour, minute=block_minute)
                    
                    # Add time-based patterns to make data more realistic
                    time_factor = 1.0
                    # Morning peak (7-10 AM)
                    if 7 <= block_hour <= 10:
                        time_factor = 1.3
                    # Evening peak (6-9 PM)
                    elif 18 <= block_hour <= 21:
                        time_factor = 1.5
                    # Night low (11 PM - 5 AM)
                    elif block_hour >= 23 or block_hour <= 5:
                        time_factor = 0.7
                    
                    # Add some randomness
                    random_factor = random.uniform(0.9, 1.1)
                    
                    # Calculate values for this block
                    mcv = int(base_mcv * time_factor * random_factor)
                    mcp = round(base_mcp * time_factor * random_factor, 2)
                    purchase_bids = int(base_purchase_bids * time_factor * random_factor)
                    sell_bids = int(base_sell_bids * time_factor * random_factor)
                    
                    # Create record
                    IEXMarketData.objects.create(
                        product=product,
                        purchase_bids=purchase_bids,
                        sell_bids=sell_bids,
                        mcv=mcv,
                        mcp=mcp,
                        timestamp=timestamp
                    )
                    total_records += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded {total_records} records for {days} days'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Date range: {(today - timedelta(days=days-1)).strftime("%Y-%m-%d")} to {today.strftime("%Y-%m-%d")}'
        )) 