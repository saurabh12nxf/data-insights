from django.shortcuts import render
from .models import IEXMarketData
import pandas as pd
from .forms import UploadFileForm
from django.db.models import Avg, Sum, F
import io, os, json, requests, re
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def dashboard(request):
    message = ""

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            try:
                content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError:
                content = uploaded_file.read().decode('latin1')

            try:
                df = pd.read_csv(io.StringIO(content))
                df.columns = df.columns.str.strip().str.lower()
                df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

                # Check if required columns exist
                required_columns = ['product', 'mcv', 'mcp', 'timestamp', 'purchasebids', 'sellbids']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

                # Count records and gather info before saving
                record_count = 0
                products = set()
                min_date = None
                max_date = None

                for _, row in df.iterrows():
                    # Convert timestamp to datetime for comparison
                    try:
                        timestamp = pd.to_datetime(row['timestamp'])
                        if min_date is None or timestamp < min_date:
                            min_date = timestamp
                        if max_date is None or timestamp > max_date:
                            max_date = timestamp
                    except:
                        pass  # Skip timestamp validation if format is wrong
                    
                    # Track unique products
                    products.add(row['product'])
                    
                    # Create the database record
                    IEXMarketData.objects.create(
                        product=row['product'],
                        purchase_bids=row['purchasebids'],
                        sell_bids=row['sellbids'],
                        mcv=row['mcv'],
                        mcp=row['mcp'],
                        timestamp=row['timestamp']
                    )
                    record_count += 1

                # Format detailed success message
                message = f"Data uploaded successfully. {record_count} records imported for {', '.join(products)}."
                if min_date and max_date:
                    message += f" Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}."
            except Exception as e:
                message = f"Error processing CSV: {str(e)}"
        else:
            message = "Invalid form submission."
    else:
        form = UploadFileForm()

    # Get latest data
    data = IEXMarketData.objects.all().order_by('-timestamp')[:10]
    
    # Explicitly create data dictionary for template to ensure all fields are available
    formatted_data = []
    for item in data:
        formatted_data.append({
            'product': item.product,
            'purchase_bids': item.purchase_bids,
            'sell_bids': item.sell_bids,
            'mcv': item.mcv,
            'mcp': item.mcp,
            'timestamp': item.timestamp
        })

    # Aggregations
    avg_prices = list(IEXMarketData.objects.values('product').annotate(avg_price=Avg('mcp')))
    total_volumes = list(IEXMarketData.objects.values('product').annotate(total_volume=Sum('mcv')))

    # Get recent data for charts (last 7 days)
    recent_date = now() - timedelta(days=7)
    recent_volumes = list(IEXMarketData.objects.filter(timestamp__gte=recent_date)
                          .values('product').annotate(total_volume=Sum('mcv')))
    
    # If no recent data, use data from 2024 onwards to ensure we have something to show
    if not recent_volumes:
        # Filter for data from 2024 onwards
        recent_volumes = list(IEXMarketData.objects.filter(timestamp__year__gte=2024)
                            .values('product').annotate(total_volume=Sum('mcv')))

    # Chart data
    # Limit to 50 most recent entries for better visualization
    chart_data_qs = IEXMarketData.objects.all().order_by('-timestamp')[:50]
    
    # Sort chronologically for the chart
    chart_data_qs = sorted(chart_data_qs, key=lambda x: x.timestamp)

    mcp_chart_data = [
        {
            'timestamp': entry.timestamp.isoformat(),
            'mcp': entry.mcp,
            'product': entry.product
        } for entry in chart_data_qs
    ]

    return render(request, 'dashboard.html', {
        'form': form,
        'data': formatted_data,
        'message': message,
        'avg_prices': avg_prices,
        'total_volumes': total_volumes,
        'recent_volumes': recent_volumes,
        'mcp_chart_data': mcp_chart_data,
        'openai_enabled': True
    })


