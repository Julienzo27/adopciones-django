from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from adopciones.models import Adoptante, Criterio
from adopciones.services.motor import calcular_compatibilidades


class PesosConfigurablesTests(TestCase):
    fixtures = ["datos_ficticios"]

    def setUp(self):
        admin_user = get_user_model().objects.create_superuser("admin", password="x")
        self.client.force_login(admin_user)
        self.url_lista = reverse("admin:adopciones_criterio_changelist")

    def datos_lista(self, cambios=None, inactivos=()):
        """Arma el POST de la lista editable de criterios (una fila por criterio)."""
        cambios = cambios or {}
        criterios = list(Criterio.objects.order_by("id"))
        datos = {
            "form-TOTAL_FORMS": len(criterios), "form-INITIAL_FORMS": len(criterios),
            "form-MIN_NUM_FORMS": 0, "form-MAX_NUM_FORMS": 1000, "_save": "Guardar",
        }
        for i, c in enumerate(criterios):
            datos[f"form-{i}-id"] = c.pk
            datos[f"form-{i}-peso"] = cambios.get(c.nombre, c.peso)
            if c.nombre not in inactivos:
                datos[f"form-{i}-activo"] = "on"
        return datos

    def porcentajes_de_ana(self):
        compatibles, _ = calcular_compatibilidades(Adoptante.objects.get(nombre="Ana"))
        return {c.perro.nombre: c.porcentaje for c in compatibles}

    def test_cambiar_pesos_desde_el_admin_cambia_los_porcentajes(self):
        antes = self.porcentajes_de_ana()
        self.client.post(self.url_lista, self.datos_lista({"energia": 60}, inactivos=["preferencias"]))
        despues = self.porcentajes_de_ana()
        self.assertEqual(antes["Luna"], 90.0)
        self.assertEqual(despues, {"Luna": 91.7, "Kira": 91.7, "Nina": 68.8, "Bruno": 68.8})

    def test_no_se_pueden_desactivar_todos_los_criterios(self):
        respuesta = self.client.post(self.url_lista, self.datos_lista(inactivos=[c.nombre for c in Criterio.objects.all()]))
        self.assertContains(respuesta, "al menos un criterio activo")
        self.assertEqual(Criterio.objects.filter(activo=True).count(), 5)

    def test_no_se_aceptan_pesos_negativos_en_el_admin(self):
        self.client.post(self.url_lista, self.datos_lista({"energia": -5}))
        self.assertEqual(Criterio.objects.get(nombre="energia").peso, 30)

    def test_peso_negativo_falla_en_el_modelo(self):
        criterio = Criterio.objects.get(nombre="energia")
        criterio.peso = -1
        with self.assertRaises(ValidationError):
            criterio.full_clean()

    def test_peso_negativo_falla_en_la_base_de_datos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Criterio.objects.filter(nombre="energia").update(peso=-1)

    def test_los_pesos_no_tienen_que_sumar_100(self):
        self.client.post(self.url_lista, self.datos_lista({"energia": 5, "experiencia": 5, "espacio": 5, "edad": 5, "preferencias": 5}))
        pct = self.porcentajes_de_ana()
        self.assertTrue(all(0 <= v <= 100 for v in pct.values()))

    def test_formulario_de_edicion_no_deja_sin_criterios_utiles(self):
        Criterio.objects.exclude(nombre="energia").update(activo=False)
        criterio = Criterio.objects.get(nombre="energia")
        url = reverse("admin:adopciones_criterio_change", args=[criterio.pk])
        respuesta = self.client.post(url, {"nombre": "energia", "peso": 30})   # sin "activo" = inactivo
        self.assertContains(respuesta, "al menos un criterio activo")
        criterio.refresh_from_db()
        self.assertTrue(criterio.activo)
