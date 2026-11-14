from django.contrib import admin

from .models import Adoptante, Criterio, Perro, Solicitud


@admin.register(Perro)
class PerroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "edad", "nivel_energia", "estado")
    list_filter = ("estado", "nivel_energia")
    search_fields = ("nombre",)


@admin.register(Adoptante)
class AdoptanteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "tipo_vivienda", "perfil_completo")
    search_fields = ("nombre", "email")

    @admin.display(boolean=True, description="Perfil completo")
    def perfil_completo(self, obj):
        return obj.perfil_completo


@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "peso", "activo")
    list_editable = ("peso", "activo")


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("adoptante", "perro", "estado", "porcentaje_compatibilidad", "fecha")
    list_filter = ("estado",)
    readonly_fields = ("porcentaje_compatibilidad", "detalle_calculo", "fecha")
