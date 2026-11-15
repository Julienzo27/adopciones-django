from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from adopciones.models import Adoptante, Perro, Solicitud
from adopciones.services.solicitudes import (
    ReglaSolicitud, aprobar_solicitud, crear_solicitud, rechazar_solicitud,
)


class BaseSolicitudes(TestCase):
    fixtures = ["datos_ficticios"]

    def setUp(self):
        self.ana = Adoptante.objects.get(nombre="Ana")
        self.beto = Adoptante.objects.get(nombre="Beto")
        self.carla = Adoptante.objects.get(nombre="Carla")
        self.luna = Perro.objects.get(nombre="Luna")
        self.thor = Perro.objects.get(nombre="Thor")
        self.personal = get_user_model().objects.create_user("personal", password="x", is_staff=True)


class CrearSolicitudTests(BaseSolicitudes):
    def test_guarda_porcentaje_y_detalle(self):
        s = crear_solicitud(self.ana, self.luna)
        self.assertEqual(s.estado, Solicitud.Estado.PENDIENTE)
        self.assertEqual(s.porcentaje_compatibilidad, 90.0)
        self.assertEqual(s.detalle_calculo["espacio"], 10)

    def test_perro_excluido_no_se_puede_solicitar(self):
        with self.assertRaises(ReglaSolicitud):
            crear_solicitud(self.ana, self.thor)   # Thor no es apto para departamento

    def test_perfil_incompleto_no_puede_solicitar(self):
        with self.assertRaises(ReglaSolicitud):
            crear_solicitud(self.carla, self.luna)

    def test_no_se_duplica_una_solicitud_activa(self):
        crear_solicitud(self.ana, self.luna)
        with self.assertRaises(ReglaSolicitud):
            crear_solicitud(self.ana, self.luna)


class ResolverSolicitudTests(BaseSolicitudes):
    def setUp(self):
        super().setUp()
        self.s_ana = crear_solicitud(self.ana, self.luna)
        self.s_beto = crear_solicitud(self.beto, self.luna)
        self.nina = Perro.objects.get(nombre="Nina")
        self.s_otro = crear_solicitud(self.ana, self.nina)

    def test_aprobar_deja_perro_en_proceso_y_rechaza_las_otras(self):
        aprobar_solicitud(self.s_ana, self.personal)
        for obj in (self.s_ana, self.s_beto, self.s_otro, self.luna):
            obj.refresh_from_db()
        self.assertEqual(self.s_ana.estado, Solicitud.Estado.APROBADA)
        self.assertEqual(self.s_ana.personal, self.personal)
        self.assertEqual(self.luna.estado, Perro.Estado.EN_PROCESO)
        self.assertEqual(self.s_beto.estado, Solicitud.Estado.RECHAZADA)
        self.assertEqual(self.s_otro.estado, Solicitud.Estado.PENDIENTE)   # otro perro: intacta

    def test_solo_se_aprueba_una_solicitud_por_perro(self):
        aprobar_solicitud(self.s_ana, self.personal)
        with self.assertRaises(ReglaSolicitud):
            aprobar_solicitud(self.s_beto, self.personal)

    def test_no_se_aprueba_una_solicitud_ya_resuelta(self):
        rechazar_solicitud(self.s_ana, self.personal)
        with self.assertRaises(ReglaSolicitud):
            aprobar_solicitud(self.s_ana, self.personal)

    def test_rechazar_no_cambia_el_perro(self):
        rechazar_solicitud(self.s_ana, self.personal)
        self.luna.refresh_from_db()
        self.s_ana.refresh_from_db()
        self.assertEqual(self.s_ana.estado, Solicitud.Estado.RECHAZADA)
        self.assertEqual(self.luna.estado, Perro.Estado.DISPONIBLE)

    def test_la_aprobacion_es_atomica(self):
        # Si falla al actualizar el perro, no debe quedar nada a medias.
        with mock.patch.object(Perro, "save", side_effect=RuntimeError("falla simulada")):
            with self.assertRaises(RuntimeError):
                aprobar_solicitud(self.s_ana, self.personal)
        self.s_ana.refresh_from_db()
        self.s_beto.refresh_from_db()
        self.luna.refresh_from_db()
        self.assertEqual(self.s_ana.estado, Solicitud.Estado.PENDIENTE)
        self.assertEqual(self.s_beto.estado, Solicitud.Estado.PENDIENTE)
        self.assertEqual(self.luna.estado, Perro.Estado.DISPONIBLE)

    def test_perro_en_proceso_desaparece_del_listado(self):
        from adopciones.services.motor import calcular_compatibilidades
        aprobar_solicitud(self.s_ana, self.personal)
        compatibles, _ = calcular_compatibilidades(self.beto)
        self.assertNotIn("Luna", [c.perro.nombre for c in compatibles])


class VistasYAdminSolicitudesTests(BaseSolicitudes):
    def ingresar(self, email):
        self.client.post(reverse("ingresar"), {"email": email})

    def test_solicitar_desde_la_vista(self):
        self.ingresar("ana@mail.com")
        respuesta = self.client.post(reverse("solicitar", args=[self.luna.pk]))
        self.assertRedirects(respuesta, reverse("mis_solicitudes"))
        self.assertEqual(Solicitud.objects.filter(adoptante=self.ana, perro=self.luna).count(), 1)

    def test_solicitar_requiere_post(self):
        self.ingresar("ana@mail.com")
        self.assertEqual(self.client.get(reverse("solicitar", args=[self.luna.pk])).status_code, 405)

    def test_mis_solicitudes_muestra_el_estado(self):
        self.ingresar("ana@mail.com")
        self.client.post(reverse("solicitar", args=[self.luna.pk]))
        respuesta = self.client.get(reverse("mis_solicitudes"))
        self.assertContains(respuesta, "Luna")
        self.assertContains(respuesta, "Pendiente")

    def test_detalle_avisa_si_ya_hay_solicitud(self):
        self.ingresar("ana@mail.com")
        self.client.post(reverse("solicitar", args=[self.luna.pk]))
        self.assertContains(self.client.get(reverse("detalle_perro", args=[self.luna.pk])),
                            "Ya tenés una solicitud")

    def test_accion_del_admin_aprueba(self):
        solicitud = crear_solicitud(self.ana, self.luna)
        admin_user = get_user_model().objects.create_superuser("admin", password="x")
        self.client.force_login(admin_user)
        self.client.post(reverse("admin:adopciones_solicitud_changelist"), {
            "action": "aprobar_seleccionadas", "_selected_action": [solicitud.pk],
        })
        solicitud.refresh_from_db()
        self.luna.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.Estado.APROBADA)
        self.assertEqual(self.luna.estado, Perro.Estado.EN_PROCESO)
