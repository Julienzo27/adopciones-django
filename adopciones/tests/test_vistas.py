from django.test import TestCase
from django.urls import reverse

from adopciones.models import Adoptante

DATOS_REGISTRO = {
    "nombre": "Dani", "email": "dani@mail.com", "tipo_vivienda": "casa",
    "espacio_exterior": "amplio", "hay_ninos": "False", "tiene_otras_mascotas": "False",
    "experiencia_previa": "alguna", "nivel_actividad": "medio", "edad_preferida": "sin preferencia",
}


class VistasAdoptanteTests(TestCase):
    fixtures = ["datos_ficticios"]

    def ingresar(self, email):
        return self.client.post(reverse("ingresar"), {"email": email})

    def test_listado_sin_sesion_redirige_a_ingresar(self):
        self.assertRedirects(self.client.get(reverse("listado")), reverse("ingresar"))

    def test_registro_crea_adoptante_y_abre_sesion(self):
        respuesta = self.client.post(reverse("registro"), DATOS_REGISTRO)
        self.assertRedirects(respuesta, reverse("listado"))
        self.assertTrue(Adoptante.objects.get(email="dani@mail.com").perfil_completo)

    def test_registro_con_campos_faltantes_muestra_errores(self):
        datos = dict(DATOS_REGISTRO)
        del datos["nivel_actividad"]
        respuesta = self.client.post(reverse("registro"), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Adoptante.objects.filter(email="dani@mail.com").exists())

    def test_listado_de_ana_muestra_compatibles_y_oculta_excluidos(self):
        self.ingresar("ana@mail.com")
        respuesta = self.client.get(reverse("listado"))
        self.assertContains(respuesta, "Luna")
        self.assertContains(respuesta, "90,0 %")
        self.assertNotContains(respuesta, "Thor")    # excluido por los filtros
        self.assertNotContains(respuesta, "Lola")    # ya adoptada

    def test_perfil_incompleto_redirige_al_cuestionario(self):
        self.ingresar("carla@mail.com")
        self.assertRedirects(self.client.get(reverse("listado")), reverse("perfil"))

    def test_detalle_muestra_el_desglose(self):
        self.ingresar("ana@mail.com")
        respuesta = self.client.get(reverse("detalle_perro", args=[1]))
        self.assertContains(respuesta, "Cómo se calculó")
        self.assertContains(respuesta, "Energía")

    def test_detalle_de_perro_excluido_da_404(self):
        self.ingresar("ana@mail.com")
        self.assertEqual(self.client.get(reverse("detalle_perro", args=[2])).status_code, 404)  # Thor
