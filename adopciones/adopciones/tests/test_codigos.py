import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from adopciones.models import Adoptante, CodigoIngreso
from adopciones.services.codigos import MAX_INTENTOS
from adopciones.tests.test_vistas import DATOS_REGISTRO
from adopciones.tests.utils import ingresar_con_codigo


def codigo_del_ultimo_correo():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


class IngresoConCodigoTests(TestCase):
    fixtures = ["datos_ficticios"]

    def pedir(self, email="ana@mail.com"):
        return self.client.post(reverse("ingresar"), {"email": email})

    def enviar_codigo(self, codigo):
        return self.client.post(reverse("ingresar_codigo"), {"codigo": codigo})

    def sesion_iniciada(self):
        return self.client.get(reverse("listado")).status_code == 200

    def test_pedir_codigo_envia_un_correo_de_6_digitos(self):
        self.assertRedirects(self.pedir(), reverse("ingresar_codigo"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@mail.com"])
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

    def test_el_codigo_no_se_guarda_en_claro(self):
        self.pedir()
        codigo = codigo_del_ultimo_correo()
        guardado = CodigoIngreso.objects.get()
        self.assertNotIn(codigo, guardado.codigo_hash)
        self.assertEqual(len(guardado.codigo_hash), 64)

    def test_codigo_correcto_inicia_sesion(self):
        self.pedir()
        self.assertRedirects(self.enviar_codigo(codigo_del_ultimo_correo()), reverse("listado"))
        self.assertTrue(self.sesion_iniciada())

    def test_el_email_no_distingue_mayusculas(self):
        self.pedir("ANA@Mail.com")
        self.assertEqual(len(mail.outbox), 1)
        self.enviar_codigo(codigo_del_ultimo_correo())
        self.assertTrue(self.sesion_iniciada())

    def test_email_desconocido_no_envia_nada_ni_revela_que_no_existe(self):
        respuesta = self.pedir("nadie@mail.com")
        self.assertRedirects(respuesta, reverse("ingresar_codigo"))   # misma respuesta que con un email real
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.enviar_codigo("123456").status_code, 200)   # el código nunca coincide
        self.assertFalse(self.sesion_iniciada())

    def test_codigo_incorrecto_no_inicia_sesion(self):
        self.pedir()
        correcto = codigo_del_ultimo_correo()
        incorrecto = "000000" if correcto != "000000" else "111111"
        respuesta = self.enviar_codigo(incorrecto)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "incorrecto o venció")
        self.assertFalse(self.sesion_iniciada())

    def test_el_codigo_sirve_una_sola_vez(self):
        self.pedir()
        codigo = codigo_del_ultimo_correo()
        self.enviar_codigo(codigo)
        self.client.get(reverse("salir"))
        self.client.cookies.clear()
        # El segundo intento necesita un email pendiente: se vuelve a pedir y se prueba el código viejo.
        self.client.post(reverse("ingresar"), {"email": "ana@mail.com"})   # dentro de los 60 s: no se reenvía
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.enviar_codigo(codigo).status_code, 200)
        self.assertFalse(self.sesion_iniciada())

    def test_cinco_intentos_fallidos_bloquean_el_codigo(self):
        self.pedir()
        correcto = codigo_del_ultimo_correo()
        incorrecto = "000000" if correcto != "000000" else "111111"
        for _ in range(MAX_INTENTOS):
            self.enviar_codigo(incorrecto)
        self.assertEqual(self.enviar_codigo(correcto).status_code, 200)   # ya no alcanza con acertar
        self.assertFalse(self.sesion_iniciada())

    def test_codigo_vencido_se_rechaza(self):
        self.pedir()
        CodigoIngreso.objects.update(vence=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.enviar_codigo(codigo_del_ultimo_correo()).status_code, 200)
        self.assertFalse(self.sesion_iniciada())

    def test_no_se_puede_pedir_otro_codigo_antes_de_60_segundos(self):
        self.pedir()
        self.pedir()
        self.assertEqual(len(mail.outbox), 1)

    def test_un_codigo_nuevo_invalida_el_anterior(self):
        with mock.patch("adopciones.services.codigos.secrets.randbelow", side_effect=[111111, 222222]):
            self.pedir()
            CodigoIngreso.objects.update(creado=timezone.now() - timedelta(minutes=2))   # pasó la espera
            self.pedir()
        self.assertEqual(len(mail.outbox), 2)
        self.enviar_codigo("111111")                      # el viejo ya no sirve
        self.assertFalse(self.sesion_iniciada())
        self.enviar_codigo("222222")
        self.assertTrue(self.sesion_iniciada())

    def test_la_pantalla_del_codigo_exige_haber_pedido_uno(self):
        self.assertRedirects(self.client.get(reverse("ingresar_codigo")), reverse("ingresar"))

    def test_codigo_con_formato_invalido(self):
        self.pedir()
        respuesta = self.enviar_codigo("abc")
        self.assertContains(respuesta, "El código tiene 6 dígitos.")
        self.assertFalse(self.sesion_iniciada())

    def test_el_codigo_de_un_adoptante_no_sirve_para_otro(self):
        self.pedir("ana@mail.com")
        codigo_de_ana = codigo_del_ultimo_correo()
        self.client.post(reverse("ingresar"), {"email": "beto@mail.com"})   # ahora el pendiente es Beto
        self.enviar_codigo(codigo_de_ana)
        self.assertFalse(self.sesion_iniciada())

    def test_registro_confirma_el_email_con_codigo(self):
        self.client.post(reverse("registro"), DATOS_REGISTRO)
        self.assertEqual(mail.outbox[-1].to, ["dani@mail.com"])
        self.assertFalse(self.sesion_iniciada())
        self.enviar_codigo(codigo_del_ultimo_correo())
        self.assertTrue(self.sesion_iniciada())
        self.assertTrue(Adoptante.objects.get(email="dani@mail.com").perfil_completo)

    def test_helper_de_ingreso_completo(self):
        self.assertRedirects(ingresar_con_codigo(self.client, "ana@mail.com"), reverse("listado"))
