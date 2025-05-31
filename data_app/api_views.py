from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import IEXMarketData
from .serializers import IEXMarketDataSerializer
from django.db.models import Avg

@api_view(['GET'])
def get_market_data(request):
    product = request.GET.get('product')
    start = request.GET.get('start')
    end = request.GET.get('end')

    queryset = IEXMarketData.objects.all()
    if product:
        queryset = queryset.filter(product=product)
    if start and end:
        queryset = queryset.filter(timestamp__range=[start, end])

    serializer = IEXMarketDataSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_avg_price(request):
    product = request.GET.get('product')
    start = request.GET.get('start')
    end = request.GET.get('end')

    queryset = IEXMarketData.objects.all()
    if product:
        queryset = queryset.filter(product=product)
    if start and end:
        queryset = queryset.filter(timestamp__range=[start, end])

    avg_price = queryset.aggregate(avg_price=Avg('mcp'))['avg_price']
    return Response({'product': product, 'average_mcp': avg_price})
