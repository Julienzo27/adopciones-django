from django.urls import path

from . import views

urlpatterns = [
    path("perros/compatibles/", views.PerrosCompatiblesView.as_view(), name="api_compatibles"),
    path("perros/<int:pk>/", views.PerroDetalleView.as_view(), name="api_perro"),
    path("solicitudes/", views.SolicitudesView.as_view(), name="api_solicitudes"),
]
