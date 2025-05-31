from django.urls import path
from . import views
from . import api_views
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
      path('api/market-data/', api_views.get_market_data, name='get_market_data'),
    path('api/average-mcp/', api_views.get_avg_price, name='get_avg_price'),
     path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
]