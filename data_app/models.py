from django.db import models

class IEXMarketData(models.Model):
    product = models.CharField(max_length=10)  # DAM or RTM
    mcv = models.FloatField()  # Market Cleared Volume
    mcp = models.FloatField()  # Market Cleared Price
    timestamp = models.DateTimeField()

class LoadData(models.Model):
    block = models.IntegerField()
    value = models.FloatField()
    date = models.DateField()

class GenerationData(models.Model):
    generator = models.CharField(max_length=100)
    block = models.IntegerField()
    value = models.FloatField()
    date = models.DateField()