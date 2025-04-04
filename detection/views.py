# detection/views.py

from django.shortcuts import render
from django.http import JsonResponse
from ultralytics import YOLO
from PIL import Image

model = YOLO("yolov8n.pt")  # Используем предобученную модель


def home(request):
    return render(request, 'detection/home.html')  # показываем страницу загрузки


def detect_objects(request):
    if request.method == "POST" and request.FILES.get("image"):
        img = Image.open(request.FILES["image"]).convert("RGB")  # на всякий случай
        results = model(img)
        detections = []

        for result in results:
            for box in result.boxes:
                detections.append({
                    "class": result.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": list(map(float, box.xyxy[0]))
                })

        return JsonResponse({"detections": detections})

    return JsonResponse({"error": "Invalid request"}, status=400)
