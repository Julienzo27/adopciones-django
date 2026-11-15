"""
Gestión de solicitudes de adopción (escritura).

A diferencia del motor de compatibilidad, que es de solo lectura, este módulo sí
modifica datos: crea solicitudes y resuelve su aprobación o rechazo.

Regla central: se aprueba UNA solicitud por perro. La aprobación es atómica:
o se hace todo (solicitud aprobada, perro "en proceso", otras solicitudes del
perro rechazadas) o no se hace nada. La decisión siempre es del personal.
"""
from django.db import transaction

from adopciones.models import Perro, Solicitud
from adopciones.services.motor import RechazoMotor, calcular_compatibilidades


class ReglaSolicitud(Exception):
    """Se intentó algo que las reglas de negocio no permiten."""


def crear_solicitud(adoptante, perro):
    """Crea una solicitud pendiente guardando el % y el detalle del cálculo."""
    try:
        compatibles, _ = calcular_compatibilidades(adoptante)
    except RechazoMotor as rechazo:
        raise ReglaSolicitud(f"No se puede solicitar: {rechazo}.")

    elegido = next((c for c in compatibles if c.perro.pk == perro.pk), None)
    if elegido is None:
        raise ReglaSolicitud("Este perro no está disponible para vos.")

    ya_activa = Solicitud.objects.filter(
        adoptante=adoptante, perro=perro,
        estado__in=[Solicitud.Estado.PENDIENTE, Solicitud.Estado.APROBADA],
    ).exists()
    if ya_activa:
        raise ReglaSolicitud("Ya tenés una solicitud activa para este perro.")

    return Solicitud.objects.create(
        adoptante=adoptante,
        perro=perro,
        porcentaje_compatibilidad=elegido.porcentaje,
        detalle_calculo=elegido.puntos,
    )


def aprobar_solicitud(solicitud, personal):
    """Aprueba la solicitud de forma atómica y rechaza las demás del mismo perro."""
    with transaction.atomic():
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud.pk)
        perro = Perro.objects.select_for_update().get(pk=solicitud.perro_id)

        if solicitud.estado != Solicitud.Estado.PENDIENTE:
            raise ReglaSolicitud("La solicitud ya no está pendiente.")
        if perro.estado != Perro.Estado.DISPONIBLE:
            raise ReglaSolicitud(f"{perro.nombre} ya no está disponible.")

        solicitud.estado = Solicitud.Estado.APROBADA
        solicitud.personal = personal
        solicitud.save()

        perro.estado = Perro.Estado.EN_PROCESO
        perro.save()

        Solicitud.objects.filter(
            perro=perro, estado=Solicitud.Estado.PENDIENTE
        ).exclude(pk=solicitud.pk).update(
            estado=Solicitud.Estado.RECHAZADA, personal=personal
        )
    return solicitud


def rechazar_solicitud(solicitud, personal):
    """Rechaza una solicitud pendiente. El perro sigue disponible."""
    with transaction.atomic():
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud.pk)
        if solicitud.estado != Solicitud.Estado.PENDIENTE:
            raise ReglaSolicitud("La solicitud ya no está pendiente.")
        solicitud.estado = Solicitud.Estado.RECHAZADA
        solicitud.personal = personal
        solicitud.save()
    return solicitud
