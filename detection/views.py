# detection/views.py

import os
import uuid
from django.shortcuts import render
from django.conf import settings
from ultralytics import YOLO

model = YOLO("yolov8n.pt")


def home(request):
    if request.method == "POST" and request.FILES.get("image"):
        image = request.FILES["image"]
        uid = uuid.uuid4().hex
        original_filename = f"{uid}.jpg"
        result_filename = f"{uid}_result.jpg"

        original_path = os.path.join(settings.MEDIA_ROOT, original_filename)
        result_path = os.path.join(settings.MEDIA_ROOT, result_filename)

        # сохраняем оригинал
        with open(original_path, "wb+") as f:
            for chunk in image.chunks():
                f.write(chunk)

        # YOLO предсказание
        results = model(original_path)
        results[0].save(filename=result_path)  # сохраняем изображение с bbox

        # собираем классы и вероятности
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            label = model.names[cls_id]
            detections.append({
                "label": label,
                "confidence": round(confidence, 2)
            })

        return render(request, "detection/home.html", {
            "original_image_url": settings.MEDIA_URL + original_filename,
            "result_image_url": settings.MEDIA_URL + result_filename,
            "detections": detections
        })

    return render(request, "detection/home.html")
