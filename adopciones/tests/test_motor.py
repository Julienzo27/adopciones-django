import time

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from adopciones.models import Adoptante, Criterio, Perro
from adopciones.services.motor import RechazoMotor, calcular_compatibilidades


class MotorTests(TestCase):
    fixtures = ["datos_ficticios"]

    def porcentajes(self, nombre):
        compatibles, excluidos = calcular_compatibilidades(Adoptante.objects.get(nombre=nombre))
        return (
            {c.perro.nombre: c.porcentaje for c in compatibles},
            {e.perro.nombre: e.motivo for e in excluidos},
            compatibles,
        )

    # Escenario 1: caso correcto (Ana)
    def test_ana_listado_correcto(self):
        pct, exc, compatibles = self.porcentajes("Ana")
        self.assertEqual(pct, {"Luna": 90.0, "Kira": 90.0, "Nina": 77.5, "Bruno": 77.5})
        self.assertEqual(set(exc), {"Thor", "Toby"})
        self.assertNotIn("Lola", pct)          # adoptada: no aparece
        valores = [c.porcentaje for c in compatibles]
        self.assertEqual(valores, sorted(valores, reverse=True))
        self.assertTrue(all(0 <= v <= 100 for v in valores))

    def test_luna_con_ana_calculo_a_mano(self):
        # 30 + 25 + 10 + 15 + 10 = 90 (al espacio le falta un nivel)
        _, _, compatibles = self.porcentajes("Ana")
        luna = next(c for c in compatibles if c.perro.nombre == "Luna")
        self.assertEqual(luna.puntos, {"energia": 30, "experiencia": 25, "espacio": 10, "edad": 15, "preferencias": 10})
        self.assertEqual(luna.porcentaje, 90.0)

    # Escenario 2: caso conflictivo (Beto)
    def test_beto_perros_excluidos_sin_porcentaje(self):
        pct, exc, _ = self.porcentajes("Beto")
        self.assertEqual(pct, {"Nina": 100.0, "Toby": 100.0, "Luna": 85.0})
        self.assertEqual(exc["Thor"], "no es apto para convivir con niños")
        self.assertEqual(exc["Kira"], "no es apto para convivir con niños")
        self.assertEqual(exc["Bruno"], "no es apto para convivir con otras mascotas")
        self.assertFalse(set(exc) & set(pct))

    # Escenario 3: rechazos del motor
    def test_perfil_incompleto_se_rechaza(self):
        with self.assertRaisesMessage(RechazoMotor, "perfil incompleto"):
            calcular_compatibilidades(Adoptante.objects.get(nombre="Carla"))

    def test_sin_criterios_activos_se_rechaza(self):
        Criterio.objects.update(activo=False)
        with self.assertRaisesMessage(RechazoMotor, "sin criterios configurados"):
            calcular_compatibilidades(Adoptante.objects.get(nombre="Ana"))

    def test_el_motor_no_escribe_en_la_base(self):
        ana = Adoptante.objects.get(nombre="Ana")
        with CaptureQueriesContext(connection) as consultas:
            calcular_compatibilidades(ana)
        for q in consultas.captured_queries:
            self.assertTrue(q["sql"].lstrip().upper().startswith("SELECT"), q["sql"])

    # Escenario 4: cambiar la configuración cambia el resultado
    def test_cambio_de_pesos(self):
        antes, _, _ = self.porcentajes("Ana")
        Criterio.objects.filter(nombre="energia").update(peso=60)
        Criterio.objects.filter(nombre="preferencias").update(activo=False)
        despues, _, compatibles = self.porcentajes("Ana")
        self.assertNotEqual(antes, despues)
        self.assertEqual(despues, {"Luna": 91.7, "Kira": 91.7, "Nina": 68.8, "Bruno": 68.8})
        self.assertTrue(all(0 <= c.porcentaje <= 100 for c in compatibles))

    # Escenario 5: rendimiento con 1000 perros
    def test_rendimiento_mil_perros(self):
        Perro.objects.bulk_create([
            Perro(nombre=f"Perro{i}", edad=(i % 12) + 0.5,
                  nivel_energia=["bajo", "medio", "alto"][i % 3],
                  experiencia_requerida=["ninguna", "alguna", "mucha"][i % 3],
                  espacio_necesario=["poco", "medio", "mucho"][(i // 3) % 3])
            for i in range(1000)
        ])
        ana = Adoptante.objects.get(nombre="Ana")
        inicio = time.perf_counter()
        compatibles, _ = calcular_compatibilidades(ana)
        duracion = time.perf_counter() - inicio
        self.assertEqual(len(compatibles), 1004)
        self.assertLess(duracion, 3)
