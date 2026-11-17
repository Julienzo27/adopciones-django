import re

from django.core import mail
from django.urls import reverse


def ingresar_con_codigo(client, email):
    """Hace el ingreso completo: pide el código, lo lee del correo y lo envía."""
    mail.outbox.clear()
    client.post(reverse("ingresar"), {"email": email})
    codigo = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
    return client.post(reverse("ingresar_codigo"), {"codigo": codigo})
