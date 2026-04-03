from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os, base64, requests
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import logging

logger = logging.getLogger(__name__)

# Hugging Face Settings
HF_API_URL = "https://api-inference.huggingface.co/models/briaai/RMBG-1.4"
HF_TOKEN = os.getenv("HF_TOKEN")

def query_hugging_face(image_bytes):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(HF_API_URL, headers=headers, data=image_bytes)
    if response.status_code != 200:
        logger.error(f"Hugging Face API error: {response.text}")
        raise Exception(f"Failed to process image via Hugging Face. Status: {response.status_code}")
    return response.content

# Frontend View
def home(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            file = request.FILES['image']
            image_bytes = file.read()
            
            # Process via Hugging Face API
            processed_bytes = query_hugging_face(image_bytes)
            
            # Encode as Base64 data URI
            base64_img = base64.b64encode(processed_bytes).decode('utf-8')
            output_url = f"data:image/png;base64,{base64_img}"
            
            # Construct a dummy object to conform to output expectation
            class DummyOutput:
                url = output_url
            class DummyImg:
                output = DummyOutput()

            return render(request, 'result.html', {'img': DummyImg()})
        
        except UnidentifiedImageError:
            return render(request, 'index.html', {'error': 'Invalid image format. Please upload a valid image.'})
        except Exception as e:
            logger.error(f"Error removing background: {e}")
            return render(request, 'index.html', {'error': f'An error occurred: {str(e)}'})

    return render(request, 'index.html')

# API View (Pure Django)
@csrf_exempt
def remove_bg_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    file = request.FILES.get('image')
    if not file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        image_bytes = file.read()
        
        # Process via Hugging Face API
        processed_bytes = query_hugging_face(image_bytes)
        
        base64_img = base64.b64encode(processed_bytes).decode('utf-8')
        output_url = f"data:image/png;base64,{base64_img}"

        return JsonResponse({
            'image_processed': True,
            'output': output_url
        })
    except Exception as e:
        logger.error(f"Error removing background: {e}")
        return JsonResponse({'error': str(e)}, status=500)