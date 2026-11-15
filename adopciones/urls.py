from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("ingresar/", views.ingresar, name="ingresar"),
    path("salir/", views.salir, name="salir"),
    path("perfil/", views.perfil, name="perfil"),
    path("perros/", views.listado, name="listado"),
    path("perros/<int:pk>/", views.detalle_perro, name="detalle_perro"),
]
