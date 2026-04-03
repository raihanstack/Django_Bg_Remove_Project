from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os, base64, requests, logging
from io import BytesIO
import numpy as np
from PIL import Image
import onnxruntime as ort

logger = logging.getLogger(__name__)

# Config
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
MODEL_PATH = os.path.join("/tmp", "u2netp.onnx")

def download_model():
    """Downloads the 4MB u2netp model if it doesn't exist in /tmp"""
    if not os.path.exists(MODEL_PATH):
        logger.info("Downloading u2netp.onnx model...")
        response = requests.get(MODEL_URL, stream=True)
        if response.status_code == 200:
            with open(MODEL_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Model downloaded successfully.")
        else:
            raise Exception("Failed to download model weights.")

def preprocess(img):
    """Prepares image for U2Net inference (320x320, normalization)"""
    img = img.convert('RGB')
    img_resized = img.resize((320, 320), Image.BILINEAR)
    
    # Normalize and ensure float32 precision to avoid ONNX double errors
    input_data = np.array(img_resized).astype(np.float32) / 255.0
    input_data = (input_data - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / \
                 np.array([0.229, 0.224, 0.225], dtype=np.float32)
    
    # Transpose to NCHW
    input_data = np.transpose(input_data, (2, 0, 1))
    input_data = np.expand_dims(input_data, 0)
    return input_data.astype(np.float32)

def postprocess(pred, original_size):
    """Normalizes mask and resizes back to original dimensions"""
    pred = pred[0][0, 0, :, :]
    
    # Normalize 0-1
    p_min, p_max = pred.min(), pred.max()
    pred = (pred - p_min) / (p_max - p_min + 1e-8)
    
    # Convert to PIL mask
    mask = Image.fromarray((pred * 255).astype(np.uint8))
    mask = mask.resize(original_size, Image.BILINEAR)
    return mask

def remove_background_local(image_file):
    """Main local background removal logic using ONNX runtime"""
    download_model()
    
    # 1. Load image
    orig_img = Image.open(image_file)
    orig_size = orig_img.size
    
    # 2. Run Inference
    session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    input_tensor = preprocess(orig_img)
    
    result = session.run(None, {input_name: input_tensor})
    
    # 3. Apply Mask
    mask = postprocess(result, orig_size)
    output_img = orig_img.convert("RGBA")
    output_img.putalpha(mask)
    
    # Save to buffer
    output_buffer = BytesIO()
    output_img.save(output_buffer, format='PNG')
    return output_buffer.getvalue()

# Views
def home(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            processed_bytes = remove_background_local(image_file)
            
            base64_img = base64.b64encode(processed_bytes).decode('utf-8')
            output_url = f"data:image/png;base64,{base64_img}"
            
            class DummyOutput: url = output_url
            class DummyImg: output = DummyOutput()

            return render(request, 'result.html', {'img': DummyImg()})
        except Exception as e:
            logger.error(f"Local error: {e}")
            return render(request, 'index.html', {'error': str(e)})

    return render(request, 'index.html')

@csrf_exempt
def remove_bg_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    file = request.FILES.get('image')
    if not file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        processed_bytes = remove_background_local(file)
        base64_img = base64.b64encode(processed_bytes).decode('utf-8')
        output_url = f"data:image/png;base64,{base64_img}"

        return JsonResponse({'image_processed': True, 'output': output_url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)