@csrf_exempt
def ai_assistant(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

    try:
        data = json.loads(request.body)
        user_question = data.get('question', '')

        # Special case handling for common questions
        try:
            # Case 1: Weighted average price for last week
            if ("weighted average price" in user_question.lower() or "weighted avg" in user_question.lower()) and "last week" in user_question.lower():
                try:
                    # Create a direct response for this common case
                    today = datetime.now().date()
                    end_date = today - timedelta(days=1)  # Yesterday
                    start_date = end_date - timedelta(days=6)  # 7 days including yesterday
                    
                    start = start_date.strftime("%Y-%m-%d")
                    end = end_date.strftime("%Y-%m-%d")
                    
                    # Determine product
                    product = None
                    if "dam" in user_question.lower():
                        product = "DAM"
                    elif "rtm" in user_question.lower():
                        product = "RTM"
                    
                    # Get the data directly
                    queryset = IEXMarketData.objects.all()
                    if product:
                        queryset = queryset.filter(product=product)
                    
                    # Filter by date range
                    start_date_obj = datetime.strptime(start, "%Y-%m-%d")
                    end_date_obj = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date_obj, timestamp__lt=end_date_obj)
                    
                    # Calculate weighted average
                    result = queryset.aggregate(
                        weighted_value=Sum(F('mcp') * F('mcv')),
                        total_volume=Sum('mcv')
                    )
                    
                    weighted_avg = None
                    if result['total_volume'] and result['total_volume'] > 0:
                        weighted_avg = result['weighted_value'] / result['total_volume']
                    
                    # Format response
                    product_str = f" for {product}" if product else ""
                    date_range = f" between {start} and {end}"
                    message = f"The weighted average price{product_str}{date_range} was {round(weighted_avg, 2) if weighted_avg else 'N/A'} Rs/MWh."
                    
                    return JsonResponse({
                        'question': user_question,
                        'weighted_average_mcp': weighted_avg,
                        'total_volume': result['total_volume'],
                        'start': start,
                        'end': end,
                        'product': product,
                        'message': message
                    })
                except Exception as e:
                    print(f"Error in weighted average handler: {str(e)}")
            
            # Case 2: Price for yesterday
            elif "price" in user_question.lower() and "yesterday" in user_question.lower():
                try:
                    today = datetime.now().date()
                    yesterday = today - timedelta(days=1)
                    date_str = yesterday.strftime("%Y-%m-%d")
                    
                    # Determine product
                    product = None
                    if "dam" in user_question.lower():
                        product = "DAM"
                    elif "rtm" in user_question.lower():
                        product = "RTM"
                    
                    # Get the data directly
                    queryset = IEXMarketData.objects.all()
                    if product:
                        queryset = queryset.filter(product=product)
                    
                    # Filter by date
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    queryset = queryset.filter(timestamp__date=date_obj)
                    
                    # Calculate average price
                    avg_price = queryset.aggregate(avg_price=Avg('mcp'))['avg_price']
                    
                    # Format response
                    product_str = f" for {product}" if product else ""
                    message = f"The average price{product_str} yesterday ({date_str}) was {round(avg_price, 2) if avg_price else 'N/A'} Rs/MWh."
                    
                    return JsonResponse({
                        'question': user_question,
                        'average_mcp': avg_price,
                        'date': date_str,
                        'product': product,
                        'message': message
                    })
                except Exception as e:
                    print(f"Error in price for yesterday handler: {str(e)}")
                
            # Case 3: Generation data for yesterday
            elif "generation" in user_question.lower() and "yesterday" in user_question.lower():
                try:
                    today = datetime.now().date()
                    yesterday = today - timedelta(days=1)
                    date_str = yesterday.strftime("%Y-%m-%d")
                    
                    # Determine product/generator
                    product = None
                    if "dam" in user_question.lower():
                        product = "DAM"
                    elif "rtm" in user_question.lower():
                        product = "RTM"
                    
                    # Get the data directly
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
                    
                    if product:
                        queryset = queryset.filter(product=product)
                        
                    total_generation = queryset.aggregate(total=Sum('mcv'))['total'] or 0
                    
                    hourly_generation = list(queryset
                        .extra(select={'hour': "strftime('%%H', timestamp)"})
                        .values('hour', 'product')
                        .annotate(generation=Sum('mcv'))
                        .order_by('hour', 'product'))
                    
                    generators = queryset.values_list('product', flat=True).distinct()
                    
                    # Format response
                    product_str = f" for {product}" if product else ""
                    message = f"The total generation{product_str} for yesterday ({date_str}) was {round(total_generation, 2)} MW."
                    
                    return JsonResponse({
                        'question': user_question,
                        'date': date_str,
                        'generators': list(generators),
                        'selected_generator': product,
                        'total_generation': total_generation,
                        'hourly_generation': hourly_generation,
                        'message': message
                    })
                except Exception as e:
                    print(f"Error in generation data handler: {str(e)}")
                    return JsonResponse({
                        'error': 'Error processing generation data',
                        'details': str(e)
                    }, status=500)
                
            # Case 4: Demand for a specific date
            elif "demand" in user_question.lower() and any(term in user_question.lower() for term in ["yesterday", "today", "for"]):
                try:
                    date_str = None
                    
                    if "yesterday" in user_question.lower():
                        today = datetime.now().date()
                        yesterday = today - timedelta(days=1)
                        date_str = yesterday.strftime("%Y-%m-%d")
                    else:
                        # Try to extract a date from the question using safe pattern matching
                        date_match = None
                        question_lower = user_question.lower()
                        
                        # Look for specific date formats
                        import re
                        try:
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', question_lower)
                            if date_match:
                                date_str = date_match.group(1)
                        except:
                            date_str = None
                    
                    if date_str:
                        try:
                            # Get the data directly
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                            queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
                            
                            total_demand = queryset.aggregate(total=Sum('mcv'))['total'] or 0
                            
                            hourly_demand = list(queryset
                                .extra(select={'hour': "strftime('%%H', timestamp)"})
                                .values('hour')
                                .annotate(demand=Sum('mcv'))
                                .order_by('hour'))
                            
                            # Format response
                            message = f"The total demand for {date_str} was {round(total_demand, 2)} MW."
                            
                            return JsonResponse({
                                'question': user_question,
                                'date': date_str,
                                'total_demand': total_demand,
                                'hourly_demand': hourly_demand,
                                'message': message
                            })
                        except Exception as e:
                            return JsonResponse({
                                'error': f"Error processing date: {str(e)}",
                                'date_attempted': date_str
                            }, status=400)
                except Exception as e:
                    print(f"Error in demand handler: {str(e)}")
                    return JsonResponse({
                        'error': 'Error processing demand data',
                        'details': str(e)
                    }, status=500)
            
            # Case 5: Trend analysis between specific dates
            elif "trend" in user_question.lower() and "between" in user_question.lower():
                try:
                    # Extract product
                    product = None
                    if "dam" in user_question.lower():
                        product = "DAM"
                    elif "rtm" in user_question.lower():
                        product = "RTM"
                    
                    # Attempt to extract dates for May 1 and May 31
                    start_str = None
                    end_str = None
                    
                    # Handle specific case for May 1 and May 31
                    if "may 1" in user_question.lower() and "may 31" in user_question.lower():
                        # Use the current year or a specific year if mentioned
                        year = datetime.now().year
                        if "2024" in user_question:
                            year = 2024
                        elif "2023" in user_question:
                            year = 2023
                        
                        start_str = f"{year}-05-01"
                        end_str = f"{year}-05-31"
                    
                    if start_str and end_str:
                        # Get the data for trend analysis
                        start_date = datetime.strptime(start_str, "%Y-%m-%d")
                        end_date = datetime.strptime(end_str, "%Y-%m-%d") + timedelta(days=1)
                        
                        queryset = IEXMarketData.objects.all()
                        if product:
                            queryset = queryset.filter(product=product)
                        
                        queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                        
                        # Group by day for trend analysis
                        daily_data = list(queryset
                            .extra(select={'day': "date(timestamp)"})
                            .values('day')
                            .annotate(
                                avg_price=Avg('mcp'),
                                avg_volume=Avg('mcv'),
                                total_volume=Sum('mcv')
                            )
                            .order_by('day'))
                        
                        # Calculate trend indicators
                        price_change = None
                        price_change_pct = None
                        volume_change = None
                        volume_change_pct = None
                        
                        if len(daily_data) > 1:
                            first_day = daily_data[0]
                            last_day = daily_data[-1]
                            
                            price_change = last_day['avg_price'] - first_day['avg_price']
                            price_change_pct = (price_change / first_day['avg_price']) * 100 if first_day['avg_price'] else 0
                            
                            volume_change = last_day['total_volume'] - first_day['total_volume']
                            volume_change_pct = (volume_change / first_day['total_volume']) * 100 if first_day['total_volume'] else 0
                        
                        # Format the response message
                        direction = "increased" if price_change_pct > 0 else "decreased"
                        product_str = f" for {product}" if product else ""
                        message = f"The price{product_str} {direction} by {abs(round(price_change_pct, 2))}% between {start_str} and {end_str}."
                        
                        return JsonResponse({
                            'question': user_question,
                            'start': start_str,
                            'end': end_str,
                            'product': product,
                            'trend_data': daily_data,
                            'price_change': price_change,
                            'price_change_pct': price_change_pct,
                            'volume_change': volume_change,
                            'volume_change_pct': volume_change_pct,
                            'message': message
                        })
                except Exception as e:
                    print(f"Error in trend analysis handler: {str(e)}")
                    return JsonResponse({
                        'error': 'Error processing trend data',
                        'details': str(e)
                    }, status=500)
            
            # Case 6: Volume query for a specific date
            elif ("volume" in user_question.lower() or "traded" in user_question.lower()) and "on" in user_question.lower():
                try:
                    # Extract product
                    product = None
                    if "dam" in user_question.lower():
                        product = "DAM"
                    elif "rtm" in user_question.lower():
                        product = "RTM"
                    
                    # Extract date - handle "May 29" format
                    date_str = None
                    
                    # Check for May 29 pattern
                    if "may 29" in user_question.lower():
                        # Use the current year or a specific year if mentioned
                        year = datetime.now().year
                        if "2024" in user_question:
                            year = 2024
                        elif "2023" in user_question:
                            year = 2023
                        
                        date_str = f"{year}-05-29"
                    
                    if date_str:
                        # Get the data directly
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
                        
                        if product:
                            queryset = queryset.filter(product=product)
                        
                        # Calculate total volume
                        total_volume = queryset.aggregate(total=Sum('mcv'))['total'] or 0
                        
                        # Format response
                        product_str = f" for {product}" if product else ""
                        date_display = date_obj.strftime("%B %d, %Y")  # Format as "May 29, 2024"
                        message = f"The total volume traded{product_str} on {date_display} was {round(total_volume, 2)} MW."
                        
                        # Get hourly breakdown
                        hourly_volume = list(queryset
                            .extra(select={'hour': "strftime('%%H', timestamp)"})
                            .values('hour')
                            .annotate(volume=Sum('mcv'))
                            .order_by('hour'))
                        
                        return JsonResponse({
                            'question': user_question,
                            'date': date_str,
                            'product': product,
                            'total_volume': total_volume,
                            'hourly_volume': hourly_volume,
                            'message': message
                        })
                except Exception as e:
                    print(f"Error in volume query handler: {str(e)}")
                    return JsonResponse({
                        'error': 'Error processing volume data',
                        'details': str(e)
                    }, status=500)
        except Exception as e:
            print(f"Error in special case handlers: {str(e)}")
            # Continue to the AI processing if special case handlers fail

        prompt = (
            f"You are a helpful electricity data insights assistant. Extract structured parameters from this question:\n"
            f"\"{user_question}\"\n"
            "Analyze the question to identify:\n"
            "1. Query type (one of: price, volume, demand, generation, trend, weighted_avg)\n"
            "2. Product/generator (e.g., DAM, RTM, or a specific generator name)\n"
            "3. Date range (start date and end date)\n"
            "4. Comparison flag (boolean: is user asking for a comparison?)\n"
            "5. Aggregation type (e.g., average, sum, min, max)\n\n"
            "Return your result strictly as a JSON object like this:\n"
            "{\n"
            "  \"query_type\": \"price\",\n"
            "  \"product\": \"RTM\",\n"
            "  \"start\": \"2024-01-01\",\n"
            "  \"end\": \"2024-01-07\",\n"
            "  \"comparison\": false,\n"
            "  \"aggregation\": \"average\"\n"
            "}\n"
            "If any value is missing, set it to null. Respond ONLY with valid JSON, nothing else."
        )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language."},
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )

        try:
            result = response.json()
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON from OpenRouter', 'text': response.text}, status=500)

        gpt_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        json_match = re.search(r'{.*}', gpt_text, re.DOTALL)

        if not json_match:
            return JsonResponse({'error': 'No valid JSON found in AI response', 'response': gpt_text}, status=400)

        gpt_json = json_match.group(0)
        try:
            params = json.loads(gpt_json)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Malformed JSON from AI', 'text': gpt_json}, status=400)

        query_type = params.get('query_type')
        product = params.get('product')
        start = params.get('start')
        end = params.get('end')
        comparison = params.get('comparison', False)
        aggregation = params.get('aggregation')

        # Initialize response data
        response_data = {
            'question': user_question,
            'parsed_params': params,
        }

        # Function to handle relative dates
        def process_relative_dates(query_text):
            today = datetime.now().date()
            start_date = None
            end_date = None
            
            if "yesterday" in query_text.lower():
                yesterday = today - timedelta(days=1)
                start_date = yesterday
                end_date = yesterday
            
            elif "last week" in query_text.lower():
                end_date = today - timedelta(days=1)  # Yesterday
                start_date = end_date - timedelta(days=6)  # 7 days including yesterday
            
            elif "last month" in query_text.lower():
                end_date = today - timedelta(days=1)  # Yesterday
                start_date = end_date - timedelta(days=29)  # 30 days including yesterday
            
            elif "this month" in query_text.lower():
                # First day of current month to yesterday
                start_date = today.replace(day=1)
                end_date = today - timedelta(days=1)
            
            elif "this year" in query_text.lower():
                # First day of current year to yesterday
                start_date = today.replace(month=1, day=1)
                end_date = today - timedelta(days=1)
            
            return start_date, end_date

        # Process relative dates in the question before handling query types
        # This needs to happen for all query types that might use date ranges
        if query_type in ['price', 'weighted_avg', 'volume', 'trend'] and (not start or not end):
            start_date, end_date = process_relative_dates(user_question)
            if start_date and end_date:
                start = start_date.strftime("%Y-%m-%d")
                end = end_date.strftime("%Y-%m-%d")
                # Update params for response context
                params['start'] = start
                params['end'] = end
        
        # For single-date queries like demand and generation
        elif query_type in ['demand', 'generation'] and not start:
            start_date, _ = process_relative_dates(user_question)
            if start_date:
                start = start_date.strftime("%Y-%m-%d")
                params['start'] = start

        # Verify that dates are properly formatted before using them
        def validate_date(date_str):
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            except (ValueError, TypeError):
                return False
        
        # Check start and end dates for validity
        if (start and not validate_date(start)) or (end and not validate_date(end)):
            error_msg = "Invalid date format detected. "
            error_details = {}
            
            if start and not validate_date(start):
                error_details['start'] = start
            if end and not validate_date(end):
                error_details['end'] = end
            
            error_msg += "Dates must be in YYYY-MM-DD format."
            
            return JsonResponse({
                'error': error_msg,
                'details': error_details,
                'processed_query': params
            }, status=400)
        
        # Handle different query types
        if query_type == 'price':
            # Get market price data
            queryset = IEXMarketData.objects.all()
            
            if product:
                queryset = queryset.filter(product=product)
            
            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d")
                    end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
            
            avg_price = queryset.aggregate(avg_price=Avg('mcp'))['avg_price']
            response_data['average_mcp'] = avg_price
            
            # Get the time series data for visualization
            time_series = list(queryset.values('timestamp', 'mcp', 'product').order_by('timestamp'))
            response_data['time_series'] = time_series
            
        elif query_type == 'weighted_avg':
            # Get weighted average price (weighted by volume)
            queryset = IEXMarketData.objects.all()
            
            if product:
                queryset = queryset.filter(product=product)
            
            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d")
                    end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
            
            result = queryset.aggregate(
                weighted_value=Sum(F('mcp') * F('mcv')),
                total_volume=Sum('mcv')
            )
            
            weighted_avg = None
            if result['total_volume'] and result['total_volume'] > 0:
                weighted_avg = result['weighted_value'] / result['total_volume']
            
            response_data['weighted_average_mcp'] = weighted_avg
            response_data['total_volume'] = result['total_volume']
            
        elif query_type == 'demand':
            # Get demand/load data
            if not start:
                # If no start date, assume user wants the most recent data
                latest = IEXMarketData.objects.all().order_by('-timestamp').first()
                if latest:
                    start = latest.timestamp.strftime("%Y-%m-%d")
            
            if start:
                try:
                    date_obj = datetime.strptime(start, "%Y-%m-%d").date()
                    queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
                    
                    if product:
                        queryset = queryset.filter(product=product)
                    
                    total_demand = queryset.aggregate(total=Sum('mcv'))['total'] or 0
                    
                    hourly_demand = list(queryset
                        .extra(select={'hour': "strftime('%%H', timestamp)"})
                        .values('hour')
                        .annotate(demand=Sum('mcv'))
                        .order_by('hour'))
                    
                    response_data['date'] = start
                    response_data['total_demand'] = total_demand
                    response_data['hourly_demand'] = hourly_demand
                    
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
            
        elif query_type == 'generation':
            # Get generation data
            if not start:
                # If no start date, assume user wants the most recent data
                latest = IEXMarketData.objects.all().order_by('-timestamp').first()
                if latest:
                    start = latest.timestamp.strftime("%Y-%m-%d")
            
            if start:
                try:
                    date_obj = datetime.strptime(start, "%Y-%m-%d").date()
                    queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
                    
                    if product:
                        queryset = queryset.filter(product=product)
                        
                    total_generation = queryset.aggregate(total=Sum('mcv'))['total'] or 0
                    
                    hourly_generation = list(queryset
                        .extra(select={'hour': "strftime('%%H', timestamp)"})
                        .values('hour', 'product')
                        .annotate(generation=Sum('mcv'))
                        .order_by('hour', 'product'))
                    
                    generators = queryset.values_list('product', flat=True).distinct()
                    
                    response_data['date'] = start
                    response_data['generators'] = list(generators)
                    response_data['selected_generator'] = product
                    response_data['total_generation'] = total_generation
                    response_data['hourly_generation'] = hourly_generation
                
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        
        elif query_type == 'volume':
            # Get market volume data
            queryset = IEXMarketData.objects.all()
            
            if product:
                queryset = queryset.filter(product=product)
            
            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d")
                    end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
            
            total_volume = queryset.aggregate(total_volume=Sum('mcv'))['total_volume']
            response_data['total_volume'] = total_volume
            
            # Get the time series data for visualization
            time_series = list(queryset.values('timestamp', 'mcv', 'product').order_by('timestamp'))
            response_data['time_series'] = time_series
        
        elif query_type == 'trend':
            # Get trend analysis data
            queryset = IEXMarketData.objects.all()
            
            if product:
                queryset = queryset.filter(product=product)
            
            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d")
                    end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
            
            # Group by day for trend analysis
            daily_data = list(queryset
                .extra(select={'day': "date(timestamp)"})
                .values('day')
                .annotate(
                    avg_price=Avg('mcp'),
                    avg_volume=Avg('mcv'),
                    total_volume=Sum('mcv')
                )
                .order_by('day'))
            
            response_data['trend_data'] = daily_data
            
            # Calculate simple trend indicators
            if len(daily_data) > 1:
                first_day = daily_data[0]
                last_day = daily_data[-1]
                
                price_change = last_day['avg_price'] - first_day['avg_price']
                price_change_pct = (price_change / first_day['avg_price']) * 100 if first_day['avg_price'] else 0
                
                volume_change = last_day['total_volume'] - first_day['total_volume']
                volume_change_pct = (volume_change / first_day['total_volume']) * 100 if first_day['total_volume'] else 0
                
                response_data['price_change'] = price_change
                response_data['price_change_pct'] = price_change_pct
                response_data['volume_change'] = volume_change
                response_data['volume_change_pct'] = volume_change_pct
        
        else:
            # Default to basic price query if unknown query type
            queryset = IEXMarketData.objects.all()

            if product:
                queryset = queryset.filter(product=product)

            if start and end:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d")
                    end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
                    queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

            avg_price = queryset.aggregate(avg_price=Avg('mcp'))['avg_price']
            response_data['average_mcp'] = avg_price

        # Format a user-friendly response message
        if query_type == 'price':
            if product and start and end:
                response_data['message'] = f"The average price for {product} between {start} and {end} was {round(avg_price, 2) if avg_price else 'N/A'} Rs/MWh."
            elif product:
                response_data['message'] = f"The average price for {product} was {round(avg_price, 2) if avg_price else 'N/A'} Rs/MWh."
            else:
                response_data['message'] = f"The average price was {round(avg_price, 2) if avg_price else 'N/A'} Rs/MWh."
        
        elif query_type == 'weighted_avg':
            if product and start and end:
                response_data['message'] = f"The weighted average price for {product} between {start} and {end} was {round(weighted_avg, 2) if weighted_avg else 'N/A'} Rs/MWh."
            elif product:
                response_data['message'] = f"The weighted average price for {product} was {round(weighted_avg, 2) if weighted_avg else 'N/A'} Rs/MWh."
            else:
                response_data['message'] = f"The weighted average price was {round(weighted_avg, 2) if weighted_avg else 'N/A'} Rs/MWh."
        
        elif query_type == 'demand':
            response_data['message'] = f"The total demand for {start} was {round(total_demand, 2) if 'total_demand' in response_data else 'N/A'} MW."
        
        elif query_type == 'generation':
            if product:
                response_data['message'] = f"The total generation for {product} on {start} was {round(total_generation, 2) if 'total_generation' in response_data else 'N/A'} MW."
            else:
                response_data['message'] = f"The total generation on {start} was {round(total_generation, 2) if 'total_generation' in response_data else 'N/A'} MW."
        
        elif query_type == 'volume':
            if product and start and end:
                response_data['message'] = f"The total volume for {product} between {start} and {end} was {round(total_volume, 2) if total_volume else 'N/A'} MW."
            elif product:
                response_data['message'] = f"The total volume for {product} was {round(total_volume, 2) if total_volume else 'N/A'} MW."
            else:
                response_data['message'] = f"The total volume was {round(total_volume, 2) if total_volume else 'N/A'} MW."
        
        elif query_type == 'trend':
            if 'price_change_pct' in response_data:
                direction = "increased" if response_data['price_change_pct'] > 0 else "decreased"
                response_data['message'] = f"The price {direction} by {abs(round(response_data['price_change_pct'], 2))}% over the period."
            else:
                response_data['message'] = "Not enough data to determine a trend."

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': 'Unexpected error occurred', 'details': str(e)}, status=500)

