from django.urls import path
from . import views
from . import api_views
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/market-data/', api_views.get_market_data, name='get_market_data'),
    path('api/average-mcp/', api_views.get_avg_price, name='get_avg_price'),
    path('api/load-data/', api_views.get_load_data, name='get_load_data'),
    path('api/generation-data/', api_views.get_generation_data, name='get_generation_data'),
    path('api/weighted-average-mcp/', views.get_weighted_avg_price, name='get_weighted_avg_price'),
    path('api/total-demand/', views.get_total_demand, name='get_total_demand'),
    path('api/generator-data/', views.get_generator_data, name='get_generator_data'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
]