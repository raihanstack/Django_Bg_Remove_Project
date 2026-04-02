import os, uuid, threading, time
from django.shortcuts import render
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ImageUpload
from rembg import remove, new_session
from PIL import Image, UnidentifiedImageError
import logging

logger = logging.getLogger(__name__)

# Initialize the ONNX session once at startup to significantly improve response time per request
session = new_session("u2net")

def schedule_image_deletion(instance_id, delay=120):
    def delete_task():
        time.sleep(delay)
        try:
            from .models import ImageUpload
            instance = ImageUpload.objects.get(id=instance_id)
            if instance.image and os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
            if instance.output and os.path.isfile(instance.output.path):
                os.remove(instance.output.path)
            instance.delete()
            logger.info(f"Auto-deleted ImageUpload {instance_id} and its files after {delay} seconds.")
        except Exception as e:
            logger.error(f"Failed to auto-delete ImageUpload {instance_id}: {e}")
            
    thread = threading.Thread(target=delete_task)
    thread.daemon = True
    thread.start()

# Frontend View
def home(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            file = request.FILES['image']
            instance = ImageUpload.objects.create(image=file)

            filename = f"{uuid.uuid4()}.png"
            output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Process the image faster heavily using the global cached session
            input_img = Image.open(instance.image.path)
            output_img = remove(input_img, session=session)
            output_img.save(output_path)

            instance.output.name = f"outputs/{filename}"
            instance.save()

            # Schedule deletion 2 minutes (120 seconds) after processing
            schedule_image_deletion(instance.id, 120)

            return render(request, 'result.html', {'img': instance})
        
        except UnidentifiedImageError:
            return render(request, 'index.html', {'error': 'Invalid image format. Please upload a valid image.'})
        except Exception as e:
            logger.error(f"Error removing background: {e}")
            return render(request, 'index.html', {'error': 'An error occurred while processing the image. Please try again.'})

    return render(request, 'index.html')


# API View
@api_view(['POST'])
def remove_bg_api(request):
    file = request.FILES.get('image')
    if not file:
        return Response({'error': 'No image provided'}, status=400)

    try:
        instance = ImageUpload.objects.create(image=file)

        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        input_img = Image.open(instance.image.path)
        output_img = remove(input_img, session=session)
        output_img.save(output_path)

        instance.output.name = f"outputs/{filename}"
        instance.save()

        # Schedule deletion 2 minutes (120 seconds) after processing
        schedule_image_deletion(instance.id, 120)

        return Response({
            'id': instance.id,
            'image': instance.image.url,
            'output': instance.output.url
        })
    except UnidentifiedImageError:
        return Response({'error': 'Invalid image format. Please upload a valid image.'}, status=400)
    except Exception as e:
        logger.error(f"Error removing background: {e}")
        return Response({'error': str(e)}, status=500)