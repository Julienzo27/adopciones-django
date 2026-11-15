"""Autenticación de la API: reutiliza la sesión del adoptante (la misma de las páginas)."""
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.permissions import BasePermission

from adopciones.models import Adoptante

SESION = "adoptante_id"


class AdoptanteSesion(BaseAuthentication):
    """Identifica al adoptante por la sesión. Las operaciones que modifican datos
    exigen además el token CSRF, igual que las páginas."""

    def authenticate(self, request):
        pk = request.session.get(SESION)
        if not pk:
            return None
        adoptante = Adoptante.objects.filter(pk=pk).first()
        if adoptante is None:
            return None
        SessionAuthentication().enforce_csrf(request)
        return (adoptante, None)

    def authenticate_header(self, request):
        return "Session"          # hace que la API responda 401 (y no 403) sin sesión


class EsAdoptante(BasePermission):
    message = "Tenés que ingresar con tu email."

    def has_permission(self, request, view):
        return isinstance(request.user, Adoptante)
