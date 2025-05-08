import os
import uuid
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages  # Добавлен импорт messages
from .models import UploadedVideo, UploadedImage, DetectionResult
from ultralytics import YOLO
import subprocess

model = YOLO("best.pt")


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

        # Пути к файлам (абсолютные)
        original_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT, video.video.name))
        result_dir = os.path.abspath(os.path.join(settings.MEDIA_ROOT, "results/videos"))
        os.makedirs(result_dir, exist_ok=True)

        # Генерируем имена файлов
        file_uuid = uuid.uuid4().hex
        avi_filename = f"{file_uuid}.avi"
        mp4_filename = f"{file_uuid}.mp4"
        avi_path = os.path.join(result_dir, avi_filename)
        mp4_path = os.path.join(result_dir, mp4_filename)

        try:
            # 1. Сохраняем результат YOLO в AVI
            results = model.predict(
                source=original_path,
                save=True,
                project=result_dir,
                name=file_uuid,
                exist_ok=True
            )

            # 2. Ищем созданный AVI файл (с абсолютным путем)
            predicted_avi = os.path.abspath(os.path.join(result_dir, file_uuid, avi_filename))
            if not os.path.exists(predicted_avi):
                # Альтернативный поиск
                for root, _, files in os.walk(os.path.join(result_dir, file_uuid)):
                    for file in files:
                        if file.endswith('.avi'):
                            predicted_avi = os.path.abspath(os.path.join(root, file))
                            break

            if os.path.exists(predicted_avi):
                # 3. Конвертируем AVI в MP4 с абсолютными путями
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', predicted_avi,
                    '-c:v', 'libx264',  # Перекодируем в H.264
                    '-c:a', 'aac',  # Перекодируем аудио в AAC (если есть)
                    '-movflags', '+faststart',  # Для стриминга
                    '-y',
                    mp4_path
                ]

                # Для Windows: преобразуем пути к формату, который понимает ffmpeg
                # if os.name == 'nt':
                #     ffmpeg_cmd[2] = predicted_avi.replace('\\', '/')
                #     ffmpeg_cmd[6] = mp4_path.replace('\\', '/')

                subprocess.run(ffmpeg_cmd, shell=True, check=True)

                # 4. Удаляем временные файлы
                shutil.rmtree(os.path.join(result_dir, file_uuid))

                # 5. Сохраняем результат (относительный путь для Django)
                video.result_video = f"results/videos/{mp4_filename}"
                video.save()
                messages.success(request, "Видео успешно обработано!")
            else:
                messages.error(request, "Не удалось создать AVI файл")

        except subprocess.CalledProcessError as e:
            messages.error(request, f"Ошибка конвертации видео: {str(e)}")
            # Очистка
            if os.path.exists(mp4_path):
                os.remove(mp4_path)
            temp_dir = os.path.join(result_dir, file_uuid)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            messages.error(request, f"Ошибка обработки: {str(e)}")
            if os.path.exists(mp4_path):
                os.remove(mp4_path)
            temp_dir = os.path.join(result_dir, file_uuid)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return redirect('video_detail', pk=pk)

    # Проверка существования результата
    has_result = video.result_video and os.path.exists(video.result_video.path)

    return render(request, "detection/video_detail.html", {
        'video': video,
        'has_result': has_result,
    })
