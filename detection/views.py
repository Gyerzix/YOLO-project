import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import UploadedImage, DetectionResult
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def home(request):
    if request.method == "POST" and request.FILES.get("image"):
        # Создаем запись в базе данных
        uploaded_image = UploadedImage(
            title=request.POST.get('title', ''),
            image=request.FILES['image']
        )
        uploaded_image.save()
        return redirect('home')

    # Получаем все загруженные изображения
    images = UploadedImage.objects.all().order_by('-uploaded_at')
    return render(request, "detection/home.html", {'images': images})


def image_detail(request, pk):
    image = get_object_or_404(UploadedImage, pk=pk)

    if request.method == "POST" and 'detect' in request.POST:
        # Удаляем старые результаты, если они есть
        DetectionResult.objects.filter(image=image).delete()

        # Полный путь к изображению
        image_path = os.path.join(settings.MEDIA_ROOT, image.image.name)

        # YOLO предсказание
        results = model(image_path)

        # Сохраняем результаты в базу данных
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            label = model.names[cls_id]

            DetectionResult.objects.create(
                image=image,
                label=label,
                confidence=confidence
            )

        return redirect('image_detail', pk=pk)

    detections = DetectionResult.objects.filter(image=image)
    return render(request, "detection/image_detail.html", {
        'image': image,
        'detections': detections
    })
