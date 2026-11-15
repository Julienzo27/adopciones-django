from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from adopciones.models import Adoptante, Solicitud


class ApiTests(APITestCase):
    fixtures = ["datos_ficticios"]

    def cliente_de(self, nombre, csrf=False):
        cliente = APIClient(enforce_csrf_checks=csrf)
        sesion = cliente.session
        sesion["adoptante_id"] = Adoptante.objects.get(nombre=nombre).pk
        sesion.save()
        cliente.cookies["sessionid"] = sesion.session_key
        return cliente

    def test_sin_sesion_responde_401(self):
        self.assertEqual(self.client.get(reverse("api_compatibles")).status_code, 401)

    def test_compatibles_de_ana(self):
        r = self.cliente_de("Ana").get(reverse("api_compatibles"))
        self.assertEqual(r.status_code, 200)
        porcentajes = {p["nombre"]: p["porcentaje"] for p in r.json()}
        self.assertEqual(porcentajes, {"Luna": 90.0, "Kira": 90.0, "Nina": 77.5, "Bruno": 77.5})
        self.assertNotIn("Thor", porcentajes)

    def test_perfil_incompleto_responde_409(self):
        r = self.cliente_de("Carla").get(reverse("api_compatibles"))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detalle"], "perfil incompleto")

    def test_detalle_con_desglose(self):
        r = self.cliente_de("Ana").get(reverse("api_perro", args=[1]))   # Luna
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["porcentaje"], 90.0)
        self.assertEqual(len(r.json()["desglose"]), 5)

    def test_detalle_de_perro_excluido_responde_404(self):
        self.assertEqual(self.cliente_de("Ana").get(reverse("api_perro", args=[2])).status_code, 404)  # Thor

    def test_crear_solicitud_exige_csrf(self):
        cliente = self.cliente_de("Ana", csrf=True)
        r = cliente.post(reverse("api_solicitudes"), {"perro": 1}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Solicitud.objects.count(), 0)

    def test_crear_solicitud_con_csrf(self):
        cliente = self.cliente_de("Ana", csrf=True)
        cliente.get(reverse("listado_dinamico"))              # esta página entrega la cookie CSRF
        token = cliente.cookies["csrftoken"].value
        r = cliente.post(reverse("api_solicitudes"), {"perro": 1}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["porcentaje_compatibilidad"], 90.0)
        repetida = cliente.post(reverse("api_solicitudes"), {"perro": 1}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(repetida.status_code, 409)

    def test_no_se_puede_solicitar_un_perro_excluido(self):
        r = self.cliente_de("Ana").post(reverse("api_solicitudes"), {"perro": 2}, format="json")
        self.assertEqual(r.status_code, 409)

    def test_listar_mis_solicitudes(self):
        cliente = self.cliente_de("Ana")
        cliente.post(reverse("api_solicitudes"), {"perro": 1}, format="json")
        r = cliente.get(reverse("api_solicitudes"))
        self.assertEqual([s["perro_nombre"] for s in r.json()], ["Luna"])

    def test_pagina_dinamica_requiere_sesion_y_entrega_cookie(self):
        self.assertEqual(self.client.get(reverse("listado_dinamico")).status_code, 302)
        cliente = self.cliente_de("Ana")
        r = cliente.get(reverse("listado_dinamico"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)
