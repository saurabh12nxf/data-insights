from django.contrib import admin
from .models import IEXMarketData, LoadData, GenerationData

admin.site.register(IEXMarketData)
admin.site.register(LoadData)
admin.site.register(GenerationData)

