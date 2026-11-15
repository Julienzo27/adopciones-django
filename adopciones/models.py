from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Perro(models.Model):
    class Nivel(models.TextChoices):
        BAJO = "bajo", "Bajo"
        MEDIO = "medio", "Medio"
        ALTO = "alto", "Alto"

    class Experiencia(models.TextChoices):
        NINGUNA = "ninguna", "Ninguna"
        ALGUNA = "alguna", "Alguna"
        MUCHA = "mucha", "Mucha"

    class Espacio(models.TextChoices):
        POCO = "poco", "Poco"
        MEDIO = "medio", "Medio"
        MUCHO = "mucho", "Mucho"

    class Estado(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        EN_PROCESO = "en_proceso", "En proceso"
        ADOPTADO = "adoptado", "Adoptado"

    nombre = models.CharField(max_length=60)
    edad = models.FloatField(help_text="Edad en años (puede ser decimal, ej. 0.5).")
    nivel_energia = models.CharField(max_length=10, choices=Nivel.choices)
    experiencia_requerida = models.CharField(max_length=10, choices=Experiencia.choices)
    espacio_necesario = models.CharField(max_length=10, choices=Espacio.choices)
    apto_ninos = models.BooleanField("apto para niños", default=True)
    apto_otras_mascotas = models.BooleanField("apto para otras mascotas", default=True)
    apto_departamento = models.BooleanField("apto para departamento", default=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.DISPONIBLE)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Adoptante(models.Model):
    """Perfil del adoptante. Los campos del cuestionario pueden estar vacíos:
    un adoptante con el email confirmado pero sin cuestionario es un perfil incompleto."""

    class Vivienda(models.TextChoices):
        CASA = "casa", "Casa"
        DEPARTAMENTO = "departamento", "Departamento"

    class EspacioExterior(models.TextChoices):
        NINGUNO = "ninguno", "Ninguno"
        CHICO = "chico", "Chico"
        AMPLIO = "amplio", "Amplio"

    class Experiencia(models.TextChoices):
        NINGUNA = "ninguna", "Ninguna"
        ALGUNA = "alguna", "Alguna"
        MUCHA = "mucha", "Mucha"

    class Actividad(models.TextChoices):
        BAJO = "bajo", "Bajo"
        MEDIO = "medio", "Medio"
        ALTO = "alto", "Alto"

    class EdadPreferida(models.TextChoices):
        CACHORRO = "cachorro", "Cachorro (menos de 2 años)"
        ADULTO = "adulto", "Adulto (2 a 7 años)"
        MAYOR = "mayor", "Mayor (8 años o más)"
        SIN_PREFERENCIA = "sin preferencia", "Sin preferencia"

    nombre = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    # Cuestionario (vacío = perfil incompleto)
    tipo_vivienda = models.CharField(max_length=15, choices=Vivienda.choices, blank=True)
    espacio_exterior = models.CharField(max_length=10, choices=EspacioExterior.choices, blank=True)
    hay_ninos = models.BooleanField("hay niños en el hogar", null=True, blank=True)
    tiene_otras_mascotas = models.BooleanField(null=True, blank=True)
    experiencia_previa = models.CharField(max_length=10, choices=Experiencia.choices, blank=True)
    nivel_actividad = models.CharField(max_length=10, choices=Actividad.choices, blank=True)
    edad_preferida = models.CharField(max_length=15, choices=EdadPreferida.choices, blank=True)
    # Preferencias: lista cerrada de 3 opciones
    pref_apto_ninos = models.BooleanField("prefiere perro apto para niños", default=False)
    pref_apto_otras_mascotas = models.BooleanField("prefiere perro apto para otras mascotas", default=False)
    pref_apto_departamento = models.BooleanField("prefiere perro apto para departamento", default=False)

    class Meta:
        ordering = ["nombre"]

    CAMPOS_CUESTIONARIO = [
        "tipo_vivienda", "espacio_exterior", "hay_ninos", "tiene_otras_mascotas",
        "experiencia_previa", "nivel_actividad", "edad_preferida",
    ]

    @property
    def perfil_completo(self):
        return all(getattr(self, c) not in ("", None) for c in self.CAMPOS_CUESTIONARIO)

    def __str__(self):
        return f"{self.nombre} <{self.email}>"


class Criterio(models.Model):
    """Criterio de compatibilidad con su peso configurable."""

    class Nombre(models.TextChoices):
        ENERGIA = "energia", "Energía"
        EXPERIENCIA = "experiencia", "Experiencia"
        ESPACIO = "espacio", "Espacio"
        EDAD = "edad", "Edad"
        PREFERENCIAS = "preferencias", "Preferencias"

    nombre = models.CharField(max_length=20, choices=Nombre.choices, unique=True)
    peso = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Debe ser 0 o mayor. Los pesos son relativos: no hace falta que sumen 100.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "criterio"
        verbose_name_plural = "criterios"
        constraints = [
            models.CheckConstraint(condition=models.Q(peso__gte=0), name="criterio_peso_no_negativo"),
        ]

    def __str__(self):
        return f"{self.get_nombre_display()} (peso {self.peso:g})"


class Solicitud(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    adoptante = models.ForeignKey(Adoptante, on_delete=models.PROTECT, related_name="solicitudes")
    perro = models.ForeignKey(Perro, on_delete=models.PROTECT, related_name="solicitudes")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    porcentaje_compatibilidad = models.FloatField(null=True, blank=True)
    detalle_calculo = models.JSONField(null=True, blank=True, help_text="Puntos obtenidos por cada criterio.")
    fecha = models.DateTimeField(auto_now_add=True)
    personal = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Persona del personal que resolvió la solicitud.",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name_plural = "solicitudes"

    def __str__(self):
        return f"{self.adoptante.nombre} → {self.perro.nombre} ({self.get_estado_display()})"
