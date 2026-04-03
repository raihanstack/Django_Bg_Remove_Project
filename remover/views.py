from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os, base64
from io import BytesIO
from rembg import remove, new_session
from PIL import Image, UnidentifiedImageError
import logging

logger = logging.getLogger(__name__)

# Set U2NET_HOME to /tmp so rembg downloads the model to Vercel's writable ephemeral storage
os.environ["U2NET_HOME"] = "/tmp"

# Initialize the ONNX session once at startup to significantly improve response time per request
session = new_session("u2net")

# Frontend View
def home(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            file = request.FILES['image']
            
            # Process the image fully in memory
            input_img = Image.open(file)
            output_img = remove(input_img, session=session)
            
            # Save the result to a BytesIO object
            io_buf = BytesIO()
            output_img.save(io_buf, format='PNG')
            io_buf.seek(0)
            
            # Encode as Base64 data URI
            base64_img = base64.b64encode(io_buf.read()).decode('utf-8')
            output_url = f"data:image/png;base64,{base64_img}"
            
            # Construct a dummy object to conform to the existing template expectation
            class DummyOutput:
                url = output_url
            class DummyImg:
                output = DummyOutput()

            return render(request, 'result.html', {'img': DummyImg()})
        
        except UnidentifiedImageError:
            return render(request, 'index.html', {'error': 'Invalid image format. Please upload a valid image.'})
        except Exception as e:
            logger.error(f"Error removing background: {e}")
            return render(request, 'index.html', {'error': 'An error occurred while processing the image. Please try again.'})

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
        input_img = Image.open(file)
        output_img = remove(input_img, session=session)

        # Save to BytesIO
        io_buf = BytesIO()
        output_img.save(io_buf, format='PNG')
        io_buf.seek(0)
        
        base64_img = base64.b64encode(io_buf.read()).decode('utf-8')
        output_url = f"data:image/png;base64,{base64_img}"

        return JsonResponse({
            'image_processed': True,
            'output': output_url
        })
    except UnidentifiedImageError:
        return JsonResponse({'error': 'Invalid image format. Please upload a valid image.'}, status=400)
    except Exception as e:
        logger.error(f"Error removing background: {e}")
        return JsonResponse({'error': str(e)}, status=500)