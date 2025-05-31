from django.test import TestCase, Client
from django.urls import reverse
from .models import IEXMarketData
from datetime import datetime
import json

class IEXMarketDataModelTests(TestCase):
    def setUp(self):
        # Create test data
        IEXMarketData.objects.create(
            product="DAM",
            purchase_bids=1200,
            sell_bids=1100,
            mcv=1050,
            mcp=4.32,
            timestamp="2024-05-29T00:00:00"
        )
        IEXMarketData.objects.create(
            product="RTM",
            purchase_bids=900,
            sell_bids=850,
            mcv=800,
            mcp=3.90,
            timestamp="2024-05-29T00:15:00"
        )

    def test_market_data_creation(self):
        """Test that market data objects are created correctly"""
        dam_data = IEXMarketData.objects.get(product="DAM")
        rtm_data = IEXMarketData.objects.get(product="RTM")
        
        self.assertEqual(dam_data.mcp, 4.32)
        self.assertEqual(rtm_data.mcv, 800)
        self.assertEqual(dam_data.purchase_bids, 1200)
        self.assertEqual(rtm_data.sell_bids, 850)

class DashboardViewTests(TestCase):
    def setUp(self):
        # Create test data
        IEXMarketData.objects.create(
            product="DAM",
            purchase_bids=1200,
            sell_bids=1100,
            mcv=1050,
            mcp=4.32,
            timestamp="2024-05-29T00:00:00"
        )
        self.client = Client()

    def test_dashboard_view(self):
        """Test that dashboard view loads correctly"""
        response = self.client.get(reverse('dashboard'))  # Assuming you have a 'dashboard' URL name
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Electricity Data Dashboard")
        self.assertContains(response, "Latest IEX Market Data")

class APIEndpointTests(TestCase):
    def setUp(self):
        # Create test data
        IEXMarketData.objects.create(
            product="DAM",
            purchase_bids=1200,
            sell_bids=1100,
            mcv=1050,
            mcp=4.32,
            timestamp="2024-05-29T00:00:00"
        )
        IEXMarketData.objects.create(
            product="DAM",
            purchase_bids=1100,
            sell_bids=1000,
            mcv=950,
            mcp=4.50,
            timestamp="2024-05-29T00:15:00"
        )
        self.client = Client()

    def test_weighted_avg_price_endpoint(self):
        """Test the weighted average price API endpoint"""
        response = self.client.get(
            reverse('get_weighted_avg_price'),  # Assuming you have this URL name
            {'product': 'DAM', 'start': '2024-05-29', 'end': '2024-05-29'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Calculate expected weighted average: (4.32*1050 + 4.50*950)/(1050+950) ≈ 4.406
        expected_weighted_avg = (4.32*1050 + 4.50*950) / (1050 + 950)
        self.assertAlmostEqual(data['weighted_average_mcp'], expected_weighted_avg, places=2)
        
    def test_total_demand_endpoint(self):
        """Test the total demand API endpoint"""
        response = self.client.get(
            reverse('get_total_demand'),  # Assuming you have this URL name
            {'date': '2024-05-29'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Expected total demand is sum of MCVs: 1050 + 950 = 2000
        self.assertEqual(data['total_demand'], 2000)
        
    def test_generator_data_endpoint(self):
        """Test the generator data API endpoint"""
        response = self.client.get(
            reverse('get_generator_data'),  # Assuming you have this URL name
            {'date': '2024-05-29', 'generator': 'DAM'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Expected total generation for DAM is sum of MCVs: 1050 + 950 = 2000
        self.assertEqual(data['total_generation'], 2000)
        self.assertEqual(data['selected_generator'], 'DAM')
        
class AIAssistantTests(TestCase):
    def setUp(self):
        # Create test data
        IEXMarketData.objects.create(
            product="DAM",
            purchase_bids=1200,
            sell_bids=1100,
            mcv=1050,
            mcp=4.32,
            timestamp="2024-05-29T00:00:00"
        )
        self.client = Client()

    def test_ai_assistant_endpoint(self):
        """Test the AI assistant endpoint with a basic price query"""
        # Note: This test may need modification if you're using an external AI service
        # as it might be mocked in testing environments
        response = self.client.post(
            reverse('ai_assistant'),  # Assuming you have this URL name
            json.dumps({'question': 'What is the price for DAM on May 29, 2024?'}),
            content_type='application/json'
        )
        
        # We might just check that it returns a 200 response
        # since the actual AI processing might be mocked
        self.assertEqual(response.status_code, 200) 