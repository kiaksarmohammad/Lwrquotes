from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("manual", views.manual_view, name="manual_form"),
    path("drawing", views.drawing_form, name="drawing_form"),
    path("drawing/upload", views.drawing_upload, name="drawing_upload"),
    path("drawing/measure", views.drawing_measure, name="drawing_measure"),
    path("drawing/analyze", views.drawing_analyze, name="drawing_analyze"),
]
