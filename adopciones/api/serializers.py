from rest_framework import serializers

from adopciones.models import Perro, Solicitud


class CompatibleSerializer(serializers.Serializer):
    """Un perro compatible con su porcentaje y los puntos por criterio."""
    id = serializers.IntegerField(source="perro.pk")
    nombre = serializers.CharField(source="perro.nombre")
    edad = serializers.FloatField(source="perro.edad")
    nivel_energia = serializers.CharField(source="perro.nivel_energia")
    porcentaje = serializers.FloatField()
    puntos = serializers.DictField(child=serializers.FloatField())


class SolicitudSerializer(serializers.ModelSerializer):
    perro_nombre = serializers.CharField(source="perro.nombre", read_only=True)
    estado_texto = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Solicitud
        fields = ["id", "perro", "perro_nombre", "estado", "estado_texto",
                  "porcentaje_compatibilidad", "detalle_calculo", "fecha"]
        read_only_fields = fields


class SolicitudCrearSerializer(serializers.Serializer):
    perro = serializers.PrimaryKeyRelatedField(queryset=Perro.objects.all())
