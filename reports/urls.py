from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('track/', views.track_case, name='track_case'),
    path('about/', views.about, name='about'),
]