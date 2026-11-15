from django.contrib import admin, messages

from .models import Adoptante, Criterio, Perro, Solicitud
from .services.solicitudes import ReglaSolicitud, aprobar_solicitud, rechazar_solicitud


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
    list_display = ("adoptante", "perro", "estado", "porcentaje_compatibilidad", "fecha", "personal")
    list_filter = ("estado", "perro")
    ordering = ("perro__nombre", "-porcentaje_compatibilidad")   # mayor % primero, por perro
    readonly_fields = ("porcentaje_compatibilidad", "detalle_calculo", "fecha", "personal")
    actions = ["aprobar_seleccionadas", "rechazar_seleccionadas"]

    @admin.action(description="Aprobar solicitudes seleccionadas")
    def aprobar_seleccionadas(self, request, queryset):
        for solicitud in queryset:
            try:
                aprobar_solicitud(solicitud, request.user)
                self.message_user(request, f"Aprobada: {solicitud}", messages.SUCCESS)
            except ReglaSolicitud as error:
                self.message_user(request, f"{solicitud}: {error}", messages.WARNING)

    @admin.action(description="Rechazar solicitudes seleccionadas")
    def rechazar_seleccionadas(self, request, queryset):
        for solicitud in queryset:
            try:
                rechazar_solicitud(solicitud, request.user)
                self.message_user(request, f"Rechazada: {solicitud}", messages.SUCCESS)
            except ReglaSolicitud as error:
                self.message_user(request, f"{solicitud}: {error}", messages.WARNING)
