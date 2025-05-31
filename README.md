# Electricity Data Insights Platform

A comprehensive platform for storing, querying, and visualizing electricity market and operational data.

## Overview

This platform provides insights into electricity market data, including IEX (Indian Electricity Exchange) market prices, volume, demand, and generation data. It features a powerful AI assistant that understands natural language queries about the data.

## Features

- **Data Storage**: Store electricity market and operational data with 15-minute granularity
- **Data Visualization**: Charts for market prices, demand, and generation
- **RESTful API**: Query data via well-defined endpoints
- **AI Assistant**: Natural language queries for data insights
- **CSV Import**: Upload data via CSV files

## Setup Instructions

### Prerequisites

- Python 3.8+
- Django 3.2+
- Pandas, NumPy, and other dependencies (see requirements.txt)

### Installation

1. Clone the repository
```bash
git clone https://github.com/saurabh12nxf/data-insights.git
cd data-insights-platform
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Run migrations
```bash
python manage.py migrate
```

5. Start the development server
```bash
python manage.py runserver
```

6. Access the platform at http://127.0.0.1:8000/

## Data Import

You can import data via CSV files. The platform accepts CSV files with the following formats:

### IEX Market Data

```csv
product,purchasebids,sellbids,mcv,mcp,timestamp
DAM,1200,1100,1050,4.32,2024-05-29T00:00:00
RTM,900,850,800,3.90,2024-05-29T00:15:00
```

- **product**: DAM or RTM
- **purchasebids**: Purchase bids in MW
- **sellbids**: Sell bids in MW
- **mcv**: Market Cleared Volume in MW
- **mcp**: Market Cleared Price in Rs/MWh
- **timestamp**: ISO format timestamp (YYYY-MM-DDThh:mm:ss)

## API Endpoints

The platform provides the following API endpoints:

### Market Data

- **GET** `/api/market-data/?product=DAM&start=2024-05-01&end=2024-05-31`
  - Returns market data for the specified product and date range

### Weighted Average Price

- **GET** `/api/weighted-average-mcp/?product=DAM&start=2024-05-01&end=2024-05-31`
  - Returns weighted average price (weighted by volume) for the specified product and date range

### Total Demand

- **GET** `/api/total-demand/?date=2024-05-29`
  - Returns total demand and hourly breakdown for the specified date

### Generator Data

- **GET** `/api/generator-data/?date=2024-05-29&generator=DAM`
  - Returns generation data for the specified date and generator

## AI Assistant

The platform includes an AI assistant that can understand natural language queries about the data. Examples include:

- "What is the weighted average price for DAM last week?"
- "Show me the demand for May 29, 2024"
- "What was the generation data for RTM yesterday?"
- "What's the trend for DAM prices between May 1 and May 31?"
- "How much volume was traded for RTM on May 29?"

### Supported Query Types

1. **Price Queries**
   - Information about market prices
   - Example: "What was the average price for DAM yesterday?"

2. **Weighted Average Queries**
   - Weighted average price calculations (weighted by volume)
   - Example: "What is the weighted average price for RTM last month?"

3. **Volume Queries**
   - Information about trading volumes
   - Example: "How much volume was traded for DAM last week?"

4. **Demand Queries**
   - Information about electricity demand
   - Example: "What was the total demand on May 29?"

5. **Generation Queries**
   - Information about electricity generation
   - Example: "Show me the generation data for RTM yesterday"

6. **Trend Analysis**
   - Analysis of price and volume trends
   - Example: "What's the trend for DAM prices this month?"

### Date Terminology

The assistant understands various date terms:

- **Specific dates**: "May 29, 2024"
- **Relative dates**: "yesterday", "last week", "last month", "this month", "this year"
- **Date ranges**: "between May 1 and May 31"

## Charts and Visualizations

The platform provides the following visualizations:

1. **Market Price Trends**: Line chart showing price trends over time
2. **Market Volume Trends**: Bar chart showing volume by product
3. **Blockwise Demand**: Bar chart showing demand by hour for a specific date
4. **Blockwise Generation**: Bar chart showing generation by hour for a specific generator and date

## Extending the Platform

### Adding New Data Sources

To add a new data source:

1. Create a new model in `data_app/models.py`
2. Create a serializer in `data_app/serializers.py`
3. Add API endpoints in `data_app/views.py`
4. Add visualizations in `data_app/templates/dashboard.html`

### Enhancing the AI Assistant

To enhance the AI assistant:

1. Add new query types in the prompt in `data_app/views.py`
2. Add corresponding handlers in the AI assistant function
3. Update the frontend to display the new types of responses

## License

This project is licensed under the MIT License - see the LICENSE file for details.
