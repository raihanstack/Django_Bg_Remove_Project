import os, uuid
from django.shortcuts import render
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ImageUpload
from rembg import remove
from PIL import Image

# Frontend View
def home(request):
    if request.method == 'POST' and request.FILES.get('image'):
        file = request.FILES['image']
        instance = ImageUpload.objects.create(image=file)

        filename = f"{uuid.uuid4()}.png"
        output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        input_img = Image.open(instance.image.path)
        output_img = remove(input_img)
        output_img.save(output_path)

        instance.output.name = f"outputs/{filename}"
        instance.save()

        return render(request, 'result.html', {'img': instance})

    return render(request, 'index.html')


# API View
@api_view(['POST'])
def remove_bg_api(request):
    file = request.FILES.get('image')
    if not file:
        return Response({'error': 'No image provided'}, status=400)

    instance = ImageUpload.objects.create(image=file)

    filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    input_img = Image.open(instance.image.path)
    output_img = remove(input_img)
    output_img.save(output_path)

    instance.output.name = f"outputs/{filename}"
    instance.save()

    return Response({
        'id': instance.id,
        'image': instance.image.url,
        'output': instance.output.url
    })