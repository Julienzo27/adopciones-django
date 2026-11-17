"""Ingreso con código de un solo uso enviado por email.

Reglas:
- el código tiene 6 dígitos y vence a los 10 minutos;
- sirve una sola vez y se admiten 5 intentos fallidos;
- pedir un código nuevo invalida los anteriores;
- no se puede pedir otro hasta pasados 60 segundos;
- en la base se guarda solo un hash (HMAC), nunca el código.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from adopciones.models import Adoptante, CodigoIngreso

VIGENCIA = timedelta(minutes=10)
ESPERA_REENVIO = timedelta(seconds=60)
MAX_INTENTOS = 5


def _hash(adoptante_id: int, codigo: str) -> str:
    clave = settings.SECRET_KEY.encode()
    return hmac.new(clave, f"{adoptante_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def enviar_codigo(adoptante: Adoptante) -> bool:
    """Genera un código nuevo y lo envía por email. Devuelve False si se pidió
    otro hace menos de 60 segundos (en ese caso no se envía nada)."""
    ahora = timezone.now()
    with transaction.atomic():
        ultimo = adoptante.codigos.first()          # el más reciente (orden -creado)
        if ultimo and ahora - ultimo.creado < ESPERA_REENVIO:
            return False
        adoptante.codigos.filter(usado=False).update(usado=True)   # invalida los anteriores
        codigo = f"{secrets.randbelow(10 ** 6):06d}"
        CodigoIngreso.objects.create(
            adoptante=adoptante, codigo_hash=_hash(adoptante.pk, codigo), vence=ahora + VIGENCIA,
        )
    send_mail(
        subject="Tu código para ingresar a Adopciones",
        message=(
            f"Hola {adoptante.nombre}:\n\n"
            f"Tu código para ingresar es: {codigo}\n\n"
            f"Vence en {int(VIGENCIA.total_seconds() // 60)} minutos y sirve una sola vez.\n"
            "Si no lo pediste vos, ignorá este mensaje."
        ),
        from_email=None,
        recipient_list=[adoptante.email],
    )
    return True


def verificar_codigo(adoptante: Adoptante, codigo: str) -> bool:
    """True si el código es el vigente de este adoptante. Lo consume al acertar."""
    ahora = timezone.now()
    with transaction.atomic():
        vigente = (
            adoptante.codigos.select_for_update()
            .filter(usado=False, vence__gt=ahora)
            .first()
        )
        if vigente is None:
            return False
        if hmac.compare_digest(vigente.codigo_hash, _hash(adoptante.pk, codigo.strip())):
            vigente.usado = True
            vigente.save(update_fields=["usado"])
            return True
        vigente.intentos += 1
        if vigente.intentos >= MAX_INTENTOS:
            vigente.usado = True                    # se agotaron los intentos: hay que pedir otro
        vigente.save(update_fields=["intentos", "usado"])
        return False
