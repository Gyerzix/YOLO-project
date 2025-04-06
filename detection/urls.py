from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('image/<int:pk>/', views.image_detail, name='image_detail'),
]