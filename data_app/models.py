from django.db import models

class IEXMarketData(models.Model):
    product = models.CharField(max_length=10)  # DAM or RTM
    purchase_bids = models.FloatField()  # Total purchase bids (MW)
    sell_bids = models.FloatField()      # Total sell bids (MW)
    mcv = models.FloatField()            # Market Cleared Volume (MW)
    mcp = models.FloatField()            # Market Cleared Price (Rs/MWh)
    timestamp = models.DateTimeField()   # 15-min interval timestamp

class LoadData(models.Model):
    block = models.IntegerField()        # 15-min block number (1-96)
    value = models.FloatField()          # Drawal value (MW)
    date = models.DateField()            # Date of the record

class GenerationData(models.Model):
    generator = models.CharField(max_length=100)  # Generator name
    block = models.IntegerField()                 # 15-min block number (1-96)
    value = models.FloatField()                   # Generation value (MW)
    date = models.DateField()                     # Date of the record   