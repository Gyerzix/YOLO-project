from django.db import models


class UploadedImage(models.Model):
    title = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Image {self.id}"


class DetectionResult(models.Model):
    image = models.ForeignKey(UploadedImage, on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.confidence:.2f})"
