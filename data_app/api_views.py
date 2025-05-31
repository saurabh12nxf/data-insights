from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Avg
from datetime import datetime
from .models import IEXMarketData, LoadData, GenerationData
from .serializers import IEXMarketDataSerializer, LoadDataSerializer, GenerationDataSerializer

@api_view(['GET'])
def get_market_data(request):
    product = request.GET.get('product')
    start = request.GET.get('start')
    end = request.GET.get('end')

    queryset = IEXMarketData.objects.all()
    if product:
        queryset = queryset.filter(product=product)
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

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
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    avg_price = queryset.aggregate(avg_price=Avg('mcp'))['avg_price']
    return Response({
        'product': product,
        'start': start,
        'end': end,
        'average_mcp': avg_price
    })

@api_view(['GET'])
def get_load_data(request):
    date = request.GET.get('date')
    if not date:
        return Response({'error': 'Missing date parameter'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    queryset = LoadData.objects.filter(date=date_obj)
    serializer = LoadDataSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_generation_data(request):
    date = request.GET.get('date')
    generator = request.GET.get('generator')

    if not date:
        return Response({'error': 'Missing date parameter'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    queryset = GenerationData.objects.filter(date=date_obj)
    if generator:
        queryset = queryset.filter(generator=generator)

    serializer = GenerationDataSerializer(queryset, many=True)
    return Response(serializer.data)
