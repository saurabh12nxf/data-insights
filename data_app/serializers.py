from rest_framework import serializers
from .models import IEXMarketData, LoadData, GenerationData

class IEXMarketDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = IEXMarketData
        fields = '__all__'

class LoadDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadData
        fields = '__all__'

class GenerationDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationData
        fields = '__all__'
    