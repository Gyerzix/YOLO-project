# Generated by Django 4.2.20 on 2025-04-06 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('detection', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DetectionResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=100)),
                ('confidence', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='UploadedImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=255)),
                ('image', models.ImageField(upload_to='uploads/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.DeleteModel(
            name='DetectedObject',
        ),
        migrations.DeleteModel(
            name='Detection',
        ),
        migrations.AddField(
            model_name='detectionresult',
            name='image',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='detection.uploadedimage'),
        ),
    ]
