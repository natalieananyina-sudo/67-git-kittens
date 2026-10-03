from django.urls import path

from .views import analyze_view

urlpatterns = [path("api/analyze", analyze_view)]