@require_http_methods(['GET'])
@api_view(['GET'])
def get_weighted_avg_price(request):
    product = request.GET.get('product')
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # Get queryset with filtering
    queryset = IEXMarketData.objects.all()
    if product:
        queryset = queryset.filter(product=product)
    
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
            queryset = queryset.filter(timestamp__gte=start_date, timestamp__lt=end_date)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    
    # Calculate weighted average: Σ(price * volume) / Σ(volume)
    result = queryset.aggregate(
        weighted_value=Sum(F('mcp') * F('mcv')),
        total_volume=Sum('mcv')
    )
    
    weighted_avg = None
    if result['total_volume'] and result['total_volume'] > 0:
        weighted_avg = result['weighted_value'] / result['total_volume']
    
    return Response({
        'product': product,
        'start': start,
        'end': end,
        'weighted_average_mcp': weighted_avg,
        'total_volume': result['total_volume']
    })

@api_view(['GET'])
def get_total_demand(request):
    """
    Get total electricity demand for a specific date.
    """
    date = request.GET.get('date')
    if not date:
        return Response({'error': 'Missing date parameter'}, status=400)
    
    try:
        # Parse the date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Get all records for this date
        queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
        
        # Calculate total demand (sum of MCV)
        total_demand = queryset.aggregate(total=Sum('mcv'))['total'] or 0
        
        # Get hourly demand for the chart
        hourly_demand = list(queryset
            .extra(select={'hour': "strftime('%%H', timestamp)"})
            .values('hour')
            .annotate(demand=Sum('mcv'))
            .order_by('hour'))
        
        return Response({
            'date': date,
            'total_demand': total_demand,
            'hourly_demand': hourly_demand
        })
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_generator_data(request):
    """
    Get generation data for a specific date and generator.
    Returns hourly generation breakdown.
    """
    date = request.GET.get('date')
    generator = request.GET.get('generator')
    
    if not date:
        return Response({'error': 'Missing date parameter'}, status=400)
    
    try:
        # Parse the date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Build the query
        queryset = IEXMarketData.objects.filter(timestamp__date=date_obj)
        
        # Filter by generator if provided
        if generator:
            queryset = queryset.filter(product=generator)  # Assuming generator info is in product field
            
        # Calculate total generation (sum of MCV)
        total_generation = queryset.aggregate(total=Sum('mcv'))['total'] or 0
        
        # Get hourly generation data
        hourly_generation = list(queryset
            .extra(select={'hour': "strftime('%%H', timestamp)"})
            .values('hour', 'product')
            .annotate(generation=Sum('mcv'))
            .order_by('hour', 'product'))
        
        # Get unique generators in this data
        generators = queryset.values_list('product', flat=True).distinct()
        
        return Response({
            'date': date,
            'generators': list(generators),
            'selected_generator': generator,
            'total_generation': total_generation,
            'hourly_generation': hourly_generation
        })
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
