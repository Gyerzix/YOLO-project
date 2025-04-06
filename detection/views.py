import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import UploadedImage, DetectionResult
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def home(request):
    if request.method == "POST" and request.FILES.get("image"):
        uploaded_image = UploadedImage(
            title=request.POST.get('title', ''),
            image=request.FILES['image']
        )
        uploaded_image.save()
        return redirect('home')

    images = UploadedImage.objects.all().order_by('-uploaded_at')
    return render(request, "detection/home.html", {'images': images})


def image_detail(request, pk):
    image = get_object_or_404(UploadedImage, pk=pk)

    if request.method == "POST" and 'detect' in request.POST:
        # Удаляем старые результаты
        DetectionResult.objects.filter(image=image).delete()

        # Пути к файлам
        original_path = os.path.join(settings.MEDIA_ROOT, image.image.name)
        result_filename = f"results/{uuid.uuid4().hex}.jpg"
        result_path = os.path.join(settings.MEDIA_ROOT, result_filename)

        # Создаем директорию results, если ее нет
        os.makedirs(os.path.dirname(result_path), exist_ok=True)

        # YOLO предсказание
        results = model(original_path)
        results[0].save(filename=result_path)  # сохраняем изображение с bbox

        # Обновляем запись в базе данных
        image.result_image = result_filename
        image.save()

        # Сохраняем обнаруженные объекты
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
        'detections': detections,
        'has_result': image.result_image and os.path.exists(image.result_image.path)  # проверяем наличие файла
    })
