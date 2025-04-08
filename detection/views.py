import os
import uuid
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages  # Добавлен импорт messages
from .models import UploadedVideo, UploadedImage, DetectionResult
from ultralytics import YOLO
import subprocess

model = YOLO("yolov8n.pt")


def home(request):
    if request.method == "POST":
        if request.FILES.get("image"):
            uploaded_image = UploadedImage(
                title=request.POST.get('title', ''),
                image=request.FILES['image']
            )
            uploaded_image.save()
            return redirect('home')
        elif request.FILES.get("video"):
            uploaded_video = UploadedVideo(
                title=request.POST.get('title', ''),
                video=request.FILES['video']
            )
            uploaded_video.save()
            return redirect('home')

    images = UploadedImage.objects.all().order_by('-uploaded_at')
    videos = UploadedVideo.objects.all().order_by('-uploaded_at')
    return render(request, "detection/home.html", {
        'images': images,
        'videos': videos
    })


def image_detail(request, pk):
    image = get_object_or_404(UploadedImage, pk=pk)

    if request.method == "POST" and 'detect' in request.POST:
        DetectionResult.objects.filter(image=image).delete()

        original_path = os.path.join(settings.MEDIA_ROOT, image.image.name)
        result_filename = f"results/{uuid.uuid4().hex}.jpg"
        result_path = os.path.join(settings.MEDIA_ROOT, result_filename)

        os.makedirs(os.path.dirname(result_path), exist_ok=True)

        results = model(original_path)
        results[0].save(filename=result_path)

        image.result_image = result_filename
        image.save()

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
        'object': image,
        'detections': detections,
        'has_result': image.result_image and os.path.exists(image.result_image.path),
        'is_video': False
    })


def video_detail(request, pk):
    video = get_object_or_404(UploadedVideo, pk=pk)

    if request.method == "POST" and 'detect' in request.POST:
        # Удаляем предыдущие результаты
        if video.result_video:
            if os.path.exists(video.result_video.path):
                os.remove(video.result_video.path)
            video.result_video = None
            video.save()

        # Пути к файлам
        original_path = os.path.join(settings.MEDIA_ROOT, video.video.name)
        result_filename = f"results/videos/{uuid.uuid4().hex}.mp4"
        result_path = os.path.join(settings.MEDIA_ROOT, result_filename)

        # Создаем директорию
        os.makedirs(os.path.dirname(result_path), exist_ok=True)

        try:
            # 1. Запускаем предсказание с явным указанием параметров
            results = model.predict(
                source=original_path,
                save=True,
                project=os.path.dirname(result_path),
                name="temp_yolo_output",
                exist_ok=True,
                imgsz=640,
                save_fmt='mp4',  # Явное указание формата
                stream=True,  # Для плавного воспроизведения
                codec='libx264'  # Кодек, поддерживаемый браузерами
            )

            # 2. Ищем созданный файл (теперь ищем .mp4)
            temp_dir = os.path.join(os.path.dirname(result_path), "temp_yolo_output")
            predicted_files = []

            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith('.mp4'):  # Ищем MP4 в любом регистре
                        predicted_files.append(os.path.join(root, file))

            if predicted_files:
                predicted_path = predicted_files[0]

                # 3. Переименовываем вместо копирования (быстрее)
                os.rename(predicted_path, result_path)

                # 4. Удаляем временную папку (если пустая)
                try:
                    os.rmdir(temp_dir)
                except OSError:
                    pass  # Папка не пустая - оставляем как есть

                # 5. Сохраняем результат
                video.result_video = result_filename
                video.save()
                messages.success(request, "Видео успешно обработано!")
            else:
                messages.error(request, "Не удалось найти результат обработки")
        except Exception as e:
            messages.error(request, f"Ошибка обработки: {str(e)}")
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        return redirect('video_detail', pk=pk)

    # Проверка существования результата и его доступности
    has_result = False
    if video.result_video:
        result_full_path = os.path.join(settings.MEDIA_ROOT, video.result_video.name)
        has_result = os.path.exists(result_full_path) and os.path.getsize(result_full_path) > 0

    return render(request, "detection/video_detail.html", {
        'video': video,
        'has_result': has_result,
    })
