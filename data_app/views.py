from django.shortcuts import render
from .models import IEXMarketData
import pandas as pd
from .forms import UploadFileForm
from django.db.models import Avg, Sum
import io, os, json, requests, re
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils.timezone import now

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

                for _, row in df.iterrows():
                    IEXMarketData.objects.create(
                        product=row['product'],
                        mcv=row['mcv'],
                        mcp=row['mcp'],
                        timestamp=row['timestamp']
                    )

                message = "Data uploaded successfully."
            except Exception as e:
                message = f"Error processing CSV: {str(e)}"
        else:
            message = "Invalid form submission."
    else:
        form = UploadFileForm()

    # Get latest data
    data = IEXMarketData.objects.all().order_by('-timestamp')[:10]

    # Aggregations
    avg_prices = list(IEXMarketData.objects.values('product').annotate(avg_price=Avg('mcp')))
    total_volumes = list(IEXMarketData.objects.values('product').annotate(total_volume=Sum('mcv')))

    # Chart data for last 30 days (increased from 1)
    # cutoff = now() - timedelta(days=30)
    chart_data_qs = IEXMarketData.objects.all().order_by('timestamp')

    mcp_chart_data = [
        {
            'timestamp': entry.timestamp.isoformat(),
            'mcp': entry.mcp,
            'product': entry.product
        } for entry in chart_data_qs
    ]

    return render(request, 'dashboard.html', {
        'form': form,
        'data': data,
        'message': message,
        'avg_prices': avg_prices,
        'total_volumes': total_volumes,
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

        prompt = (
            f"You are a helpful assistant. Extract the product, start date, and end date from this sentence:\n"
            f"\"{user_question}\"\n"
            "Return your result strictly as a JSON object like this:\n"
            "{\n  \"product\": \"RTM\",\n  \"start\": \"2024-01-01\",\n  \"end\": \"2024-01-07\"\n}\n"
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

        product = params.get('product')
        start = params.get('start')
        end = params.get('end')

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

        return JsonResponse({
            'question': user_question,
            'parsed_params': params,
            'average_mcp': avg_price
        })

    except Exception as e:
        return JsonResponse({'error': 'Unexpected error occurred', 'details': str(e)}, status=500)
