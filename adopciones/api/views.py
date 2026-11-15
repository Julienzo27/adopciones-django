from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from adopciones.models import Criterio
from adopciones.services.motor import RechazoMotor, calcular_compatibilidades
from adopciones.services.solicitudes import ReglaSolicitud, crear_solicitud

from .auth import AdoptanteSesion, EsAdoptante
from .serializers import CompatibleSerializer, SolicitudCrearSerializer, SolicitudSerializer


class ApiAdoptanteView(APIView):
    authentication_classes = [AdoptanteSesion]
    permission_classes = [EsAdoptante]


def _compatibles(adoptante):
    """Devuelve (lista, None) o (None, Response de error) si el motor rechaza el cálculo."""
    try:
        compatibles, _ = calcular_compatibilidades(adoptante)
    except RechazoMotor as rechazo:
        return None, Response({"detalle": str(rechazo)}, status=status.HTTP_409_CONFLICT)
    return compatibles, None


class PerrosCompatiblesView(ApiAdoptanteView):
    """GET /api/perros/compatibles/ — perros compatibles del adoptante, de mayor a menor %."""

    def get(self, request):
        compatibles, error = _compatibles(request.user)
        if error:
            return error
        return Response(CompatibleSerializer(compatibles, many=True).data)


class PerroDetalleView(ApiAdoptanteView):
    """GET /api/perros/<id>/ — un perro compatible con el desglose del cálculo."""

    def get(self, request, pk):
        compatibles, error = _compatibles(request.user)
        if error:
            return error
        elegido = next((c for c in compatibles if c.perro.pk == pk), None)
        if elegido is None:
            return Response({"detalle": "Este perro no está disponible para vos."},
                            status=status.HTTP_404_NOT_FOUND)
        pesos = {c.nombre: c.peso for c in Criterio.objects.filter(activo=True)}
        datos = CompatibleSerializer(elegido).data
        datos["desglose"] = [
            {"criterio": Criterio.Nombre(nombre).label, "puntos": puntos, "peso": pesos[nombre]}
            for nombre, puntos in elegido.puntos.items()
        ]
        return Response(datos)


class SolicitudesView(ApiAdoptanteView):
    """GET /api/solicitudes/ lista las del adoptante. POST /api/solicitudes/ crea una."""

    def get(self, request):
        solicitudes = request.user.solicitudes.select_related("perro")
        return Response(SolicitudSerializer(solicitudes, many=True).data)

    def post(self, request):
        entrada = SolicitudCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            solicitud = crear_solicitud(request.user, entrada.validated_data["perro"])
        except ReglaSolicitud as error:
            return Response({"detalle": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(SolicitudSerializer(solicitud).data, status=status.HTTP_201_CREATED)
